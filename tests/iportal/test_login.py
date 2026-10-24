import httpx
import pytest
import respx

from hnu_query.cas import TokenExpired as CasTokenExpired
from hnu_query.iportal import (
    IPortalLoginError,
    IPortalNetworkError,
    IPortalStatusError,
    IPortalToken,
    acquire_by_cas_login,
)
from hnu_query.iportal._http import BASE_URL
from hnu_query.iportal.login import IPORTAL_LOGIN_URL

TICKET = BASE_URL + "/hnu/frontend/login?ticket=ST-test"


@respx.mock
async def test_login_merges_cookies_and_visits_one_redirect(cas_token):
    respx.get(IPORTAL_LOGIN_URL).respond(302, headers={"location": TICKET})
    ticket = respx.get(TICKET).respond(
        302,
        headers=[
            ("location", "/home"),
            ("set-cookie", "session=old; Path=/"),
            ("set-cookie", "route=node1; Path=/"),
        ],
    )
    home = respx.get(BASE_URL + "/home").respond(
        302,
        headers=[
            ("location", "/next"),
            ("set-cookie", "session=new; Path=/"),
            ("set-cookie", "auth=ok; Path=/"),
        ],
    )
    token = await IPortalToken.acquire_by_cas_login(cas_token)
    assert token.headers["Cookie"] == "session=new; route=node1; auth=ok"
    assert "cookie" not in ticket.calls.last.request.headers
    assert home.calls.last.request.headers["cookie"] == "session=old; route=node1"
    assert len(respx.calls) == 3


@respx.mock
async def test_cookies_only_in_second_response(cas_token):
    respx.get(IPORTAL_LOGIN_URL).respond(302, headers={"location": TICKET})
    respx.get(TICKET).respond(302, headers={"location": BASE_URL + "/home"})
    respx.get(BASE_URL + "/home").respond(200, headers={"set-cookie": "session=ready"})
    token = await acquire_by_cas_login(cas_token)
    assert token.headers["Cookie"] == "session=ready"


@respx.mock
async def test_missing_location_can_still_have_cookie(cas_token):
    respx.get(IPORTAL_LOGIN_URL).respond(302, headers={"location": TICKET})
    respx.get(TICKET).respond(302, headers={"set-cookie": "session=ready"})
    token = await acquire_by_cas_login(cas_token)
    assert token.headers["Cookie"] == "session=ready"
    assert len(respx.calls) == 2


@pytest.mark.parametrize(
    "status,headers,error",
    [
        (200, {"set-cookie": "session=ready"}, IPortalLoginError),
        (303, {}, IPortalLoginError),
        (302, {}, IPortalLoginError),
        (500, {}, IPortalStatusError),
        (
            302,
            {"location": "https://example.org/home", "set-cookie": "session=secret"},
            IPortalLoginError,
        ),
    ],
)
@respx.mock
async def test_bad_login(cas_token, status, headers, error):
    respx.get(IPORTAL_LOGIN_URL).respond(302, headers={"location": TICKET})
    respx.get(TICKET).respond(status, headers=headers)
    with pytest.raises(error):
        await acquire_by_cas_login(cas_token)


@respx.mock
async def test_expired_cas(cas_token):
    respx.get(IPORTAL_LOGIN_URL).respond(200)
    with pytest.raises(CasTokenExpired):
        await acquire_by_cas_login(cas_token)
    assert len(respx.calls) == 1


@respx.mock
async def test_network_failure(cas_token):
    respx.get(IPORTAL_LOGIN_URL).respond(302, headers={"location": TICKET})
    respx.get(TICKET).mock(side_effect=httpx.ConnectError("offline"))
    with pytest.raises(IPortalNetworkError):
        await acquire_by_cas_login(cas_token)
