import httpx

from .exceptions import PtNetworkError, PtStatusError

BASE_URL = "https://pt.hnu.edu.cn"


async def request(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    *,
    allow_redirect: bool = False,
    **kwargs,
) -> httpx.Response:
    if url.startswith("/"):
        url = BASE_URL + url
    try:
        response = await client.request(method, url, follow_redirects=False, **kwargs)
    except httpx.RequestError as exc:
        raise PtNetworkError("个人门户网络请求失败") from exc
    if not 200 <= response.status_code < 300 and not (allow_redirect and response.is_redirect):
        raise PtStatusError(response.status_code)
    return response
