import httpx
import pytest
import respx

from hnu_query.cas import CasToken, TFAToken
from hnu_query.cas.exceptions import CasNetworkError, CasStatusError

CAS_BASE = "https://cas.hnu.edu.cn"
SMS_URL = f"{CAS_BASE}/cas/syz/services/sedsms"
LOGIN_URL = f"{CAS_BASE}/cas/login"

TFA_HTML = """
<form>
    <input id="phone" name="username" value="13800138000"/>
    <input type="hidden" name="execution" value="tfa-exec-xyz"/>
</form>
"""


@pytest.fixture
def tfa_token():
    return TFAToken(
        phone="13800138000",
        execution="tfa-exec-xyz",
        cookie="TGC=tgt-fake; JSESSIONID=js-fake",
        stu_id="20210001",
        password="password",
    )


# ---------- from_html ----------


def test_tfa_from_html_success():
    token = TFAToken.from_html(TFA_HTML, "cookie-x", "20210001", "pwd")
    assert token.phone == "13800138000"
    assert token.execution == "tfa-exec-xyz"
    assert token.cookie == "cookie-x"
    assert token.stu_id == "20210001"


def test_tfa_from_html_no_execution():
    from hnu_query.cas.exceptions import CasLoginError

    with pytest.raises(CasLoginError, match="execution"):
        TFAToken.from_html("<html></html>", "c", "s", "p")


def test_tfa_from_html_no_phone():
    from hnu_query.cas.exceptions import CasLoginError

    html = '<input type="hidden" name="execution" value="x"/>'
    with pytest.raises(CasLoginError, match="手机号"):
        TFAToken.from_html(html, "c", "s", "p")


# ---------- send_sms ----------


@pytest.mark.asyncio
@respx.mock
async def test_send_sms_success(tfa_token):
    respx.get(SMS_URL).mock(return_value=httpx.Response(200, text="success"))
    assert await tfa_token.send_sms() == "success"


@pytest.mark.asyncio
@respx.mock
async def test_send_sms_valid(tfa_token):
    respx.get(SMS_URL).mock(return_value=httpx.Response(200, text="valid"))
    assert await tfa_token.send_sms() == "valid"


@pytest.mark.asyncio
@respx.mock
async def test_send_sms_other(tfa_token):
    respx.get(SMS_URL).mock(return_value=httpx.Response(200, text="unknown"))
    assert await tfa_token.send_sms() == "unknown"


@pytest.mark.asyncio
@respx.mock
async def test_send_sms_network_error(tfa_token):
    respx.get(SMS_URL).mock(side_effect=httpx.ConnectError("refused"))
    with pytest.raises(CasNetworkError):
        await tfa_token.send_sms()


@pytest.mark.asyncio
@respx.mock
async def test_send_sms_status_error(tfa_token):
    respx.get(SMS_URL).mock(return_value=httpx.Response(500, text="err"))
    with pytest.raises(CasStatusError):
        await tfa_token.send_sms()


# ---------- verify ----------


@pytest.mark.asyncio
@respx.mock
async def test_verify_success(tfa_token):
    """302 → 验证通过，返回新的 CasToken。"""
    respx.post(LOGIN_URL).mock(
        return_value=httpx.Response(
            302,
            headers={
                "Location": "http://cas.hnu.edu.cn/",
                "Set-Cookie": "TGC=tgt-new; Path=/cas/",
            },
        )
    )

    status, value = await tfa_token.verify("123456")
    assert status == "success"
    assert isinstance(value, CasToken)
    assert "TGC=tgt-new" in value.cookie
    assert value.stu_id == "20210001"


@pytest.mark.asyncio
@respx.mock
async def test_verify_code_error(tfa_token):
    """200 + 验证码错误 → 返回新的 TFAToken。"""
    error_html = """
    <html>
      <p>验证码错误，请重新输入！</p>
      <input id="phone" name="username" value="13800138000"/>
      <input type="hidden" name="execution" value="new-exec-abc"/>
    </html>
    """
    respx.post(LOGIN_URL).mock(return_value=httpx.Response(200, text=error_html))

    status, value = await tfa_token.verify("000000")
    assert status == "code_error"
    assert isinstance(value, TFAToken)
    assert value.execution == "new-exec-abc"


@pytest.mark.asyncio
@respx.mock
async def test_verify_expired(tfa_token):
    """200 但页面不是验证码错误 → TFA 令牌过期。"""
    respx.post(LOGIN_URL).mock(return_value=httpx.Response(200, text="<html>其他错误</html>"))

    status, value = await tfa_token.verify("123456")
    assert status == "expired"
    assert value is None
