from urllib.parse import parse_qs, urljoin, urlsplit

import httpx

from hnu_query.cas import CasToken, get_ticket_url

from ._http import BASE_URL, request
from .exceptions import AiLoginError
from .parse import bearer_token
from .token import AiToken

INITIAL_AUTH_URL = "https://deepseek.hnu.edu.cn:5556/auth?client_id=openclaw&response_type=code&redirect_uri=https%3A%2F%2Fmaas.nscc-cs.cn%2Fcallback&scope=openid%20profile%20email"
OAUTH_LOGIN_URL = BASE_URL + "/api/oauth-login"


def _target(url: str):
    try:
        target = urlsplit(url)
        allowed = {
            ("deepseek.hnu.edu.cn", 5556),
            ("cas.hnu.edu.cn", 443),
            ("maas.nscc-cs.cn", 443),
        }
        if (
            target.scheme != "https"
            or target.username is not None
            or target.password is not None
            or (target.hostname, 443 if target.port is None else target.port)
            not in allowed
        ):
            raise ValueError
    except ValueError as exc:
        raise AiLoginError("OAuth 跳转目标不受支持") from exc
    return target


async def acquire_by_cas_login(cas_token: CasToken) -> AiToken:
    """跟随最多十次 OAuth 请求，使用原始 CAS 令牌换票据。"""
    current = INITIAL_AUTH_URL
    authenticated = False
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=False) as client:
        for _ in range(10):
            target = _target(current)
            # 其他域只使用 HTTP CookieJar 匹配的 Cookie，CAS 始终使用原始凭据。
            headers = (
                {"Cookie": cas_token.cookie}
                if target.hostname == "cas.hnu.edu.cn"
                else {}
            )
            response = await request(
                client, "GET", current, login=True, headers=headers
            )
            if response.status_code in (302, 303):
                location = response.headers.get("location")
                if not location:
                    raise AiLoginError("OAuth 跳转缺少 Location")
                current = urljoin(current, location)
                _target(current)
                continue
            if target.hostname == "maas.nscc-cs.cn" and target.path == "/callback":
                codes = parse_qs(target.query, keep_blank_values=True).get("code", [])
                if len(codes) != 1 or not codes[0]:
                    raise AiLoginError("OAuth 回调缺少唯一 code")
                code = codes[0]
                break
            if target.hostname == "cas.hnu.edu.cn" and not authenticated:
                current = urljoin(current, await get_ticket_url(cas_token, current))
                _target(current)
                authenticated = True
                continue
            raise AiLoginError("OAuth 登录收到非预期页面")
        else:
            raise AiLoginError("OAuth 跳转次数超过限制")

        response = await request(
            client, "POST", OAUTH_LOGIN_URL, login=True, json={"code": code}
        )
        if response.is_redirect:
            raise AiLoginError("OAuth 换取令牌时发生跳转")
        bearer = bearer_token(response.text)
        # 仅保存 MaaS API 路径可用的 Cookie，不保存 CAS/DeepSeek Cookie。
        api_request = client.build_request("GET", BASE_URL + "/api/tokens")
        headers = {"Authorization": f"Bearer {bearer}"}
        if "cookie" in api_request.headers:
            headers["Cookie"] = api_request.headers["cookie"]
        return AiToken(headers)
