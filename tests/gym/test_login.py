from urllib.parse import parse_qs

import pytest
import respx

from hnu_query.cas import TokenExpired as CasTokenExpired
from hnu_query.gym import (
    GymLoginError,
    GymToken,
    acquire_by_cas_login,
    acquire_by_direct_login,
)
from hnu_query.gym._http import API_URL, BASE_URL
from hnu_query.gym.login import GYM_URL_FROM_CAS


@respx.mock
async def test_direct_login():
    route = respx.post(API_URL + "/Login/login").respond(
        200,
        json={"info": "登录成功"},
        headers=[
            ("set-cookie", "PHPSESSID=secret; Path=/"),
            ("set-cookie", "route=node1; HttpOnly"),
        ],
    )
    token = await GymToken.acquire_by_direct_login("20250001", "p&+word")
    assert token.headers["Cookie"] == "PHPSESSID=secret; route=node1"
    assert parse_qs(route.calls.last.request.content.decode()) == {
        "student_num": ["20250001"],
        "password": ["p&+word"],
    }


@respx.mock
async def test_cas_login(cas_token):
    respx.get(GYM_URL_FROM_CAS).respond(
        302,
        headers={
            "location": "https://cas.hnu.edu.cn/sprcialapp/zf_form/index.zf?x=1&s_ticket=ST%2Btest",
        },
    )
    page = respx.get(BASE_URL + "/view/login/loginPage.html").respond(
        200, headers={"set-cookie": "page=initial; Path=/"}
    )
    login = respx.post(API_URL + "/Login/ticketLogin").respond(
        200,
        json={"info": "登录成功"},
        headers={"set-cookie": "PHPSESSID=authenticated; Path=/"},
    )
    token = await GymToken.acquire_by_cas_login(cas_token)
    assert token.headers["Cookie"] == "PHPSESSID=authenticated"
    assert page.calls.last.request.url.params["s_ticket"] == "ST+test"
    assert page.calls.last.request.url.params["login_id"] == cas_token.stu_id
    assert "TGC" not in page.calls.last.request.headers.get("cookie", "")
    assert login.calls.last.request.headers["cookie"] == "page=initial"
    assert parse_qs(login.calls.last.request.content.decode()) == {
        "s_ticket": ["ST+test"],
        "login_id": [cas_token.stu_id],
    }
    assert len(respx.calls) == 3


@pytest.mark.parametrize(
    "body,headers",
    [
        ('{"info":"密码错误"}', {}),
        ('{"info":"登录成功"}', {}),
        ("<html>login</html>", {}),
        ("null", {}),
        ("[]", {}),
    ],
)
@respx.mock
async def test_bad_login(body, headers):
    respx.post(API_URL + "/Login/login").respond(200, text=body, headers=headers)
    with pytest.raises(GymLoginError):
        await acquire_by_direct_login("20250001", "password")


@respx.mock
async def test_expired_cas(cas_token):
    respx.get(GYM_URL_FROM_CAS).respond(200)
    with pytest.raises(CasTokenExpired):
        await acquire_by_cas_login(cas_token)
    assert len(respx.calls) == 1
