from urllib.parse import parse_qs

import httpx
import pytest
import respx

from hnu_query.cas import TokenExpired as CasTokenExpired
from hnu_query.netflow import (
    NetflowLoginError,
    NetflowNetworkError,
    NetflowStatusError,
    NetflowToken,
    acquire_by_cas_login,
)
from hnu_query.netflow._http import BASE_URL
from hnu_query.netflow.login import NETFLOW_URL

CALLBACK = "https://cas.hnu.edu.cn/sprcialapp/zf_form/index.zf?login=netflow&s_ticket=ST%2Btest"


def cas_redirect():
    return respx.get(NETFLOW_URL).respond(
        302,
        headers={
            "location": CALLBACK,
            "set-cookie": "route=cas-node; Path=/",
        },
    )


@pytest.mark.parametrize("status", [200, 302])
@respx.mock
async def test_login_get_body_and_selected_cookies(cas_token, status):
    cas_redirect()
    route = respx.get(BASE_URL + "/login/validate").respond(
        status,
        headers=[
            ("set-cookie", "ASP.NET_SessionId=session; Path=/"),
            ("set-cookie", ".ASPXAUTH=old1; Path=/"),
            ("set-cookie", ".ASPXAUTH=old2; Path=/"),
            ("set-cookie", ".ASPXAUTH=valid; Path=/"),
            ("location", "/home"),
        ],
    )
    token = await NetflowToken.acquire_by_cas_login(cas_token)
    assert token.headers["Cookie"] == "ASP.NET_SessionId=session; .ASPXAUTH=valid"
    request = route.calls.last.request
    assert request.method == "GET"
    assert not request.url.query
    assert request.headers["content-type"] == "application/x-www-form-urlencoded"
    assert parse_qs(request.content.decode(), keep_blank_values=True) == {
        "s_ticket": ["ST+test"],
        "login_id": [cas_token.stu_id],
        "password": [""],
        "null": [""],
    }
    assert "route=cas-node" in request.headers["cookie"]
    assert "TGC=tgt-fake" in request.headers["cookie"]
    assert len(respx.calls) == 2


@respx.mock
async def test_single_cookie_preserves_rust_behavior(cas_token):
    cas_redirect()
    respx.get(BASE_URL + "/login/validate").respond(200, headers={"set-cookie": "session=one"})
    token = await acquire_by_cas_login(cas_token)
    assert token.headers["Cookie"] == "session=one; session=one"


@respx.mock
async def test_no_cookie(cas_token):
    cas_redirect()
    respx.get(BASE_URL + "/login/validate").respond(200)
    with pytest.raises(NetflowLoginError):
        await acquire_by_cas_login(cas_token)


@respx.mock
async def test_cas_expired(cas_token):
    respx.get(NETFLOW_URL).respond(200)
    with pytest.raises(CasTokenExpired):
        await acquire_by_cas_login(cas_token)
    assert len(respx.calls) == 1


@respx.mock
async def test_login_http_error(cas_token):
    cas_redirect()
    respx.get(BASE_URL + "/login/validate").respond(500)
    with pytest.raises(NetflowStatusError):
        await acquire_by_cas_login(cas_token)


@respx.mock
async def test_login_network_error(cas_token):
    cas_redirect()
    respx.get(BASE_URL + "/login/validate").mock(side_effect=httpx.ConnectError("offline"))
    with pytest.raises(NetflowNetworkError):
        await acquire_by_cas_login(cas_token)
