import httpx
import pytest
import respx

from hnu_query.credential import acquire_by_cas_login
from hnu_query.credential.exceptions import CaLoginError, CaStatusError

BASE = "https://ca.hnu.edu.cn"

#: acquire_by_cas_login 内部传给 get_ticket_url 的 CAS 登录 URL
CAS_LOGIN_URL = "http://cas.hnu.edu.cn/cas/login?service=https://ca.hnu.edu.cn/student/"

#: CAS 302 后回调的 ticket_url
TICKET_URL = f"{BASE}/student/?ticket=ST-fake-123"


class FakeCasToken:
    """模拟 CasToken，只暴露 cookie 和 stu_id 字段。"""

    def __init__(self, cookie: str = "TGC=fake; JSESSIONID=fake"):
        self.cookie = cookie
        self.stu_id = "20210001"


def _mock_cas_login_ok():
    """mock CAS 登录：GET CAS_LOGIN_URL → 302 到 TICKET_URL。"""
    respx.get(CAS_LOGIN_URL).mock(
        return_value=httpx.Response(
            302,
            headers={"Location": TICKET_URL},
        )
    )


@pytest.mark.asyncio
@respx.mock
async def test_acquire_by_cas_login_success():
    """完整流程：CAS 302 → GET ticket_url → validateLogin → CaToken。"""
    _mock_cas_login_ok()

    # GET ticket_url 建立会话
    respx.get(TICKET_URL).mock(
        return_value=httpx.Response(
            200,
            text="redirected",
            headers={"Set-Cookie": "CA_SESSION=ca-sess-001; Path=/"},
        )
    )

    # validateLogin 返回 JSON
    respx.get(url__startswith=f"{BASE}/student/cas/client/validateLogin").mock(
        return_value=httpx.Response(
            200,
            json={
                "message": "登录成功",
                "result": {"token": "eyJhbGciOiJIUzI1NiJ9.fake-token"},
            },
        )
    )

    cas_token = FakeCasToken()
    ca_token = await acquire_by_cas_login(cas_token)

    assert ca_token.headers["X-Access-Token"] == "eyJhbGciOiJIUzI1NiJ9.fake-token"
    assert ca_token.headers["Cookie"] == "X-Access-Token=eyJhbGciOiJIUzI1NiJ9.fake-token"
    assert ca_token.is_empty() is False


@pytest.mark.asyncio
@respx.mock
async def test_acquire_by_cas_login_cas_session_expired():
    """CAS 返回 200（会话已过期）→ TokenExpired。"""
    from hnu_query.cas.exceptions import TokenExpired

    respx.get(CAS_LOGIN_URL).mock(
        return_value=httpx.Response(200, text="<html>CAS login page</html>")
    )

    cas_token = FakeCasToken()
    with pytest.raises(TokenExpired):
        await acquire_by_cas_login(cas_token)


@pytest.mark.asyncio
@respx.mock
async def test_acquire_by_cas_login_ticket_url_fails():
    """GET ticket_url 返回 4xx → CaStatusError。"""
    _mock_cas_login_ok()
    respx.get(TICKET_URL).mock(return_value=httpx.Response(403, text="Forbidden"))

    cas_token = FakeCasToken()
    with pytest.raises(CaStatusError) as exc:
        await acquire_by_cas_login(cas_token)

    assert exc.value.status_code == 403


@pytest.mark.asyncio
@respx.mock
async def test_acquire_by_cas_login_message_failure():
    """validateLogin 返回 message != 登录成功 → CaLoginError。"""
    _mock_cas_login_ok()
    respx.get(TICKET_URL).mock(return_value=httpx.Response(200))
    respx.get(url__startswith=f"{BASE}/student/cas/client/validateLogin").mock(
        return_value=httpx.Response(
            200,
            json={
                "message": "ticket 已过期",
                "result": {},
            },
        )
    )

    cas_token = FakeCasToken()
    with pytest.raises(CaLoginError, match="登录失败"):
        await acquire_by_cas_login(cas_token)


@pytest.mark.asyncio
@respx.mock
async def test_acquire_by_cas_login_missing_token():
    """validateLogin 没有 token 字段 → CaLoginError。"""
    _mock_cas_login_ok()
    respx.get(TICKET_URL).mock(return_value=httpx.Response(200))
    respx.get(url__startswith=f"{BASE}/student/cas/client/validateLogin").mock(
        return_value=httpx.Response(
            200,
            json={
                "message": "登录成功",
                "result": {},
            },
        )
    )

    cas_token = FakeCasToken()
    with pytest.raises(CaLoginError, match="找不到 token"):
        await acquire_by_cas_login(cas_token)


@pytest.mark.asyncio
@respx.mock
async def test_acquire_by_cas_login_returns_html():
    """validateLogin 返回 HTML（ticket 失效）→ CaLoginError。"""
    _mock_cas_login_ok()
    respx.get(TICKET_URL).mock(return_value=httpx.Response(200))
    respx.get(url__startswith=f"{BASE}/student/cas/client/validateLogin").mock(
        return_value=httpx.Response(
            200,
            text="<html>CAS login page</html>",
            headers={"content-type": "text/html"},
        )
    )

    cas_token = FakeCasToken()
    with pytest.raises(CaLoginError, match="非 JSON"):
        await acquire_by_cas_login(cas_token)
