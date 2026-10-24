import httpx

from hnu_query.cas import CasToken, get_ticket_url
from hnu_query.utils.cookie import cookie_parser

from ._http import request
from .exceptions import XgxtLoginError
from .token import XgxtToken

XGXT_URL = "http://cas.hnu.edu.cn/cas/login?service=http://xgxt.hnu.edu.cn/zftal-xgxt-web/teacher/xtgl/index/check.zf"


async def acquire_by_cas_login(cas_token: CasToken) -> XgxtToken:
    """CAS 返回 HTTP 回调，但实际兑换时使用 HTTPS。"""
    ticket_url = await get_ticket_url(cas_token, XGXT_URL)
    target = httpx.URL(ticket_url)
    if target.host != "xgxt.hnu.edu.cn" or target.scheme not in ("http", "https"):
        raise XgxtLoginError("学工票据回调不属于学工系统")
    target = target.copy_with(scheme="https")
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=False) as client:
        response = await request(client, str(target), login=True)
    if response.status_code != 302:
        raise XgxtLoginError("学工登录未返回预期的 302 响应")
    cookies = cookie_parser(response.headers.get_list("set-cookie"))
    if not cookies:
        raise XgxtLoginError("学工登录未返回会话 Cookie")
    return XgxtToken({"Cookie": "; ".join(cookies)})
