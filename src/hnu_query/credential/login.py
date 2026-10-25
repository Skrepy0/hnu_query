from urllib.parse import parse_qs, urlsplit

import httpx

from hnu_query.cas import CasToken, get_ticket_url

from .client import CaClient
from .exceptions import CaLoginError
from .token import CaToken

CA_URL = "http://cas.hnu.edu.cn/cas/login?service=https://ca.hnu.edu.cn/student/"


async def acquire_by_cas_login(cas_token: CasToken) -> CaToken:
    """使用 CAS 票据兑换凭证会话；保留预取响应的 Cookie。"""
    ticket_url = await get_ticket_url(cas_token, CA_URL)
    try:
        target = urlsplit(ticket_url)
        if (
            target.scheme != "https"
            or target.hostname != "ca.hnu.edu.cn"
            or target.port not in (None, 443)
            or target.username is not None
            or target.password is not None
        ):
            raise ValueError
        tickets = parse_qs(target.query, keep_blank_values=True).get("ticket", [])
        if len(tickets) != 1 or not tickets[0]:
            raise ValueError
        ticket = tickets[0]
    except ValueError as exc:
        raise CaLoginError("凭证回调地址或 ticket 无效") from exc

    async with httpx.AsyncClient(timeout=30.0, follow_redirects=False) as http:
        async with CaClient(CaToken(), client=http) as client:
            # 仅跟随凭证域内的跳转，禁止向其他站点提交一次性票据。
            await _login_get(client, ticket_url)
            response = await _login_get(
                client,
                "https://ca.hnu.edu.cn/student/cas/client/validateLogin",
                params={
                    "ticket": ticket + "#/",
                    "service": "https://ca.hnu.edu.cn/student/",
                },
            )

    try:
        data = response.json()
    except ValueError as exc:
        raise CaLoginError("validateLogin 返回非 JSON") from exc
    if not isinstance(data, dict):
        raise CaLoginError("validateLogin 响应不是对象")
    if data.get("message") != "登录成功":
        raise CaLoginError("登录失败")
    result = data.get("result")
    token = result.get("token") if isinstance(result, dict) else None
    if (
        not isinstance(token, str)
        or not token
        or ";" in token
        or any(ord(char) < 33 or ord(char) > 126 for char in token)
    ):
        raise CaLoginError("找不到 token 或 token 无效")
    return CaToken(
        {
            "X-Access-Token": token,
            "Cookie": f"X-Access-Token={token}",
        }
    )


async def _login_get(client: CaClient, url: str, **kwargs) -> httpx.Response:
    # 与下载接口不同，票据兑换不能重定向到 CDN 或其他域。
    return await client._request(
        "GET",
        url,
        allowed_host="ca.hnu.edu.cn",
        **kwargs,
    )
