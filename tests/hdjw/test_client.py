from urllib.parse import parse_qs

import httpx
import pytest
import respx

from hnu_query import hdjw
from hnu_query.hdjw.client import BASE_URL


@pytest.mark.parametrize(
    "method,path,fixture,args,expected_query",
    [
        (
            "get_grade",
            "/jsxsd/kscj/cjcx_list",
            "cjcx_list.json",
            (2025, 1),
            {"kksj": "2025-2026-1", "pageSize": "50", "xsfs": "all"},
        ),
        (
            "get_class_table",
            "/jsxsd/xskb/xskb_list.do",
            "xskb_list_mixed.json",
            (2025, 2),
            {
                "xnxq01id": "2025-2026-2",
                "sfykb": "2",
                "xsflMapListJsonStr": "讲课学时,指导学时,实验学时,其他,",
            },
        ),
        (
            "get_class_table_extra",
            "/jsxsd/xskb/xskb_list.do",
            "xskb_list_mixed.json",
            (2025, 2),
            {"xnxq01id": "2025-2026-2"},
        ),
        (
            "get_grade_detail",
            "/jsxsd/kscj/pscj_list.do",
            "pscj_list.html",
            ("id&special=1",),
            {"jx0404id": "id&special=1", "zcj": ""},
        ),
        (
            "get_exam_schedule",
            "/jsxsd/xsks/xsksap_list",
            "xsksap_list.json",
            (2025, 3),
            {"xnxqid": "2025-2026-3", "pageSize": "20"},
        ),
    ],
)
@respx.mock
async def test_public_gets(hdjw_token, fixture_text, method, path, fixture, args, expected_query):
    route = respx.get(BASE_URL + path).respond(200, text=fixture_text(fixture))
    result = await getattr(hdjw, method)(hdjw_token, *args)
    assert result
    request = route.calls.last.request
    assert request.headers["cookie"] == "JSESSIONID=hdjw-test"
    assert all(request.url.params[key] == value for key, value in expected_query.items())


@respx.mock
async def test_rank_form(hdjw_token, fixture_text):
    route = respx.post(BASE_URL + "/jsxsd/xscjsq/cjpmcx_list.do").respond(
        200,
        text=fixture_text("cjpmcx_list.json"),
    )
    await hdjw.get_rank(
        hdjw_token,
        [(2024, 1), (2025, 2)],
        hdjw.Range.Minor,
        hdjw.DataSource.Execution,
        hdjw.Display.Initial,
    )
    assert parse_qs(route.calls.last.request.content.decode(), keep_blank_values=True) == {
        "xnxq01id": ["2024-2025-1,2025-2026-2"],
        "kkxz1": [""],
        "pmfs1": [""],
        "kclx1": ["1"],
        "kcly1": ["2"],
        "xsfs1": ["1"],
    }
    await hdjw.get_rank(hdjw_token)
    assert parse_qs(route.calls.last.request.content.decode(), keep_blank_values=True)[
        "xnxq01id"
    ] == [""]


@respx.mock
async def test_empty_classroom_form(hdjw_token, fixture_text):
    route = respx.post(BASE_URL + "/jsxsd/kbxx/jsjy_query2").respond(
        200,
        text=fixture_text("jsjy_query2.json"),
    )
    result = await hdjw.get_empty_classroom(hdjw_token, "building", 0, 4, [1, 2, 3, 4, 5], 2025, 1)
    assert len(result) == 4
    assert parse_qs(route.calls.last.request.content.decode()) == {
        "xnxqh": ["2025-2026-1"],
        "jxlbh": ["building"],
        "selectZc": ["0"],
        "selectXq": ["4"],
        "selectJc": ["0102,0304,0506,0708,091011"],
        "typewhere": ["jszq"],
    }


@pytest.mark.parametrize("periods", [[0], [6], [True], [1.5]])
async def test_invalid_periods(hdjw_token, periods):
    async with hdjw.HdjwClient(hdjw_token) as client:
        with pytest.raises(ValueError):
            await client.get_empty_classroom("b", 1, 1, periods, 2025, 1)


@pytest.mark.parametrize(
    "status,headers,error",
    [
        (500, {}, hdjw.HdjwStatusError),
        (403, {}, hdjw.HdjwStatusError),
        (302, {"location": "/jsxsd/xk/LoginToXk"}, hdjw.TokenExpired),
        (302, {"location": "/unexpected"}, hdjw.HdjwStatusError),
    ],
)
@respx.mock
async def test_http_errors(hdjw_token, status, headers, error):
    respx.get(BASE_URL + "/jsxsd/kscj/cjcx_list").respond(status, headers=headers)
    with pytest.raises(error):
        await hdjw.get_grade(hdjw_token, 2025, 1)


@respx.mock
async def test_network_error(hdjw_token):
    respx.get(BASE_URL + "/jsxsd/kscj/cjcx_list").mock(side_effect=httpx.ConnectError("offline"))
    with pytest.raises(hdjw.HdjwNetworkError):
        await hdjw.get_grade(hdjw_token, 2025, 1)


async def test_injected_client_ownership_and_headers(hdjw_token):
    def handler(request):
        assert request.headers["cookie"] == "JSESSIONID=hdjw-test"
        assert request.url.host == "hdjw.hnu.edu.cn"
        return httpx.Response(200, json={"data": []})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as transport:
        async with hdjw.HdjwClient(hdjw_token, client=transport) as client:
            assert await client.get_grade(2025, 1) == []
        assert not transport.is_closed
    owned = hdjw.HdjwClient(hdjw_token)
    async with owned:
        pass
    assert owned._client.is_closed


def test_immutable_token():
    headers = {"Cookie": "secret"}
    token = hdjw.HdjwToken.from_headers_unchecked(headers)
    headers["Cookie"] = "changed"
    assert token.headers["Cookie"] == "secret"
    assert "secret" not in repr(token)
    with pytest.raises(TypeError):
        token.headers["Cookie"] = "new"
