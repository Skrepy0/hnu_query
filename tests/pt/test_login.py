import httpx
import pytest
import respx

from hnu_query.cas import TokenExpired as CasTokenExpired
from hnu_query.pt import (
    PtLoginError,
    PtNetworkError,
    PtStatusError,
    PtToken,
    acquire_by_cas_login,
)
from hnu_query.pt._http import BASE_URL
from hnu_query.pt.login import PT_URL

TICKET = BASE_URL + "/?ticket=ST-test"


@respx.mock
async def test_cas_login_cookie_and_no_follow(cas_token):
    cas = respx.get(PT_URL).respond(302, headers={"location": TICKET})
    route = respx.get(TICKET).respond(
        302,
        headers=[
            ("location", "/home"),
            ("set-cookie", "SESSION=pt-session; Path=/; HttpOnly"),
            ("set-cookie", "route=node1; Secure"),
        ],
    )
    token = await PtToken.acquire_by_cas_login(cas_token)
    assert token.headers["Cookie"] == "SESSION=pt-session; route=node1"
    assert cas.calls.last.request.url.params["service"] == "https://pt.hnu.edu.cn/"
    assert cas.calls.last.request.headers["cookie"] == cas_token.cookie
    assert "cookie" not in route.calls.last.request.headers
    assert len(respx.calls) == 2


@pytest.mark.parametrize(
    "status,headers,error",
    [
        (200, {"set-cookie": "SESSION=test"}, PtLoginError),
        (303, {"set-cookie": "SESSION=test"}, PtLoginError),
        (302, {}, PtLoginError),
        (500, {}, PtStatusError),
    ],
)
@respx.mock
async def test_bad_login_response(cas_token, status, headers, error):
    respx.get(PT_URL).respond(302, headers={"location": TICKET})
    respx.get(TICKET).respond(status, headers=headers)
    with pytest.raises(error):
        await acquire_by_cas_login(cas_token)


@respx.mock
async def test_expired_cas(cas_token):
    respx.get(PT_URL).respond(200)
    with pytest.raises(CasTokenExpired):
        await acquire_by_cas_login(cas_token)
    assert len(respx.calls) == 1


@respx.mock
async def test_unexpected_callback(cas_token):
    respx.get(PT_URL).respond(
        302, headers={"location": "https://example.org/?ticket=ST-test"}
    )
    with pytest.raises(PtLoginError):
        await acquire_by_cas_login(cas_token)
    assert len(respx.calls) == 1


@respx.mock
async def test_network_error(cas_token):
    respx.get(PT_URL).respond(302, headers={"location": TICKET})
    respx.get(TICKET).mock(side_effect=httpx.ConnectError("offline"))
    with pytest.raises(PtNetworkError):
        await acquire_by_cas_login(cas_token)
