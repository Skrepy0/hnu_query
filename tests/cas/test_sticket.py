import httpx
import pytest
import respx

from hnu_query.cas import CasNetworkError, CasStatusError, TokenExpired, get_sticket

START = "http://cas.hnu.edu.cn/application/sso.zf?login=gym"
CALLBACK = (
    "https://cas.hnu.edu.cn/sprcialapp/zf_form/index.zf?s_ticket=ST%2Btest&other=1"
)


@respx.mock
async def test_sticket_redirects_and_cookie_merge(cas_token):
    respx.get(START).respond(
        302, headers={"location": "/next", "set-cookie": "route=one; Path=/"}
    )
    route = respx.get("http://cas.hnu.edu.cn/next").respond(
        302,
        headers={
            "location": CALLBACK,
            "set-cookie": "route=two; Path=/",
        },
    )
    ticket, cookies = await get_sticket(cas_token, START)
    assert ticket == "ST+test"
    assert "route=two" in cookies and "route=one" not in cookies
    assert "TGC=tgt-fake" in cookies
    assert "route=one" in route.calls.last.request.headers["cookie"]
    assert len(respx.calls) == 2


@pytest.mark.parametrize(
    "status,headers,error",
    [
        (200, {}, TokenExpired),
        (500, {}, CasStatusError),
        (303, {}, CasStatusError),
        (302, {}, CasStatusError),
        (302, {"location": "https://example.org/"}, CasStatusError),
        (
            302,
            {"location": CALLBACK.replace("s_ticket=ST%2Btest", "s_ticket=")},
            CasStatusError,
        ),
    ],
)
@respx.mock
async def test_sticket_failures(cas_token, status, headers, error):
    respx.get(START).respond(status, headers=headers)
    with pytest.raises(error):
        await get_sticket(cas_token, START)


@respx.mock
async def test_sticket_loop_limit(cas_token):
    route = respx.get(START).respond(302, headers={"location": START})
    with pytest.raises(CasStatusError):
        await get_sticket(cas_token, START)
    assert route.call_count == 6


@respx.mock
async def test_sticket_network_failure(cas_token):
    respx.get(START).mock(side_effect=httpx.ConnectError("offline"))
    with pytest.raises(CasNetworkError):
        await get_sticket(cas_token, START)


@respx.mock
async def test_sticket_keeps_portal_and_cas_session_paths_separate(cas_token):
    login = "http://cas.hnu.edu.cn/cas/login?service=portal"
    exchange = "http://cas.hnu.edu.cn/system/login/login.zf?ticket=ST-test"
    respx.get(START).respond(
        302,
        headers={
            "location": login,
            "set-cookie": "JSESSIONID=portal; Path=/",
        },
    )
    respx.get(login).respond(
        302,
        headers={
            "location": exchange,
            "set-cookie": "JSESSIONID=cas; Path=/cas",
        },
    )

    def portal_session(request):
        cookies = request.headers.get("cookie", "")
        if "JSESSIONID=portal" in cookies and "JSESSIONID=cas" not in cookies:
            return httpx.Response(302, headers={"location": CALLBACK})
        return httpx.Response(302, headers={"location": "/system/login/main.zf"})

    route = respx.get(exchange).mock(side_effect=portal_session)
    respx.get("http://cas.hnu.edu.cn/system/login/main.zf").respond(200)
    ticket, cookies = await get_sticket(cas_token, START)
    assert ticket == "ST+test"
    assert "JSESSIONID=portal" in cookies and "JSESSIONID=cas" not in cookies
    assert route.call_count == 1
