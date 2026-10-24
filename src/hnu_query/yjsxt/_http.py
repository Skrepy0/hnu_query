import httpx

from .exceptions import TokenExpired, YjsxtNetworkError, YjsxtStatusError

BASE_URL = "http://yjsxt.hnu.edu.cn"


async def request(
    client: httpx.AsyncClient, method: str, url: str, *, login: bool = False, **kwargs
) -> httpx.Response:
    if url.startswith("/"):
        url = BASE_URL + url
    try:
        response = await client.request(method, url, follow_redirects=False, **kwargs)
    except httpx.RequestError as exc:
        raise YjsxtNetworkError("研究生系统网络请求失败") from exc
    if response.status_code == 302 and not login:
        raise TokenExpired("研究生系统会话已失效")
    if not 200 <= response.status_code < 300 and not (login and response.is_redirect):
        raise YjsxtStatusError(response.status_code)
    return response
