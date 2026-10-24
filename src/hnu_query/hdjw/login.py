from urllib.parse import urljoin

import httpx

from hnu_query.cas import CasToken, get_ticket_url
from hnu_query.utils.cookie import cookie_parser

from .client import request
from .exceptions import HdjwLoginError
from .token import HdjwToken

HDJW_ENTER_URL = "http://hdjw.hnu.edu.cn/gld/sso.jsp"
HDJW_FROM_CAS_URL = f"http://cas.hnu.edu.cn/cas/login?service={HDJW_ENTER_URL}"


def _merge_cookies(cookies: dict[str, str], response: httpx.Response) -> None:
    for item in cookie_parser(response.headers.get_list("set-cookie")):
        name, value = item.split("=", 1)
        cookies[name] = value


async def acquire_by_cas_login(cas_token: CasToken) -> HdjwToken:
    """按 Rust 的 SSO 流程预取 Cookie、兑换票据、访问最终重定向。"""
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=False) as client:
        cookies = {}
        response = await request(client, "GET", HDJW_ENTER_URL)
        _merge_cookies(cookies, response)
        if not cookies:
            raise HdjwLoginError("教务登录入口未返回会话 Cookie")

        def headers():
            return {
                "Cookie": "; ".join(f"{key}={value}" for key, value in cookies.items())
            }

        ticket_url = await get_ticket_url(cas_token, HDJW_FROM_CAS_URL)
        response = await request(client, "GET", ticket_url, headers=headers())
        _merge_cookies(cookies, response)
        response = await request(client, "GET", HDJW_ENTER_URL, headers=headers())
        _merge_cookies(cookies, response)
        if response.status_code != 302 or not response.headers.get("location"):
            raise HdjwLoginError("教务登录未返回预期的 302 重定向")
        target = urljoin(str(response.url), response.headers["location"])
        # 只允许教务域，避免将显式 Cookie 请求头送往其他站点。
        parsed = httpx.URL(target)
        if parsed.host != "hdjw.hnu.edu.cn" or parsed.scheme not in ("http", "https"):
            raise HdjwLoginError("教务登录重定向目标不属于教务系统")
        response = await request(client, "GET", target, headers=headers())
        _merge_cookies(cookies, response)
        # Rust 在此直接读取 Set-Cookie；认证 Cookie 也可能由 302 响应下发。
        return HdjwToken(headers=headers())
