from urllib.parse import parse_qs, urljoin, urlsplit

import httpx

from hnu_query.cas import CasToken, get_ticket_url

from ._http import request
from .exceptions import YjsxtLoginError
from .token import YjsxtToken

YJSXT_FROM_CAS_URL = (
    "http://cas.hnu.edu.cn/cas/login?service=http://yjsxt.hnu.edu.cn/gmis/oauthLogin/hndxnew?ywdm="
)


def _check_target(url: str) -> None:
    parsed = urlsplit(url)
    if parsed.hostname != "yjsxt.hnu.edu.cn" or parsed.scheme not in ("http", "https"):
        raise YjsxtLoginError("研究生登录回调不属于研究生系统")


async def acquire_by_cas_login(cas_token: CasToken) -> YjsxtToken:
    """兑换 CAS 票据，从 Location 提取路径会话 ID，再检查账号访问权限。"""
    ticket_url = await get_ticket_url(cas_token, YJSXT_FROM_CAS_URL)
    _check_target(ticket_url)
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=False) as client:
        response = await request(client, "GET", ticket_url, login=True)
        if response.status_code != 302:
            raise YjsxtLoginError("研究生登录未返回预期的 302 响应")
        location = response.headers.get("location")
        if not location:
            raise YjsxtLoginError("研究生登录缺少 Location")
        target = urljoin(ticket_url, location)
        _check_target(target)
        path = urlsplit(target).path
        if "/gmis/" not in path:
            raise YjsxtLoginError("找不到研究生系统会话 ID")
        id = path.split("/gmis/", 1)[1].split("/", 1)[0]
        if not id:
            raise YjsxtLoginError("研究生系统会话 ID 为空")
        response = await request(client, "GET", target, login=True)
        redirect = response.headers.get("location", "")
        if "/home/err" in redirect:
            message = parse_qs(urlsplit(redirect).query, keep_blank_values=True).get("msg", [""])[0]
            raise YjsxtLoginError(message or "该账号无法访问研究生系统")
    return YjsxtToken(id)
