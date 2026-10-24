from urllib.parse import urljoin

import httpx

from hnu_query.cas import CasToken, get_ticket_url
from hnu_query.utils.cookie import cookie_parser

from ._http import request
from .exceptions import IPortalLoginError
from .token import IPortalToken

IPORTAL_LOGIN_URL = "https://cas.hnu.edu.cn/cas/login?service=https%3A%2F%2Fiportal.hnu.edu.cn%2Fhnu%2Ffrontend%2Flogin%3Fredirect%3Dhttps%253A%252F%252Fiportal.hnu.edu.cn%252Fhome&isotherLogin=true"


def _check_target(url: str) -> None:
    target = httpx.URL(url)
    if target.host != "iportal.hnu.edu.cn" or target.scheme not in ("http", "https"):
        raise IPortalLoginError("新门户登录回调不属于新门户")


async def acquire_by_cas_login(cas_token: CasToken) -> IPortalToken:
    """兑换票据，再访问至多一个 Location，按 Cookie 名合并会话。"""
    ticket_url = await get_ticket_url(cas_token, IPORTAL_LOGIN_URL)
    _check_target(ticket_url)
    cookies = {}

    def merge(response):
        for cookie in cookie_parser(response.headers.get_list("set-cookie")):
            key, value = cookie.split("=", 1)
            cookies[key] = value

    def headers():
        return (
            {"Cookie": "; ".join(f"{key}={value}" for key, value in cookies.items())}
            if cookies
            else {}
        )

    async with httpx.AsyncClient(timeout=30.0, follow_redirects=False) as client:
        response = await request(client, ticket_url, login=True)
        if response.status_code != 302:
            raise IPortalLoginError("新门户登录未返回预期的 302 响应")
        merge(response)
        location = response.headers.get("location")
        if location is not None:
            target = urljoin(ticket_url, location)
            _check_target(target)
            response = await request(client, target, login=True, headers=headers())
            merge(response)
    if not cookies:
        raise IPortalLoginError("新门户登录未返回会话 Cookie")
    return IPortalToken(headers())
