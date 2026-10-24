from dataclasses import FrozenInstanceError
from urllib.parse import parse_qs

import httpx
import pytest
import respx

from hnu_query import yjsxt
from hnu_query.yjsxt._http import BASE_URL


@respx.mock
async def test_semester_session_id_in_url(yjsxt_token, yjsxt_text):
    route = respx.get(
        BASE_URL + "/gmis/(S(test-session))/student/default/bindterm"
    ).respond(200, text=yjsxt_text("bindterm.json"))
    semesters = await yjsxt.get_semester(yjsxt_token)
    assert len(semesters) == 56
    request = route.calls.last.request
    assert not request.url.query
    assert "cookie" not in request.headers
    assert not request.content


@respx.mock
async def test_class_table_form_and_session_path(yjsxt_token, yjsxt_text):
    route = respx.post(
        BASE_URL + "/gmis/(S(test-session))/student/pygl/py_kbcx_ew"
    ).respond(200, text=yjsxt_text("py_kbcx_ew.json"))
    result = await yjsxt.get_class_table(yjsxt_token, "63&other=1")
    assert len(result) == 5
    request = route.calls.last.request
    assert parse_qs(request.content.decode()) == {
        "kblx": ["xs"],
        "termcode": ["63&other=1"],
    }
    assert "cookie" not in request.headers


@pytest.mark.parametrize(
    "method,verb,path,args",
    [
        ("get_semester", "GET", "/student/default/bindterm", ()),
        ("get_class_table", "POST", "/student/pygl/py_kbcx_ew", ("63",)),
    ],
)
@pytest.mark.parametrize(
    "status,error",
    [
        (302, yjsxt.TokenExpired),
        (303, yjsxt.YjsxtStatusError),
        (403, yjsxt.YjsxtStatusError),
        (500, yjsxt.YjsxtStatusError),
    ],
)
@respx.mock
async def test_http_errors(yjsxt_token, method, verb, path, args, status, error):
    respx.route(method=verb, url=BASE_URL + "/gmis/(S(test-session))" + path).respond(
        status
    )
    with pytest.raises(error):
        await getattr(yjsxt, method)(yjsxt_token, *args)


@respx.mock
async def test_network_failure(yjsxt_token):
    respx.get(BASE_URL + "/gmis/(S(test-session))/student/default/bindterm").mock(
        side_effect=httpx.ConnectError("offline")
    )
    with pytest.raises(yjsxt.YjsxtNetworkError):
        await yjsxt.get_semester(yjsxt_token)


@respx.mock
async def test_login_html_response_is_parse_error(yjsxt_token):
    respx.get(BASE_URL + "/gmis/(S(test-session))/student/default/bindterm").respond(
        200, text="<html>login</html>"
    )
    with pytest.raises(yjsxt.YjsxtParseError):
        await yjsxt.get_semester(yjsxt_token)


async def test_connection_ownership(yjsxt_token):
    def handler(request):
        assert request.url.path == "/gmis/(S(test-session))/student/default/bindterm"
        return httpx.Response(200, json=[])

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        async with yjsxt.YjsxtClient(yjsxt_token, client=http) as client:
            assert await client.get_semester() == []
        assert not http.is_closed
    owned = yjsxt.YjsxtClient(yjsxt_token)
    async with owned:
        pass
    assert owned._client.is_closed


def test_immutable_token_and_hidden_id():
    token = yjsxt.YjsxtToken.from_id_unchecked("secret")
    assert token.id == "secret"
    assert "secret" not in repr(token)
    with pytest.raises(FrozenInstanceError):
        token.id = "changed"
