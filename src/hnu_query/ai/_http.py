import httpx

from .exceptions import AiLoginError, AiNetworkError, AiStatusError, TokenExpired

BASE_URL = "https://maas.nscc-cs.cn"


async def request(
    client: httpx.AsyncClient, method: str, url: str, *, login: bool = False, **kwargs
) -> httpx.Response:
    try:
        response = await client.request(method, url, follow_redirects=False, **kwargs)
    except httpx.RemoteProtocolError as exc:
        if login:
            raise AiLoginError("OAuth 响应协议或跳转地址无效") from exc
        raise AiNetworkError("AI 平台响应协议无效") from exc
    except httpx.RequestError as exc:
        raise AiNetworkError("AI 平台网络请求失败") from exc
    if not login and response.status_code in (301, 302, 303, 307, 308, 401, 403):
        raise TokenExpired("AI 平台会话失效或无访问权限")
    if not 200 <= response.status_code < 300 and not (login and response.status_code in (302, 303)):
        raise AiStatusError(response.status_code)
    return response
