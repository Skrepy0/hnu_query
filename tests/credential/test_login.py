# tests/ca/test_login.py
import httpx
import pytest
import respx

from hnu_query.credential import acquire_by_cas_login
from hnu_query.credential.exceptions import CaLoginError

BASE = "https://ca.hnu.edu.cn"


class FakeCasToken:
    """模拟 CasToken，只暴露测试需要的字段。"""
    def __init__(self, cookies: dict[str, str]):
        self.cookies = cookies


@pytest.mark.asyncio
@respx.mock
async def test_acquire_by_cas_login_success():
    respx.get(f"{BASE}/student/sys/common/view/index").mock(
        return_value=httpx.Response(
            200,
            text="ok",
            headers={"Set-Cookie": "CA_SESSION=ca-sess-001; Path=/"},
        )
    )

    cas_token = FakeCasToken(cookies={"CAS_SESSION": "cas-abc"})
    ca_token = await acquire_by_cas_login(cas_token)

    assert "CA_SESSION=ca-sess-001" in ca_token.headers["Cookie"]
    assert ca_token.is_empty() is False


@pytest.mark.asyncio
@respx.mock
async def test_acquire_by_cas_login_failure():
    respx.get(f"{BASE}/student/sys/common/view/index").mock(
        return_value=httpx.Response(403, text="Forbidden")
    )

    cas_token = FakeCasToken(cookies={"CAS_SESSION": "cas-abc"})
    with pytest.raises(CaLoginError):
        await acquire_by_cas_login(cas_token)