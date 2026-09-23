# src/hnu_query/ca/login.py
import httpx

from .token import CaToken
from .exceptions import CaLoginError

BASE_URL = "https://ca.hnu.edu.cn"


async def acquire_by_cas_login(cas_token) -> CaToken:
    """通过统一身份认证（CAS）登录可信电子凭证平台。

    Args:
        cas_token: 已获取的 ``CasToken``，携带 CAS 会话信息。

    Returns:
        携带 CA 平台 Cookie 的 ``CaToken``。
    """
    async with httpx.AsyncClient(
        base_url=BASE_URL,
        follow_redirects=True,
    ) as client:
        # 用 CAS token 访问 CA 平台，触发 CAS 回调并建立 CA 会话
        resp = await client.get(
            "/student/sys/common/view/index",
            cookies=cas_token.cookies,  # 假设 CasToken 持有 cookies
        )
        if resp.status_code >= 400:
              raise CaLoginError(f"CA 登录失败: HTTP {resp.status_code}")

        # 提取 CA 平台设置的 Cookie
        ca_cookies = {c.name: c.value for c in client.cookies.jar}
        return CaToken(headers={"Cookie": "; ".join(f"{k}={v}" for k, v in ca_cookies.items())})