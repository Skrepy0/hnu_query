import httpx

from hnu_query.cas import CasToken, get_sticket
from hnu_query.utils.cookie import cookie_parser

from ._http import request
from .exceptions import NetflowLoginError
from .token import NetflowToken

NETFLOW_URL = "http://cas.hnu.edu.cn/application/sso.zf?login=B5712DC2FA281C96E053026B3E0A80A6"


async def acquire_by_cas_login(cas_token: CasToken) -> NetflowToken:
    """兑换 CAS s_ticket；沿用 Rust 的 GET 表单正文和首尾 Cookie 选择。"""
    s_ticket, cas_cookies = await get_sticket(cas_token, NETFLOW_URL)
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=False) as client:
        response = await request(
            client,
            "GET",
            "/login/validate",
            allow_redirect=True,
            headers={"Cookie": cas_cookies},
            data={
                "s_ticket": s_ticket,
                "login_id": cas_token.stu_id,
                "password": "",
                "null": "",
            },
        )
    cookies = cookie_parser(response.headers.get_list("set-cookie"))
    if not cookies:
        raise NetflowLoginError("流量系统登录未返回会话 Cookie")
    return NetflowToken({"Cookie": f"{cookies[0]}; {cookies[-1]}"})
