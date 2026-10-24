import asyncio
import base64
from urllib.parse import parse_qs

import httpx
import pytest
import respx
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from hnu_query import lab
from hnu_query.lab._http import BASE_URL
from hnu_query.lab.login import CAPTCHA_PATH, LOGIN_PATH, lab_encrypt


def test_rust_encryption_vector():
    assert lab_encrypt("202402050201") == "M1laOXBibVZLeS9Qd0FvUGlnNnlmZz09"


@pytest.mark.parametrize("password", ["", "中文密码&+", "x" * 16, "x" * 17])
def test_encryption_utf8_padding(password):
    ciphertext = base64.b64decode(base64.b64decode(lab_encrypt(password)))
    decryptor = Cipher(algorithms.AES(b"1234567891234567"), modes.ECB()).decryptor()
    plaintext = decryptor.update(ciphertext) + decryptor.finalize()
    unpadder = padding.PKCS7(128).unpadder()
    assert (unpadder.update(plaintext) + unpadder.finalize()).decode() == password


@respx.mock
async def test_immediate_login_success():
    route = respx.post(BASE_URL + LOGIN_PATH).respond(
        200, json={"RTNCode": 1}, headers={"set-cookie": "session=ready; Path=/"}
    )

    def resolver(data):
        pytest.fail("首次登录成功时不应请求验证码")

    token = await lab.LabToken.acquire_by_login(
        "202402050201", "202402050201", resolver, 3
    )
    assert token.stu_id == "202402050201"
    assert token.headers["Cookie"] == "session=ready"
    assert parse_qs(
        route.calls.last.request.content.decode(), keep_blank_values=True
    ) == {
        "uname": ["202402050201"],
        "pwd": ["M1laOXBibVZLeS9Qd0FvUGlnNnlmZz09"],
        "checkcode": [""],
    }
    assert route.call_count == 1


@respx.mock
async def test_captcha_retry_and_cookie_rotation():
    route = respx.post(BASE_URL + LOGIN_PATH).mock(
        side_effect=[
            httpx.Response(
                200,
                json={"RTNCode": -2},
                headers={"set-cookie": "session=initial; Path=/"},
            ),
            httpx.Response(
                200,
                json={"RTNCode": -2},
                headers={"set-cookie": "session=rotated; Path=/"},
            ),
            httpx.Response(
                200, json={"RTNCode": 1}, headers={"set-cookie": "auth=ok; Path=/"}
            ),
        ]
    )
    image = respx.get(BASE_URL + CAPTCHA_PATH).respond(
        200, content=b"jpeg", headers={"set-cookie": "captcha=state; Path=/"}
    )

    class Resolver:
        def __init__(self):
            self.calls = 0

        async def resolve(self, data):
            assert data == b"jpeg"
            self.calls += 1
            return f"code{self.calls}"

    resolver = Resolver()
    token = await lab.acquire_by_login("student", "password", resolver, 3)
    assert resolver.calls == image.call_count == 2
    assert route.call_count == 3
    assert token.headers["Cookie"] == "session=rotated; captcha=state; auth=ok"
    assert image.calls[0].request.headers["cookie"] == "session=initial"
    assert route.calls[1].request.headers["cookie"] == "session=initial; captcha=state"
    assert parse_qs(route.calls[1].request.content.decode())["checkcode"] == ["code1"]
    assert parse_qs(route.calls[2].request.content.decode())["checkcode"] == ["code2"]


@pytest.mark.parametrize("attempts", [0, 1, 3])
@respx.mock
async def test_captcha_exhaustion(attempts):
    if attempts == 0:
        with pytest.raises(lab.CaptchaError):
            await lab.acquire_by_login("student", "password", lambda data: "wrong", 0)
        assert len(respx.calls) == 0
        return
    route = respx.post(BASE_URL + LOGIN_PATH).respond(200, json={"RTNCode": -2})
    image = respx.get(BASE_URL + CAPTCHA_PATH).respond(200, content=b"image")
    with pytest.raises(lab.CaptchaError):
        await lab.acquire_by_login(
            "student", "password", lambda data: "wrong", attempts
        )
    assert route.call_count == image.call_count == attempts


@pytest.mark.parametrize(
    "code,error", [(-1, lab.PasswordError), (0, lab.OtherError), (5, lab.OtherError)]
)
@respx.mock
async def test_non_captcha_failure_does_not_retry(code, error):
    route = respx.post(BASE_URL + LOGIN_PATH).respond(
        200, json={"RTNCode": code, "Data": "服务端说明"}
    )
    with pytest.raises(error) as caught:
        await lab.acquire_by_login("student", "password", lambda data: "code", 3)
    if code != -1:
        assert caught.value.message == "服务端说明"
    assert isinstance(caught.value, lab.LoginIssue)
    assert route.call_count == 1


@pytest.mark.parametrize(
    "body,error",
    [
        ("null", lab.LabParseError),
        ("<html></html>", lab.LabParseError),
        ('{"RTNCode":true}', lab.LabParseError),
        ('{"RTNCode":"1"}', lab.LabParseError),
        ('{"RTNCode":1}', lab.LabLoginError),
    ],
)
@respx.mock
async def test_invalid_login_response(body, error):
    respx.post(BASE_URL + LOGIN_PATH).respond(200, text=body)
    with pytest.raises(error):
        await lab.acquire_by_login("student", "password", lambda data: "code")


@pytest.mark.parametrize("failure", ["exception", "bad_type", "cancelled"])
@respx.mock
async def test_resolver_failure(failure):
    route = respx.post(BASE_URL + LOGIN_PATH).respond(200, json={"RTNCode": -2})
    respx.get(BASE_URL + CAPTCHA_PATH).respond(200, content=b"image")

    async def resolver(data):
        if failure == "exception":
            raise RuntimeError("OCR offline")
        if failure == "cancelled":
            raise asyncio.CancelledError()
        return 123

    error = (
        asyncio.CancelledError if failure == "cancelled" else lab.CaptchaResolverError
    )
    with pytest.raises(error):
        await lab.acquire_by_login("student", "password", resolver)
    assert route.call_count == 1


@pytest.mark.parametrize("attempts", [-1, True, 1.5])
async def test_invalid_attempts(attempts):
    with pytest.raises(ValueError):
        await lab.acquire_by_login("student", "password", lambda data: "code", attempts)
