# src/hnu_query/cas/login.py
import re

import httpx

from ..utils.cookie import cookie_parser
from ..utils.rsa import rsa_encrypt
from .exceptions import (
    AccountLocked,
    CasLoginError,
    CasNetworkError,
    CasParseError,
    CasStatusError,
    PasswordError,
    PasswordShouldChange,
    TFARequired,
)
from .tfa import TFAToken
from .token import CasToken

PUBKEY_URL = "http://cas.hnu.edu.cn/cas/v2/getPubKey"
SERVICE_URL = "http://cas.hnu.edu.cn/cas/login?service=http://cas.hnu.edu.cn/system/login/login.zf"
PASSWORD_SHOULD_CHANGE_PAT = "cas.hnu.edu.cn/securitycenter/modifyPwd/index.zf"

_EXECUTION_RE = re.compile(r'name="execution" value="(.*?)"')
_EVENT_ID_RE = re.compile(r'name="_eventId" value="(.*?)"')


async def acquire_by_login(stu_id: str, password: str) -> CasToken:
    """通过学号 + 密码登录 CAS，返回 CasToken。

    对应 Rust ``CasToken::acquire_by_login``。

    Args:
        stu_id: 学号。
        password: 密码。

    Returns:
        CasToken 实例。

    Raises:
        PasswordError: 密码错误。
        PasswordShouldChange: 需要前往个人门户修改密码。
        AccountLocked: 账号被锁定。
        TFARequired: 需要双因子认证（异常携带 TFAToken）。
    """
    async with httpx.AsyncClient(
        timeout=30.0,
        follow_redirects=False,
    ) as client:
        # ① GET SERVICE_URL，拿初始 cookie 和登录表单字段
        try:
            res = await client.get(SERVICE_URL)
        except httpx.RequestError as e:
            raise CasNetworkError(str(e)) from e
        if res.status_code != 200:
            raise CasStatusError(res.status_code, res.text[:200])

        cookies = cookie_parser(res.headers.get_list("set-cookie"))
        login_text = res.text

        execution = _match(_EXECUTION_RE, login_text)
        event_id = _match(_EVENT_ID_RE, login_text)

        # ② GET PUBKEY_URL，拿 modulus + exponent
        try:
            pubkey_res = await client.get(
                PUBKEY_URL,
                headers={"Cookie": "; ".join(cookies)},
            )
        except httpx.RequestError as e:
            raise CasNetworkError(str(e)) from e
        if pubkey_res.status_code >= 400:
            raise CasStatusError(pubkey_res.status_code, pubkey_res.text[:200])

        cookies.extend(cookie_parser(pubkey_res.headers.get_list("set-cookie")))

        try:
            pubkey = pubkey_res.json()
        except ValueError as e:
            raise CasParseError("getPubKey 返回非 JSON") from e

        if not isinstance(pubkey, dict):
            raise CasParseError("getPubKey 响应不是对象")
        modulus = pubkey.get("modulus")
        exponent = pubkey.get("exponent")
        if not isinstance(modulus, str) or not isinstance(exponent, str):
            raise CasParseError("无法解析 modulus 或 exponent")

        # ③ RSA 加密密码
        encrypted = rsa_encrypt(password, exponent, modulus)
        if encrypted is None:
            raise CasParseError("RSA encryption failed")

        # ④ POST 登录表单
        try:
            login = await client.post(
                SERVICE_URL,
                headers={"Cookie": "; ".join(cookies)},
                data={
                    "authcode": "",
                    "username": stu_id,
                    "password": encrypted,
                    "execution": execution,
                    "_eventId": event_id,
                },
            )
        except httpx.RequestError as e:
            raise CasNetworkError(str(e)) from e

        # ⑤ 403 → 账号锁定
        if login.status_code == 403:
            raise AccountLocked("账号因多次输错密码被锁定")
        if login.status_code not in (200, 302):
            raise CasStatusError(login.status_code)

        # 保留 _pv0 cookie（后续请求要用）
        addition = [c for c in cookies if c.startswith("_pv0=")]
        new_cookies = cookie_parser(login.headers.get_list("set-cookie"))
        new_cookies.extend(addition)

        location = login.headers.get("Location")
        login_result = login.text

        # ⑥ 判断登录结果
        if "用户名或密码错误" in login_result:
            raise PasswordError("密码错误")

        if "双因子认证" in login_result:
            tfa = TFAToken.from_html(
                login_result,
                "; ".join(new_cookies),
                stu_id,
                password,
            )
            raise TFARequired(tfa)

        if not location:
            raise CasLoginError("无法获取 cas 响应的 location")

        if PASSWORD_SHOULD_CHANGE_PAT in location:
            raise PasswordShouldChange("请前往个人门户修改密码后重试")

        return CasToken.from_cookie_unchecked("; ".join(new_cookies), stu_id)


def _match(pattern: re.Pattern, text: str) -> str:
    m = pattern.search(text)
    return m.group(1) if m else ""
