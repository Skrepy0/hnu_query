from urllib.parse import urljoin, urlsplit

import httpx

from .exceptions import CgNavigationError, CgNetworkError, CgStatusError, TokenExpired

BASE_URL = "https://cg.hnu.edu.cn"


async def request(client: httpx.AsyncClient, method: str, url: str, **kwargs) -> httpx.Response:
    if url.startswith("/"):
        url = BASE_URL + url
    try:
        response = await client.request(method, url, follow_redirects=False, **kwargs)
    except httpx.RequestError as exc:
        raise CgNetworkError("CG 网络请求失败") from exc
    if response.status_code >= 400:
        raise CgStatusError(response.status_code)
    return response


def check_token_expired(response: httpx.Response) -> None:
    if response.status_code == 302:
        location = response.headers.get("location", "")
        if "simple.jsp" in location or "login" in location:
            raise TokenExpired("CG 会话已失效")


def redirect_url(response: httpx.Response) -> str:
    location = response.headers.get("location")
    if not location:
        raise CgNavigationError("CG 跳转响应缺少 Location")
    try:
        target = urljoin(str(response.url), location)
        parsed = urlsplit(target)
        port = parsed.port
    except ValueError as exc:
        raise CgNavigationError("CG 跳转地址格式错误") from exc
    if parsed.hostname != "cg.hnu.edu.cn" or parsed.scheme != "https" or port not in (None, 443):
        raise CgNavigationError("CG 跳转目标不属于平台 HTTPS 站点")
    return target


def require_status(response: httpx.Response, status: int = 200) -> None:
    if response.status_code != status:
        raise CgStatusError(response.status_code)
