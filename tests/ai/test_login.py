import json

import httpx
import pytest
import respx

from hnu_query.ai import (
    AiLoginError,
    AiNetworkError,
    AiParseError,
    AiStatusError,
    AiToken,
    acquire_by_cas_login,
)
from hnu_query.ai._http import BASE_URL
from hnu_query.ai.login import INITIAL_AUTH_URL, OAUTH_LOGIN_URL
from hnu_query.cas import TokenExpired as CasTokenExpired

CAS_URL = "https://cas.hnu.edu.cn/cas/login?service=ai"
TICKET_URL = "https://deepseek.hnu.edu.cn:5556/finish?ticket=ST-test"
CALLBACK = BASE_URL + "/callback?code=a%2Bb%20c"


@respx.mock
async def test_oauth_cas_and_domain_cookie_flow(cas_token):
    initial = respx.get(INITIAL_AUTH_URL).respond(
        302, headers={"location": CAS_URL, "set-cookie": "oauth=deepseek; Path=/"}
    )
    cas = respx.get(CAS_URL).mock(
        side_effect=[
            httpx.Response(200, headers={"set-cookie": "JSESSIONID=anonymous; Path=/"}),
            httpx.Response(302, headers={"location": TICKET_URL}),
        ]
    )
    ticket = respx.get(TICKET_URL).respond(303, headers={"location": CALLBACK})
    callback = respx.get(CALLBACK).respond(
        200, headers={"set-cookie": "session=old; Path=/api; Secure"}
    )
    exchange = respx.post(OAUTH_LOGIN_URL).respond(
        json={"data": {"token": "bearer-value"}},
        headers={"set-cookie": "session=new; Path=/api; Secure"},
    )
    token = await AiToken.acquire_by_cas_login(cas_token)
    assert token.headers == {
        "Authorization": "Bearer bearer-value",
        "Cookie": "session=new",
    }
    assert "cookie" not in initial.calls.last.request.headers
    for call in cas.calls:
        assert call.request.headers["cookie"] == cas_token.cookie
    assert ticket.calls.last.request.headers["cookie"] == "oauth=deepseek"
    assert "cookie" not in callback.calls.last.request.headers
    assert exchange.calls.last.request.headers["cookie"] == "session=old"
    assert json.loads(exchange.calls.last.request.content) == {"code": "a+b c"}
    assert len(respx.calls) == 6


@respx.mock
async def test_already_authenticated_and_relative_location(cas_token):
    respx.get(INITIAL_AUTH_URL).respond(302, headers={"location": "/finish"})
    respx.get("https://deepseek.hnu.edu.cn:5556/finish").respond(
        303, headers={"location": CALLBACK}
    )
    respx.get(CALLBACK).respond(200)
    respx.post(OAUTH_LOGIN_URL).respond(json={"data": {"token": "bearer"}})
    token = await acquire_by_cas_login(cas_token)
    assert token.headers == {"Authorization": "Bearer bearer"}


@pytest.mark.parametrize(
    "location",
    [
        "https://example.org/callback?code=secret",
        "https://maas.nscc-cs.cn.evil.example/callback?code=secret",
        "https://user:pass@maas.nscc-cs.cn/callback",
        "http://cas.hnu.edu.cn/cas/login",
        "https://deepseek.hnu.edu.cn:9999/auth",
        "https://maas.nscc-cs.cn:bad/callback",
        "//evil.example/callback",
    ],
)
@respx.mock
async def test_reject_foreign_or_insecure_redirect(cas_token, location):
    respx.get(INITIAL_AUTH_URL).respond(302, headers={"location": location})
    with pytest.raises(AiLoginError):
        await acquire_by_cas_login(cas_token)
    assert len(respx.calls) == 1


@respx.mock
async def test_redirect_limit_even_if_final_url_has_code(cas_token):
    route = respx.get(INITIAL_AUTH_URL).mock(
        side_effect=[
            *[
                httpx.Response(302, headers={"location": INITIAL_AUTH_URL})
                for _ in range(9)
            ],
            httpx.Response(302, headers={"location": CALLBACK}),
        ]
    )
    with pytest.raises(AiLoginError, match="\u6b21\u6570"):
        await acquire_by_cas_login(cas_token)
    assert route.call_count == 10


@respx.mock
async def test_expired_cas_propagates(cas_token):
    respx.get(INITIAL_AUTH_URL).respond(302, headers={"location": CAS_URL})
    route = respx.get(CAS_URL).respond(200)
    with pytest.raises(CasTokenExpired):
        await acquire_by_cas_login(cas_token)
    assert route.call_count == 2


@respx.mock
async def test_repeated_cas_page_fails(cas_token):
    respx.get(INITIAL_AUTH_URL).respond(302, headers={"location": CAS_URL})
    respx.get(CAS_URL).mock(
        side_effect=[
            httpx.Response(200),
            httpx.Response(302, headers={"location": CAS_URL}),
            httpx.Response(200),
        ]
    )
    with pytest.raises(AiLoginError):
        await acquire_by_cas_login(cas_token)


@pytest.mark.parametrize(
    "url",
    [
        BASE_URL + "/callback",
        BASE_URL + "/callback?code=",
        BASE_URL + "/callback?code=one&code=two",
        BASE_URL + "/callback?code=one&code=",
        BASE_URL + "/other?code=one",
    ],
)
@respx.mock
async def test_invalid_callback(cas_token, url):
    respx.get(INITIAL_AUTH_URL).respond(302, headers={"location": url})
    respx.get(url).respond(200)
    with pytest.raises(AiLoginError):
        await acquire_by_cas_login(cas_token)


@pytest.mark.parametrize(
    "status,error",
    [
        (200, AiLoginError),
        (302, AiLoginError),
        (500, AiStatusError),
        (307, AiStatusError),
    ],
)
@respx.mock
async def test_unexpected_initial_response(cas_token, status, error):
    respx.get(INITIAL_AUTH_URL).respond(status)
    with pytest.raises(error):
        await acquire_by_cas_login(cas_token)


@pytest.mark.parametrize(
    "status,body,error",
    [
        (500, {}, AiStatusError),
        (302, {}, AiLoginError),
        (200, {}, AiParseError),
        (200, {"data": {"token": ""}}, AiParseError),
    ],
)
@respx.mock
async def test_exchange_failure(cas_token, status, body, error):
    respx.get(INITIAL_AUTH_URL).respond(302, headers={"location": CALLBACK})
    respx.get(CALLBACK).respond(200)
    respx.post(OAUTH_LOGIN_URL).respond(status, json=body)
    with pytest.raises(error):
        await acquire_by_cas_login(cas_token)


@pytest.mark.parametrize("phase", ["authorize", "exchange"])
@respx.mock
async def test_network_failure(cas_token, phase):
    if phase == "authorize":
        route = respx.get(INITIAL_AUTH_URL)
    else:
        respx.get(INITIAL_AUTH_URL).respond(302, headers={"location": CALLBACK})
        respx.get(CALLBACK).respond(200)
        route = respx.post(OAUTH_LOGIN_URL)
    route.mock(side_effect=httpx.ConnectError("offline"))
    with pytest.raises(AiNetworkError):
        await acquire_by_cas_login(cas_token)
