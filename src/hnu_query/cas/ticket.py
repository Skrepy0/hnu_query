import httpx

from .exceptions import CasNetworkError, CasStatusError, TokenExpired
from .token import CasToken

REDIRECT_CODES = (301, 302, 303, 307, 308)


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
