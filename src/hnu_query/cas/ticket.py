from urllib.parse import parse_qs, urljoin, urlsplit

import httpx

from .exceptions import CasNetworkError, CasStatusError, TokenExpired
from .token import CasToken

REDIRECT_CODES = (302,)


async def get_ticket_url(cas_token: CasToken, service_url: str) -> str:
    """为服务申请 Service Ticket，返回回调 URL。

    对应 Rust ``CasToken::get_ticket_url``。

    状态码规则（严格照搬 Rust）：
      - 200 / 4xx / 5xx → 会话过期
      - 非 302 的其他状态 → 意外错误
      - 302 → 从 Location 提取 ticket_url
    """
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=False) as client:
        try:
            res = await client.get(
                service_url,
                headers={"Cookie": cas_token.cookie},
            )
        except httpx.RequestError as e:
            raise CasNetworkError(str(e)) from e

    status = res.status_code
    if status == 200 or 400 <= status < 600:
        raise TokenExpired("CAS 会话已过期")

    if status not in REDIRECT_CODES:
        raise CasStatusError(status, res.text[:200])

    location = res.headers.get("Location")
    if not location:
        raise CasStatusError(status, "没有在 location 中找到 ticket_url")

    return location


def extract_ticket(ticket_url: str) -> str:
    """从 ticket_url 中提取 ticket 值。

    对应 Rust ``ticket_url.split("ticket=").nth(1)``。
    """
    if "ticket=" not in ticket_url:
        raise ValueError("ticket not found in ticket_url")
    return ticket_url.split("ticket=", 1)[1]


async def get_sticket(cas_token: CasToken, service_url: str) -> tuple[str, str]:
    """最多经过六次 CAS 跳转，返回 ``(s_ticket, 回调路径适用的 Cookie)``。

    对应 Rust ``CasToken::get_sticket``，用于体测等应用的 SSO。
    """
    current = service_url
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=False) as client:
        # CAS 与门户都使用 JSESSIONID，但 Path 不同，不能只按名称覆盖。
        for item in cas_token.cookie.split(";"):
            if "=" in item:
                key, value = item.strip().split("=", 1)
                client.cookies.set(key, value, domain="cas.hnu.edu.cn", path="/")
        for attempt in range(7):
            parsed = urlsplit(current)
            if parsed.hostname != "cas.hnu.edu.cn" or parsed.scheme not in (
                "http",
                "https",
            ):
                raise CasStatusError(302, "s_ticket 重定向目标不属于 CAS")
            if parsed.path == "/sprcialapp/zf_form/index.zf":
                ticket = parse_qs(parsed.query).get("s_ticket", [""])[0]
                if not ticket:
                    raise CasStatusError(302, "CAS 回调缺少 s_ticket")
                callback = client.build_request("GET", current)
                return ticket, callback.headers.get("cookie", "")
            if attempt == 6:
                break
            try:
                response = await client.get(current)
            except httpx.RequestError as exc:
                raise CasNetworkError("获取 s_ticket 时网络请求失败") from exc
            if response.status_code == 200:
                raise TokenExpired("CAS 会话已过期")
            if response.status_code != 302:
                raise CasStatusError(response.status_code, "获取 s_ticket 时状态码异常")
            location = response.headers.get("location")
            if not location:
                raise CasStatusError(302, "获取 s_ticket 时缺少 Location")
            current = urljoin(current, location)
    raise CasStatusError(302, "超过 s_ticket 重定向次数限制")
