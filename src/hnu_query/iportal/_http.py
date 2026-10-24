import httpx

from .exceptions import IPortalNetworkError, IPortalStatusError, IPortalTokenExpired

BASE_URL = "https://iportal.hnu.edu.cn"


async def request(
    client: httpx.AsyncClient, url: str, *, login: bool = False, **kwargs
) -> httpx.Response:
    if url.startswith("/"):
        url = BASE_URL + url
    try:
        response = await client.get(url, follow_redirects=False, **kwargs)
    except httpx.RequestError as exc:
        raise IPortalNetworkError("新门户网络请求失败") from exc
    if response.status_code == 302 and not login:
        raise IPortalTokenExpired("新门户会话已失效")
    if not 200 <= response.status_code < 300 and not (login and response.is_redirect):
        raise IPortalStatusError(response.status_code)
    return response
