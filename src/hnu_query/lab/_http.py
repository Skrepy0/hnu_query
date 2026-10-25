import httpx

from .exceptions import LabNetworkError, LabStatusError

BASE_URL = "http://10.62.106.112"


async def request(client: httpx.AsyncClient, method: str, path: str, **kwargs) -> httpx.Response:
    try:
        response = await client.request(method, BASE_URL + path, follow_redirects=False, **kwargs)
    except httpx.RequestError as exc:
        raise LabNetworkError("实验平台网络请求失败") from exc
    if not 200 <= response.status_code < 300:
        raise LabStatusError(response.status_code)
    return response
