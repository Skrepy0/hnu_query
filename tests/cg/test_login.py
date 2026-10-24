import base64
from urllib.parse import parse_qs

import httpx
import pytest
import respx
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from hnu_query.cg import (
    CaptchaError,
    CgLoginError,
    CgNetworkError,
    CgSession,
    CgStatusError,
    LoginError,
    LoginFailed,
    PasswordError,
)
from hnu_query.cg._http import BASE_URL
from hnu_query.cg.login import CAPTCHA_URL, LOGIN_PAGE, LOGIN_URL, encrypt_password


def decrypt_password(value):
    decryptor = Cipher(algorithms.AES(b"Client8Sess!06ID"), modes.ECB()).decryptor()
    plaintext = decryptor.update(base64.b64decode(value)) + decryptor.finalize()
    unpadder = padding.PKCS7(128).unpadder()
    return (unpadder.update(plaintext) + unpadder.finalize()).decode("utf-8")


@pytest.mark.parametrize("password", ["", "password", "中文&+", "x" * 16, "x" * 17])
def test_encryption_contract(password):
    encrypted = encrypt_password(password)
    assert decrypt_password(encrypted) == password
    assert len(base64.b64decode(encrypted)) % 16 == 0


@respx.mock
async def test_session_and_login_form_cookie_flow():
    page = respx.get(BASE_URL + LOGIN_PAGE).respond(
        200, headers={"set-cookie": "JSESSIONID=initial; Path=/; HttpOnly"}
    )
    captcha = respx.get(BASE_URL + CAPTCHA_URL).respond(200, content=b"captcha-image")
    login = respx.post(BASE_URL + LOGIN_URL).respond(
        302,
        headers=[
            ("location", "/main.jsp"),
            ("set-cookie", "auth=ready; Path=/"),
        ],
    )
    session = await CgSession.new()
    assert session.captcha_image == b"captcha-image"
    assert "initial" not in repr(session) and "captcha-image" not in repr(session)
    assert captcha.calls.last.request.headers["cookie"] == "JSESSIONID=initial"
    token = await session.login("20260001", "中文&+", "a&+1")
    request = login.calls.last.request
    form = parse_qs(request.content.decode())
    assert form["IndexStyle"] == ["1"] and form["stid"] == ["20260001"]
    assert form["captchaCode"] == ["a&+1"]
    assert decrypt_password(form["pwd"][0]) == "中文&+"
    assert request.headers["cookie"] == "JSESSIONID=initial"
    assert token.headers["Cookie"] == "JSESSIONID=initial; auth=ready"
    assert page.call_count == 1 and len(respx.calls) == 3


@pytest.mark.parametrize(
    "location,error",
    [
        ("/indexcs/simple.jsp?loginErr=1", PasswordError),
        ("/indexcs/simple.jsp?loginErr=6", CaptchaError),
        ("/indexcs/simple.jsp?loginErr=9", LoginFailed),
    ],
)
@respx.mock
async def test_login_business_errors(location, error):
    route = respx.post(BASE_URL + LOGIN_URL).respond(
        302, headers={"location": location}
    )
    with pytest.raises(error) as caught:
        await CgSession({"Cookie": "JSESSIONID=initial"}, b"image").login(
            "student", "password", "code"
        )
    assert isinstance(caught.value, LoginError)
    if error is LoginFailed:
        assert caught.value.code == "9"
    assert route.call_count == 1


@respx.mock
async def test_login_error_code_query_parsing():
    respx.post(BASE_URL + LOGIN_URL).respond(
        302, headers={"location": "/main.jsp?loginErr=0&next=home"}
    )
    token = await CgSession({"Cookie": "session=ready"}, b"image").login(
        "student", "password", "code"
    )
    assert token.headers["Cookie"] == "session=ready"


@pytest.mark.parametrize(
    "status,headers,error",
    [(200, {}, CgLoginError), (302, {}, CgLoginError), (500, {}, CgStatusError)],
)
@respx.mock
async def test_login_bad_response(status, headers, error):
    respx.post(BASE_URL + LOGIN_URL).respond(status, headers=headers)
    with pytest.raises(error):
        await CgSession({}, b"image").login("student", "password", "code")


@respx.mock
async def test_session_rejects_http_error():
    respx.get(BASE_URL + LOGIN_PAGE).respond(500)
    with pytest.raises(CgStatusError):
        await CgSession.new()
    assert len(respx.calls) == 1


@respx.mock
async def test_session_network_error():
    respx.get(BASE_URL + LOGIN_PAGE).mock(side_effect=httpx.ConnectError("offline"))
    with pytest.raises(CgNetworkError):
        await CgSession.new()


def test_session_headers_snapshot():
    headers = {"Cookie": "secret"}
    session = CgSession(headers, b"image")
    headers["Cookie"] = "changed"
    assert session.headers["Cookie"] == "secret"
    with pytest.raises(TypeError):
        session.headers["Cookie"] = "changed"
