import base64
from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from urllib.parse import parse_qs, urlsplit

import httpx
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from hnu_query.utils.cookie import cookie_parser

from ._http import request, require_status
from .exceptions import CaptchaError, CgLoginError, LoginFailed, PasswordError
from .token import CgToken

LOGIN_PAGE = "/indexcs/simple.jsp"
CAPTCHA_URL = "/cgjiaoyan"
LOGIN_URL = "/login/loginproc.jsp"


def encrypt_password(password: str) -> str:
    """CG 前端 AES-128-ECB/PKCS7 加密，只做一次 Base64。"""
    padder = padding.PKCS7(128).padder()
    plaintext = padder.update(password.encode("utf-8")) + padder.finalize()
    encryptor = Cipher(algorithms.AES(b"Client8Sess!06ID"), modes.ECB()).encryptor()
    ciphertext = encryptor.update(plaintext) + encryptor.finalize()
    return base64.b64encode(ciphertext).decode("ascii")


@dataclass(frozen=True, slots=True)
class CgSession:
    """登录前会话；captcha_image 是供调用方识别的图片字节。"""

    headers: Mapping[str, str] = field(repr=False)
    captcha_image: bytes = field(repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "headers", MappingProxyType(dict(self.headers)))

    @classmethod
    async def new(cls) -> "CgSession":
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=False) as client:
            response = await request(client, "GET", LOGIN_PAGE)
            require_status(response)
            cookies = "; ".join(cookie_parser(response.headers.get_list("set-cookie")))
            headers = {"Cookie": cookies}
            captcha = await request(client, "GET", CAPTCHA_URL, headers=headers)
            require_status(captcha)
            return cls(headers, captcha.content)

    async def login(self, stu_id: str, password: str, captcha_code: str) -> CgToken:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=False) as client:
            response = await request(
                client,
                "POST",
                LOGIN_URL,
                headers=dict(self.headers),
                data={
                    "IndexStyle": "1",
                    "stid": stu_id,
                    "pwd": encrypt_password(password),
                    "captchaCode": captcha_code,
                },
            )
        if response.status_code != 302:
            raise CgLoginError("CG 登录未返回预期的 302 响应")
        location = response.headers.get("location")
        if not location:
            raise CgLoginError("CG 登录响应缺少 Location")
        code = parse_qs(urlsplit(location).query, keep_blank_values=True).get("loginErr", ["0"])[0]
        if code == "1":
            raise PasswordError("CG 账号或密码错误")
        if code == "6":
            raise CaptchaError("CG 验证码错误")
        if code != "0":
            raise LoginFailed(code)
        cookies = httpx.Headers(self.headers).get("cookie", "")
        new_cookies = "; ".join(cookie_parser(response.headers.get_list("set-cookie")))
        merged = "; ".join(value for value in (cookies, new_cookies) if value)
        return CgToken({"Cookie": merged} if merged else {})
