import httpx

from .exceptions import XgxtNetworkError, XgxtStatusError

BASE_URL = "https://xgxt.hnu.edu.cn"


async def request(
    client: httpx.AsyncClient, url: str, *, login: bool = False, **kwargs
) -> httpx.Response:
    if url.startswith("/"):
        url = BASE_URL + url
    try:
        response = await client.get(url, follow_redirects=False, **kwargs)
    except httpx.RequestError as exc:
        raise XgxtNetworkError("学工系统网络请求失败") from exc
    if not 200 <= response.status_code < 300 and not (login and response.is_redirect):
        raise XgxtStatusError(response.status_code)
    return response
