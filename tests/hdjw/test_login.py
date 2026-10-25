import httpx
import pytest
import respx

from hnu_query.cas import TokenExpired as CasTokenExpired
from hnu_query.hdjw import HdjwLoginError, HdjwToken, acquire_by_cas_login
from hnu_query.hdjw.login import HDJW_ENTER_URL, HDJW_FROM_CAS_URL

TICKET = HDJW_ENTER_URL + "?ticket=ST-test"
TARGET = "http://hdjw.hnu.edu.cn/jsxsd/framework/xsMain.jsp"


def mock_login(location=TARGET, status=302):
    respx.get(HDJW_FROM_CAS_URL).respond(302, headers={"location": TICKET})
    respx.get(TICKET).respond(302, headers={"location": HDJW_ENTER_URL})
    entry = respx.get(HDJW_ENTER_URL, params={}).mock(
        side_effect=[
            httpx.Response(200, headers={"set-cookie": "JSESSIONID=initial; Path=/"}),
            httpx.Response(status, headers={"location": location}),
        ]
    )
    return entry


@respx.mock
async def test_login_sequence(cas_token):
    entry = mock_login()
    final = respx.get(TARGET).respond(
        200,
        headers=[
            ("set-cookie", "JSESSIONID=authenticated; Path=/"),
            ("set-cookie", "route=node1; Path=/"),
        ],
    )
    token = await HdjwToken.acquire_by_cas_login(cas_token)
    assert token.headers["Cookie"] == "JSESSIONID=authenticated; route=node1"
    assert entry.call_count == 2
    assert final.calls.last.request.headers["cookie"] == "JSESSIONID=initial"
    assert respx.calls[1].request.headers["cookie"] == cas_token.cookie
    assert respx.calls[2].request.headers["cookie"] == "JSESSIONID=initial"


@respx.mock
async def test_relative_redirect(cas_token):
    mock_login("/jsxsd/framework/xsMain.jsp")
    respx.get(TARGET).respond(200, headers={"set-cookie": "auth=ok"})
    token = await acquire_by_cas_login(cas_token)
    assert "auth=ok" in token.headers["Cookie"]


@respx.mock
async def test_final_redirect_can_issue_auth_cookie(cas_token):
    mock_login()
    respx.get(TARGET).respond(302, headers={"set-cookie": "auth=ok", "location": "/home"})
    token = await acquire_by_cas_login(cas_token)
    assert "auth=ok" in token.headers["Cookie"]


@pytest.mark.parametrize(
    "location,status", [(TARGET, 200), ("", 302), ("https://example.org/", 302)]
)
@respx.mock
async def test_bad_redirect(cas_token, location, status):
    mock_login(location, status)
    with pytest.raises(HdjwLoginError):
        await acquire_by_cas_login(cas_token)


@respx.mock
async def test_expired_cas(cas_token):
    respx.get(HDJW_ENTER_URL).respond(200, headers={"set-cookie": "JSESSIONID=init"})
    respx.get(HDJW_FROM_CAS_URL).respond(200)
    with pytest.raises(CasTokenExpired):
        await acquire_by_cas_login(cas_token)


@respx.mock
async def test_missing_cookie(cas_token):
    respx.get(HDJW_ENTER_URL).respond(200)
    with pytest.raises(HdjwLoginError):
        await acquire_by_cas_login(cas_token)
