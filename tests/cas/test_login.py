import httpx
import pytest
import respx

from hnu_query.cas import acquire_by_login
from hnu_query.cas.exceptions import (
    CasNetworkError,
    CasStatusError,
    PasswordError,
    PasswordShouldChange,
    AccountLocked,
    TFARequired,
)
from tests.conftest import PUBKEY_URL, SERVICE_URL

# ---------- 登录页 HTML ----------

LOGIN_HTML = """
<form action="/cas/login" method="post">
    <input type="hidden" name="execution" value="e1s1_abc123"/>
    <input type="hidden" name="_eventId" value="submit"/>
</form>
"""

PUBKEY_JSON = '{"modulus": "00bf", "exponent": "10001"}'


# ---------- 成功 ----------

@pytest.mark.asyncio
@respx.mock
async def test_login_success():
    respx.get(SERVICE_URL).mock(
        return_value=httpx.Response(
            200,
            text=LOGIN_HTML,
            headers={"Set-Cookie": "TGC=tgt-1; Path=/cas/"},
        )
    )
    respx.get(PUBKEY_URL).mock(
        return_value=httpx.Response(
            200,
            text=PUBKEY_JSON,
            headers={"Set-Cookie": "_pv0=pv0-1; Path=/"},
        )
    )
    respx.post(SERVICE_URL).mock(
        return_value=httpx.Response(
            302,
            headers={
                "Location": "http://cas.hnu.edu.cn/cas/login?ticket=ST-1",
                "Set-Cookie": "JSESSIONID=js-1; Path=/",
            },
        )
    )

    token = await acquire_by_login("20210001", "password")

    # 最终 cookie = POST 响应 + _pv0（TGC 被丢弃）
    assert "JSESSIONID=js-1" in token.cookie
    assert "_pv0=pv0-1" in token.cookie
    assert token.stu_id == "20210001"


# ---------- 密码错误 ----------

@pytest.mark.asyncio
@respx.mock
async def test_login_wrong_password():
    respx.get(SERVICE_URL).mock(
        return_value=httpx.Response(200, text=LOGIN_HTML)
    )
    respx.get(PUBKEY_URL).mock(
        return_value=httpx.Response(200, text=PUBKEY_JSON)
    )
    respx.post(SERVICE_URL).mock(
        return_value=httpx.Response(200, text="<html>用户名或密码错误</html>")
    )

    with pytest.raises(PasswordError):
        await acquire_by_login("20210001", "wrong")


# ---------- 账号锁定 ----------

@pytest.mark.asyncio
@respx.mock
async def test_login_account_locked():
    respx.get(SERVICE_URL).mock(
        return_value=httpx.Response(200, text=LOGIN_HTML)
    )
    respx.get(PUBKEY_URL).mock(
        return_value=httpx.Response(200, text=PUBKEY_JSON)
    )
    respx.post(SERVICE_URL).mock(
        return_value=httpx.Response(403, text="Forbidden")
    )

    with pytest.raises(AccountLocked):
        await acquire_by_login("20210001", "password")


# ---------- 需要改密码 ----------

@pytest.mark.asyncio
@respx.mock
async def test_login_password_should_change():
    respx.get(SERVICE_URL).mock(
        return_value=httpx.Response(200, text=LOGIN_HTML)
    )
    respx.get(PUBKEY_URL).mock(
        return_value=httpx.Response(200, text=PUBKEY_JSON)
    )
    respx.post(SERVICE_URL).mock(
        return_value=httpx.Response(
            302,
            headers={
                "Location": "http://cas.hnu.edu.cn/securitycenter/modifyPwd/index.zf",
                "Set-Cookie": "JSESSIONID=js-1; Path=/",
            },
        )
    )

    with pytest.raises(PasswordShouldChange):
        await acquire_by_login("20210001", "password")


# ---------- 需要双因子认证 ----------

@pytest.mark.asyncio
@respx.mock
async def test_login_tfa_required():
    tfa_html = """
    <html><body>
        <h1>双因子认证</h1>
        <input id="phone" name="username" value="13800138000"/>
        <input type="hidden" name="execution" value="tfa-exec-abc"/>
    </body></html>
    """
    respx.get(SERVICE_URL).mock(
        return_value=httpx.Response(200, text=LOGIN_HTML)
    )
    respx.get(PUBKEY_URL).mock(
        return_value=httpx.Response(200, text=PUBKEY_JSON)
    )
    respx.post(SERVICE_URL).mock(
        return_value=httpx.Response(200, text=tfa_html)
    )

    with pytest.raises(TFARequired) as exc:
        await acquire_by_login("20210001", "password")

    tfa = exc.value.tfa_token
    assert tfa.phone == "13800138000"
    assert tfa.execution == "tfa-exec-abc"
    assert tfa.stu_id == "20210001"


# ---------- 网络与状态码错误 ----------

@pytest.mark.asyncio
@respx.mock
async def test_login_initial_network_error():
    respx.get(SERVICE_URL).mock(side_effect=httpx.ConnectError("refused"))

    with pytest.raises(CasNetworkError):
        await acquire_by_login("20210001", "password")


@pytest.mark.asyncio
@respx.mock
async def test_login_initial_status_error():
    respx.get(SERVICE_URL).mock(
        return_value=httpx.Response(500, text="Server Error")
    )

    with pytest.raises(CasStatusError):
        await acquire_by_login("20210001", "password")


@pytest.mark.asyncio
@respx.mock
async def test_login_pubkey_invalid_json():
    respx.get(SERVICE_URL).mock(
        return_value=httpx.Response(200, text=LOGIN_HTML)
    )
    respx.get(PUBKEY_URL).mock(
        return_value=httpx.Response(200, text="not json")
    )

    with pytest.raises(CasNetworkError, match="非 JSON"):
        await acquire_by_login("20210001", "password")


@pytest.mark.asyncio
@respx.mock
async def test_login_password_encrypted():
    """确认提交的是 RSA 加密后的密码，不是明文。"""
    route_login_page = respx.get(SERVICE_URL).mock(
        return_value=httpx.Response(200, text=LOGIN_HTML)
    )
    respx.get(PUBKEY_URL).mock(
        return_value=httpx.Response(200, text=PUBKEY_JSON)
    )
    route_post = respx.post(SERVICE_URL).mock(
        return_value=httpx.Response(
            302,
            headers={
                "Location": "http://cas.hnu.edu.cn/cas/home",
                "Set-Cookie": "JSESSIONID=js-1; Path=/",
            },
        )
    )

    await acquire_by_login("20210001", "plaintext-password")

    body = route_post.calls.last.request.content.decode()
    assert "plaintext-password" not in body
    assert "username=20210001" in body
    assert "execution=e1s1_abc123" in body
    assert "_eventId=submit" in body
