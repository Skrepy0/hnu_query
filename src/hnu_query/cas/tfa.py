import re

import httpx

from ..utils.cookie import cookie_parser
from .exceptions import CasLoginError, CasNetworkError, CasStatusError
from .token import CasToken

CAS_BASE = "https://cas.hnu.edu.cn"
SMS_URL = f"{CAS_BASE}/cas/syz/services/sedsms"
LOGIN_URL = f"{CAS_BASE}/cas/login"

_EXECUTION_RE = re.compile(r'name="execution".*?value="(.*?)"', re.DOTALL)
_PHONE_RE = re.compile(r'id="phone".*?name="username".*?value="(.*?)"', re.DOTALL)


class TFAToken:
    """双因子认证令牌。

    对应 Rust ``cas::tfa::TFAToken``。
    """

    def __init__(
        self,
        phone: str,
        execution: str,
        cookie: str,
        stu_id: str,
        password: str,
    ) -> None:
        self.phone = phone
        self.execution = execution
        self.cookie = cookie
        self.stu_id = stu_id
        self.password = password

    @classmethod
    def from_html(
        cls,
        html: str,
        cookie: str,
        stu_id: str,
        password: str,
    ) -> "TFAToken":
        """从双因子认证界面的 HTML 中创建 TFAToken。

        对应 Rust ``TFAToken::new``。
        """
        m_exec = _EXECUTION_RE.search(html)
        if not m_exec:
            raise CasLoginError("没有找到 execution")

        m_phone = _PHONE_RE.search(html)
        if not m_phone:
            raise CasLoginError("没有找到绑定手机号")

        return cls(
            phone=m_phone.group(1),
            execution=m_exec.group(1),
            cookie=cookie,
            stu_id=stu_id,
            password=password,
        )

    async def send_sms(self) -> str:
        """发送短信验证码。

        对应 Rust ``TFAToken::send_sms``。

        Returns:
            ``"success"`` / ``"valid"`` / 其他服务端原文。
        """
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=False) as client:
            try:
                r = await client.get(
                    SMS_URL,
                    params={"reloginType": "reloginPhone"},
                    headers={"Cookie": self.cookie},
                )
            except httpx.RequestError as e:
                raise CasNetworkError(str(e)) from e
            if r.status_code >= 400:
                raise CasStatusError(r.status_code, r.text[:200])
            return r.text

    async def verify(self, code: str):
        """验证短信验证码。

        对应 Rust ``TFAToken::verify``。

        Returns:
            ``("success", new_cas_token)`` —— 验证通过
            ``("code_error", new_tfa_token)`` —— 验证码错误
            ``("expired", None)`` —— TFA 令牌过期
        """
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=False) as client:
            try:
                r = await client.post(
                    LOGIN_URL,
                    headers={"Cookie": self.cookie},
                    data={
                        "execution": self.execution,
                        "username": self.phone,
                        "recode": code,
                        "reloginType": "reloginPhone",
                        "_eventId": "submit",
                    },
                )
            except httpx.RequestError as e:
                raise CasNetworkError(str(e)) from e

        if r.status_code >= 400:
            raise CasStatusError(r.status_code)
        # 与 Rust 一致，仅 302 表示验证通过；同名 Cookie 使用新值。
        if r.status_code == 302:
            new_cookies = cookie_parser(r.headers.get_list("set-cookie"))
            cookies = {}
            for item in [*self.cookie.split(";"), *new_cookies]:
                if "=" in item:
                    key, value = item.strip().split("=", 1)
                    cookies[key] = value
            merged = "; ".join(f"{key}={value}" for key, value in cookies.items())
            return ("success", CasToken.from_cookie_unchecked(merged, self.stu_id))

        html = r.text
        if "验证码错误，请重新输入！" in html:
            new_tfa = TFAToken.from_html(html, self.cookie, self.stu_id, self.password)
            return ("code_error", new_tfa)

        return ("expired", None)
