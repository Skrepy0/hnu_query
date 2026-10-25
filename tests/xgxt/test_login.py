import httpx
import pytest
import respx

from hnu_query.cas import TokenExpired as CasTokenExpired
from hnu_query.xgxt import (
    XgxtLoginError,
    XgxtNetworkError,
    XgxtStatusError,
    XgxtToken,
    acquire_by_cas_login,
)
from hnu_query.xgxt.login import XGXT_URL

TICKET = "http://xgxt.hnu.edu.cn/zftal-xgxt-web/teacher/xtgl/index/check.zf?ticket=ST-test"


@respx.mock
async def test_login_upgrades_https_and_keeps_cookie(cas_token):
    respx.get(XGXT_URL).respond(302, headers={"location": TICKET})
    callback = respx.get(TICKET.replace("http://", "https://", 1)).respond(
        302,
        headers=[
            ("set-cookie", "JSESSIONID=ready; Path=/; HttpOnly"),
            ("set-cookie", "route=node1; Path=/"),
            ("location", "/home"),
        ],
    )
    token = await XgxtToken.acquire_by_cas_login(cas_token)
    assert token.headers["Cookie"] == "JSESSIONID=ready; route=node1"
    assert "cookie" not in callback.calls.last.request.headers
    assert len(respx.calls) == 2


@pytest.mark.parametrize(
    "status,headers,error",
    [
        (200, {"set-cookie": "session=ok"}, XgxtLoginError),
        (302, {}, XgxtLoginError),
        (500, {}, XgxtStatusError),
    ],
)
@respx.mock
async def test_bad_login(cas_token, status, headers, error):
    respx.get(XGXT_URL).respond(302, headers={"location": TICKET})
    respx.get(TICKET.replace("http://", "https://", 1)).respond(status, headers=headers)
    with pytest.raises(error):
        await acquire_by_cas_login(cas_token)


@respx.mock
async def test_expired_cas(cas_token):
    respx.get(XGXT_URL).respond(200)
    with pytest.raises(CasTokenExpired):
        await acquire_by_cas_login(cas_token)


@respx.mock
async def test_login_network_error(cas_token):
    respx.get(XGXT_URL).respond(302, headers={"location": TICKET})
    respx.get(TICKET.replace("http://", "https://", 1)).mock(
        side_effect=httpx.ConnectError("offline")
    )
    with pytest.raises(XgxtNetworkError):
        await acquire_by_cas_login(cas_token)
