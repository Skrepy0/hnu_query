import base64
import inspect
from collections.abc import Awaitable, Callable
from typing import Protocol, runtime_checkable

import httpx
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from hnu_query.utils.cookie import cookie_parser

from ._http import request
from .exceptions import (
    CaptchaError,
    CaptchaResolverError,
    LabLoginError,
    LabParseError,
    OtherError,
    PasswordError,
)
from .token import LabToken

LOGIN_PATH = "/BaseInfo/Login/ValidateLogin"
CAPTCHA_PATH = "/Ashx/CheckCode.ashx?t=0.29911677684547566"


@runtime_checkable
class CaptchaResolver(Protocol):
    """与 Rust trait 对齐；也可直接传入同步或异步函数。"""

    async def resolve(self, data: bytes) -> str: ...


Resolver = CaptchaResolver | Callable[[bytes], str | Awaitable[str]]


def lab_encrypt(password: str) -> str:
    """AES-128-ECB + PKCS7，再做两次 Base64，与 Rust lab_encrypt 一致。"""
    padder = padding.PKCS7(128).padder()
    plaintext = padder.update(password.encode("utf-8")) + padder.finalize()
    encryptor = Cipher(algorithms.AES(b"1234567891234567"), modes.ECB()).encryptor()
    encrypted = encryptor.update(plaintext) + encryptor.finalize()
    return base64.b64encode(base64.b64encode(encrypted)).decode("ascii")


async def _resolve(resolver: Resolver, data: bytes) -> str:
    try:
        callback = resolver.resolve if isinstance(resolver, CaptchaResolver) else resolver
        code = callback(data)
        if inspect.isawaitable(code):
            code = await code
        if not isinstance(code, str):
            raise TypeError("验证码识别结果必须为字符串")
        return code
    except Exception as exc:
        raise CaptchaResolverError("验证码识别器执行失败") from exc


async def acquire_by_login(
    stu_id: str,
    password: str,
    captcha_resolver: Resolver,
    max_tried: int = 3,
) -> LabToken:
    """最多提交 max_tried 次登录，仅 RTNCode=-2（验证码错误）触发重试。

    首次提交空验证码，服务器要求验证码后才下载图片并调用识别器。
    max_tried=0 与 Rust 一样直接抛出 CaptchaError。
    """
    if type(max_tried) is not int or max_tried < 0:
        raise ValueError("max_tried 必须为非负整数")
    encrypted = lab_encrypt(password)
    checkcode = ""
    cookies: dict[str, str] = {}

    def headers():
        return {"Cookie": "; ".join(f"{key}={value}" for key, value in cookies.items())}

    def merge(response):
        for item in cookie_parser(response.headers.get_list("set-cookie")):
            key, value = item.split("=", 1)
            cookies[key] = value

    async with httpx.AsyncClient(timeout=30.0, follow_redirects=False) as client:
        for _ in range(max_tried):
            response = await request(
                client,
                "POST",
                LOGIN_PATH,
                headers=headers(),
                data={
                    "uname": stu_id,
                    "pwd": encrypted,
                    "checkcode": checkcode,
                },
            )
            merge(response)
            try:
                data = response.json()
            except ValueError as exc:
                raise LabParseError("实验平台登录响应不是有效 JSON") from exc
            if not isinstance(data, dict) or type(data.get("RTNCode")) is not int:
                raise LabParseError("无法解析实验平台登录结果 RTNCode")
            code = data["RTNCode"]
            if code == -2:
                image = await request(client, "GET", CAPTCHA_PATH, headers=headers())
                merge(image)
                checkcode = await _resolve(captcha_resolver, image.content)
            elif code == -1:
                raise PasswordError("实验平台账号或密码错误")
            elif code == 1:
                if not cookies:
                    raise LabLoginError("实验平台登录未返回会话 Cookie")
                return LabToken(headers(), stu_id)
            else:
                message = data.get("Data")
                raise OtherError(message if isinstance(message, str) else None)
    raise CaptchaError("验证码未通过，已耗尽登录尝试次数")
