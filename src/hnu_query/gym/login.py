import httpx

from hnu_query.cas import CasToken, get_sticket
from hnu_query.utils.cookie import cookie_parser

from ._http import API_URL, BASE_URL, request
from .exceptions import GymLoginError
from .token import GymToken

GYM_URL_FROM_CAS = "http://cas.hnu.edu.cn/application/sso.zf?login=898A822E9695C137E053026B3E0A65D7"


def _login_token(response: httpx.Response) -> GymToken:
    try:
        data = response.json()
    except ValueError as exc:
        raise GymLoginError("体测登录响应不是有效 JSON") from exc
    if not isinstance(data, dict) or data.get("info") != "登录成功":
        raise GymLoginError("体测登录失败，请检查账号或重新获取 CAS 会话")
    cookies = {}
    for item in cookie_parser(response.headers.get_list("set-cookie")):
        key, value = item.split("=", 1)
        cookies[key] = value
    if not cookies:
        raise GymLoginError("体测登录未返回会话 Cookie")
    return GymToken({"Cookie": "; ".join(f"{key}={value}" for key, value in cookies.items())})


async def acquire_by_direct_login(stu_id: str, password: str) -> GymToken:
    """直接使用体测账号密码登录；体测密码可能与个人门户不同。"""
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=False) as client:
        response = await request(
            client,
            "POST",
            API_URL + "/Login/login",
            data={
                "student_num": stu_id,
                "password": password,
            },
        )
        return _login_token(response)


async def acquire_by_cas_login(cas_token: CasToken) -> GymToken:
    """兑换 CAS s_ticket，访问登录页后提交 ticketLogin。"""
    s_ticket, _ = await get_sticket(cas_token, GYM_URL_FROM_CAS)
    form = {"s_ticket": s_ticket, "login_id": cas_token.stu_id}
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=False) as client:
        await request(client, "GET", BASE_URL + "/view/login/loginPage.html", params=form)
        response = await request(client, "POST", API_URL + "/Login/ticketLogin", data=form)
        return _login_token(response)
