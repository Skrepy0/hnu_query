import httpx

from hnu_query.cas import CasToken, get_ticket_url
from hnu_query.utils.cookie import cookie_parser

from ._http import request
from .exceptions import PtLoginError
from .token import PtToken

# service 末尾的 / 必须保留，否则门户不能正常跳转。
PT_URL = "http://cas.hnu.edu.cn/cas/login?service=https://pt.hnu.edu.cn/"


async def acquire_by_cas_login(cas_token: CasToken) -> PtToken:
    """兑换 CAS 票据；读取门户 302 响应下发的 Cookie，不跟随跳转。"""
    ticket_url = await get_ticket_url(cas_token, PT_URL)
    target = httpx.URL(ticket_url)
    if target.host != "pt.hnu.edu.cn" or target.scheme not in ("http", "https"):
        raise PtLoginError("门户票据回调不属于个人门户")
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=False) as client:
        response = await request(client, "GET", ticket_url, allow_redirect=True)
    if response.status_code != 302:
        raise PtLoginError("个人门户登录未返回预期的 302 响应")
    cookies = cookie_parser(response.headers.get_list("set-cookie"))
    if not cookies:
        raise PtLoginError("个人门户登录未返回会话 Cookie")
    return PtToken({"Cookie": "; ".join(cookies)})
