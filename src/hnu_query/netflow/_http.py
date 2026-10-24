import httpx

from .exceptions import NetflowNetworkError, NetflowStatusError

BASE_URL = "http://ll.hnu.edu.cn"


async def request(
    client: httpx.AsyncClient,
    method: str,
    path: str,
    *,
    allow_redirect: bool = False,
    **kwargs,
) -> httpx.Response:
    try:
        response = await client.request(
            method, BASE_URL + path, follow_redirects=False, **kwargs
        )
    except httpx.RequestError as exc:
        raise NetflowNetworkError("校园网流量系统网络请求失败") from exc
    if not 200 <= response.status_code < 300 and not (
        allow_redirect and response.is_redirect
    ):
        raise NetflowStatusError(response.status_code)
    return response
