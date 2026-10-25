from urllib.parse import quote

import httpx
import pytest
import respx

from hnu_query.cas import TokenExpired as CasTokenExpired
from hnu_query.yjsxt import (
    YjsxtLoginError,
    YjsxtNetworkError,
    YjsxtStatusError,
    YjsxtToken,
    acquire_by_cas_login,
)
from hnu_query.yjsxt._http import BASE_URL
from hnu_query.yjsxt.login import YJSXT_FROM_CAS_URL

TICKET = BASE_URL + "/gmis/oauthLogin/hndxnew?ywdm=&ticket=ST-test"
REDIRECT = "/gmis/(S(test-session))/oauthLogin/hndxnew"


@pytest.mark.parametrize("absolute", [False, True])
@respx.mock
async def test_login_path_session_and_no_follow(cas_token, absolute):
    respx.get(YJSXT_FROM_CAS_URL).respond(302, headers={"location": TICKET})
    ticket = respx.get(TICKET).respond(
        302, headers={"location": BASE_URL + REDIRECT if absolute else REDIRECT}
    )
    target = respx.get(BASE_URL + REDIRECT).respond(
        302, headers={"location": "/gmis/(S(test-session))/student/home"}
    )
    token = await YjsxtToken.acquire_by_cas_login(cas_token)
    assert token.id == "(S(test-session))"
    assert "test-session" not in repr(token)
    assert "cookie" not in ticket.calls.last.request.headers
    assert "cookie" not in target.calls.last.request.headers
    assert len(respx.calls) == 3


@respx.mock
async def test_unqualified_account_decodes_message(cas_token):
    respx.get(YJSXT_FROM_CAS_URL).respond(302, headers={"location": TICKET})
    respx.get(TICKET).respond(302, headers={"location": REDIRECT})
    respx.get(BASE_URL + REDIRECT).respond(
        302,
        headers={"location": "/gmis/(S(test-session))/home/err?msg=" + quote("该账号不是研究生")},
    )
    with pytest.raises(YjsxtLoginError) as caught:
        await acquire_by_cas_login(cas_token)
    assert caught.value.message == "该账号不是研究生"


@pytest.mark.parametrize(
    "status,location,error",
    [
        (200, REDIRECT, YjsxtLoginError),
        (303, REDIRECT, YjsxtLoginError),
        (500, REDIRECT, YjsxtStatusError),
        (302, None, YjsxtLoginError),
        (302, "/not-gmis/path", YjsxtLoginError),
        (302, "/gmis//student/home", YjsxtLoginError),
        (302, "https://example.org/gmis/id/home", YjsxtLoginError),
    ],
)
@respx.mock
async def test_bad_login(cas_token, status, location, error):
    respx.get(YJSXT_FROM_CAS_URL).respond(302, headers={"location": TICKET})
    respx.get(TICKET).respond(
        status, headers={"location": location} if location is not None else {}
    )
    with pytest.raises(error):
        await acquire_by_cas_login(cas_token)


@respx.mock
async def test_cas_expired(cas_token):
    respx.get(YJSXT_FROM_CAS_URL).respond(200)
    with pytest.raises(CasTokenExpired):
        await acquire_by_cas_login(cas_token)
    assert len(respx.calls) == 1


@respx.mock
async def test_network_failure(cas_token):
    respx.get(YJSXT_FROM_CAS_URL).respond(302, headers={"location": TICKET})
    respx.get(TICKET).mock(side_effect=httpx.ConnectError("offline"))
    with pytest.raises(YjsxtNetworkError):
        await acquire_by_cas_login(cas_token)
