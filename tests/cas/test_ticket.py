import httpx
import pytest
import respx

from hnu_query.cas import extract_ticket, get_ticket_url
from hnu_query.cas.exceptions import (
    CasNetworkError,
    CasStatusError,
    TokenExpired,
)

CAS_LOGIN = "http://cas.hnu.edu.cn/cas/login"
CA_URL = "http://cas.hnu.edu.cn/cas/login?service=https://ca.hnu.edu.cn/student/"
TICKET_URL = "https://ca.hnu.edu.cn/student/?ticket=ST-abc-123"


# ---------- extract_ticket ----------


def test_extract_ticket_simple():
    assert extract_ticket("https://x/y?ticket=ST-abc") == "ST-abc"


def test_extract_ticket_with_extra_params():
    # Rust 的 split("ticket=").nth(1) 取后面全部
    assert extract_ticket("https://x/y?ticket=ST-1&foo=2") == "ST-1&foo=2"


def test_extract_ticket_missing():
    with pytest.raises(ValueError):
        extract_ticket("https://x/y")


# ---------- get_ticket_url ----------


@pytest.mark.asyncio
@respx.mock
async def test_get_ticket_url_success(cas_token):
    respx.get(CA_URL).mock(
        return_value=httpx.Response(
            302,
            headers={"Location": TICKET_URL},
        )
    )

    url = await get_ticket_url(cas_token, CA_URL)
    assert url == TICKET_URL


@pytest.mark.asyncio
@respx.mock
async def test_get_ticket_url_session_expired_200(cas_token):
    """200 表示 CAS 会话失效（返回登录页而不是 302）。"""
    respx.get(CA_URL).mock(return_value=httpx.Response(200, text="<html>login</html>"))

    with pytest.raises(TokenExpired):
        await get_ticket_url(cas_token, CA_URL)


@pytest.mark.asyncio
@respx.mock
async def test_get_ticket_url_session_expired_401(cas_token):
    """4xx 也视为会话失效（Rust 的保守策略）。"""
    respx.get(CA_URL).mock(return_value=httpx.Response(401, text="Unauthorized"))

    with pytest.raises(TokenExpired):
        await get_ticket_url(cas_token, CA_URL)


@pytest.mark.asyncio
@respx.mock
async def test_get_ticket_url_session_expired_500(cas_token):
    """5xx 同样视为会话失效。"""
    respx.get(CA_URL).mock(return_value=httpx.Response(500, text="Server Error"))

    with pytest.raises(TokenExpired):
        await get_ticket_url(cas_token, CA_URL)


@pytest.mark.asyncio
@respx.mock
async def test_get_ticket_url_no_location(cas_token):
    """302 但没有 Location → CasStatusError。"""
    respx.get(CA_URL).mock(return_value=httpx.Response(302))

    with pytest.raises(CasStatusError):
        await get_ticket_url(cas_token, CA_URL)


@pytest.mark.asyncio
@respx.mock
async def test_get_ticket_url_network_error(cas_token):
    respx.get(CA_URL).mock(side_effect=httpx.ConnectError("refused"))

    with pytest.raises(CasNetworkError):
        await get_ticket_url(cas_token, CA_URL)


@pytest.mark.asyncio
@respx.mock
async def test_get_ticket_url_sends_cookie(cas_token):
    """确认请求带上了 CasToken 的 Cookie。"""
    route = respx.get(CA_URL).mock(
        return_value=httpx.Response(302, headers={"Location": TICKET_URL})
    )

    await get_ticket_url(cas_token, CA_URL)

    assert route.calls.last.request.headers["Cookie"] == cas_token.cookie
