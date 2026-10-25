import json
from pathlib import Path

import httpx
import pytest
import respx

from hnu_query.credential import (
    CaClient,
    CaLoginError,
    CaParseError,
    CaToken,
    acquire_by_cas_login,
    file,
    preview_file_name,
)
from hnu_query.credential.login import CA_URL
from hnu_query.credential.parse import _parse_rank_from_text, parse_rank

BASE = "https://ca.hnu.edu.cn"
TICKET = BASE + "/student/?ticket=ST%2Btest%26part&extra=ignored#/"
VALIDATE = BASE + "/student/cas/client/validateLogin"


def test_all_rank_fields_against_rust_fixture():
    text = (Path(__file__).parent / "fixtures/grade_rank_pdf_extracted.txt").read_text(
        encoding="utf-8"
    )
    assert _parse_rank_from_text(text).model_dump() == {
        "all_gpa": "4.0",
        "all_gpa_rank": "30/90",
        "all_weighted": "86",
        "all_weighted_rank": "34/90",
        "all_arithmetic": "90",
        "all_arithmetic_rank": "32/90",
        "must_gpa": "3.8",
        "must_weighted": "84",
        "must_arithmetic": "88",
        "core_gpa_rank": "31/90",
        "core_weighted_rank": "35/90",
        "core_arithmetic_rank": "33/90",
    }


@pytest.mark.parametrize("value", [None, [], 1, "text"])
def test_preview_requires_object(value):
    with pytest.raises(CaParseError):
        preview_file_name(json.dumps(value))


@pytest.mark.parametrize("code", [200.0, "200", True, None])
def test_preview_requires_integer_code(code):
    with pytest.raises(CaParseError):
        preview_file_name(json.dumps({"code": code, "message": "file.pdf"}))


@pytest.mark.parametrize("value", [True, 123, [], {}, None])
def test_preview_requires_string_file_name(value):
    with pytest.raises(CaParseError):
        preview_file_name(json.dumps({"code": 200, "message": value}))


def test_preview_empty_string_matches_rust():
    assert preview_file_name('{"code":200,"message":""}') == ""


def test_invalid_pdf_is_parse_error():
    with pytest.raises(CaParseError):
        parse_rank(b"not a PDF")


@respx.mock
async def test_injected_client_gets_headers_and_absolute_url():
    token = CaToken({"X-Access-Token": "test", "Cookie": "session=test"})
    route = respx.get(BASE + "/student/student/caTemplate/preview_file").respond(
        json={"code": 200, "message": "file.pdf"}
    )
    async with httpx.AsyncClient(base_url="https://unrelated.example") as http:
        async with CaClient(token, client=http) as client:
            result = await client.preview_file("a&b")
        assert not http.is_closed
    request = route.calls.last.request
    assert request.headers["x-access-token"] == "test"
    assert request.headers["cookie"] == "session=test"
    assert request.url.params["templateId"] == "a&b"
    assert preview_file_name(result) == "file.pdf"


@respx.mock
async def test_cdn_does_not_receive_custom_credentials():
    source = BASE + "/student/sys/common/view/file.pdf"
    cdn = "https://cdn.example.org/file.pdf"
    respx.get(source).respond(302, headers={"location": cdn})
    route = respx.get(cdn).respond(content=b"pdf")
    token = CaToken({"X-Access-Token": "private", "Cookie": "access=private"})
    async with httpx.AsyncClient(
        headers={"X-Access-Token": "default-private", "Cookie": "default-private"},
        auth=("user", "password"),
        follow_redirects=True,
    ) as http:
        async with CaClient(token, client=http) as client:
            assert await client.file("file.pdf") == b"pdf"
    headers = route.calls.last.request.headers
    assert "cookie" not in headers and "x-access-token" not in headers
    assert "authorization" not in headers


@respx.mock
async def test_file_name_encodes_query_and_fragment(ca_token):
    route = respx.get(BASE + "/student/sys/common/view/a%3Fb%23c.pdf").respond(
        content=b"pdf"
    )
    assert await file(ca_token, "a?b#c.pdf") == b"pdf"
    assert not route.calls.last.request.url.query


@pytest.mark.parametrize(
    "target", ["http://cdn.example.org/a", "https://cas.hnu.edu.cn/cas/login"]
)
@respx.mock
async def test_download_rejects_downgrade_or_cas_login(ca_token, target):
    respx.get(BASE + "/student/sys/common/view/file.pdf").respond(
        302, headers={"location": target}
    )
    async with CaClient(ca_token) as client:
        with pytest.raises(CaLoginError):
            await client.file("file.pdf")
    assert client._client.is_closed
    assert len(respx.calls) == 1


@respx.mock
async def test_relative_download_and_redirect_limit(ca_token):
    start = BASE + "/student/sys/common/view/file.pdf"
    respx.get(start).respond(302, headers={"location": "/file.pdf"})
    route = respx.get(BASE + "/file.pdf").respond(
        302, headers={"location": "/file.pdf"}
    )
    with pytest.raises(CaLoginError):
        await file(ca_token, "file.pdf")
    assert route.call_count == 10


@respx.mock
async def test_login_encoded_ticket_and_cookie_reuse(cas_token):
    respx.get(CA_URL).respond(302, headers={"location": TICKET})
    respx.get(TICKET).respond(headers={"set-cookie": "session=ready; Path=/"})
    route = respx.get(VALIDATE).respond(
        json={"message": "\u767b\u5f55\u6210\u529f", "result": {"token": "valid-token"}}
    )
    token = await acquire_by_cas_login(cas_token)
    assert token.headers["X-Access-Token"] == "valid-token"
    assert route.calls.last.request.url.params["ticket"] == "ST+test&part#/"
    assert route.calls.last.request.url.params["service"] == BASE + "/student/"
    assert route.calls.last.request.headers["cookie"] == "session=ready"
    assert "TGC" not in route.calls.last.request.headers["cookie"]


@pytest.mark.parametrize(
    "body",
    [
        None,
        [],
        1,
        {"message": "\u767b\u5f55\u6210\u529f", "result": []},
        {"message": "\u767b\u5f55\u6210\u529f", "result": {"token": 123}},
        {"message": "\u767b\u5f55\u6210\u529f", "result": {"token": "bad\nheader"}},
    ],
)
@respx.mock
async def test_bad_login_shapes(cas_token, body):
    respx.get(CA_URL).respond(302, headers={"location": TICKET})
    respx.get(TICKET).respond(200)
    respx.get(VALIDATE).respond(text=json.dumps(body))
    with pytest.raises(CaLoginError):
        await acquire_by_cas_login(cas_token)


@pytest.mark.parametrize(
    "callback",
    [
        "https://evil.example/?ticket=ST-1",
        BASE + "/student/",
        BASE + "/student/?ticket=one&ticket=two",
        "http://ca.hnu.edu.cn/?ticket=ST-1",
    ],
)
@respx.mock
async def test_bad_ticket_callbacks(cas_token, callback):
    respx.get(CA_URL).respond(302, headers={"location": callback})
    with pytest.raises(CaLoginError):
        await acquire_by_cas_login(cas_token)
    assert len(respx.calls) == 1


@respx.mock
async def test_login_redirect_cannot_send_ticket_to_other_domain(cas_token):
    respx.get(CA_URL).respond(302, headers={"location": TICKET})
    respx.get(TICKET).respond(
        302, headers={"location": "https://other.example/?ticket=private"}
    )
    with pytest.raises(CaLoginError):
        await acquire_by_cas_login(cas_token)
    assert len(respx.calls) == 2


def test_ca_token_snapshot_and_redaction():
    headers = {"X-Access-Token": "private"}
    token = CaToken.from_headers_unchecked(headers)
    headers.clear()
    assert token.headers["X-Access-Token"] == "private"
    assert "private" not in repr(token)
    with pytest.raises(TypeError):
        token.headers["Cookie"] = "changed"


@respx.mock
async def test_file_preserves_server_returned_directory_path(ca_token):
    def download(request):
        # 实际凭证服务拒绝编码后的路径分隔符，返回的文件名包含目录。
        if b"%2f" in request.url.raw_path.lower():
            return httpx.Response(400)
        return httpx.Response(200, content=b"%PDF-test")

    route = respx.get(url__startswith=BASE + "/student/sys/common/view/").mock(
        side_effect=download
    )
    assert await file(ca_token, "temp/2026/10/document.pdf") == b"%PDF-test"
    assert route.calls.last.request.url.raw_path.endswith(b"/temp/2026/10/document.pdf")
