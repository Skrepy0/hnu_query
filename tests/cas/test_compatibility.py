import json
from pathlib import Path
from urllib.parse import parse_qs

import pytest
import respx

from hnu_query.cas import (
    CasLoginError,
    CasParseError,
    CasStatusError,
    CasToken,
    TFAToken,
    acquire_by_login,
    get_ticket_url,
)
from hnu_query.cas.login import PUBKEY_URL, SERVICE_URL
from hnu_query.cas.tfa import LOGIN_URL, SMS_URL
from hnu_query.utils.rsa import rsa_encrypt


def test_rust_tfa_sample():
    html = (Path(__file__).parent / "fixtures/tfa.html").read_text(encoding="utf-8")
    token = TFAToken.from_html(html, "session=fake", "114514", "fake-password")
    assert token.phone == "114514"
    assert token.execution.startswith("3a24971d-2944-4622-818b-77426fe38209_")
    assert token.execution.endswith("dHRzU0N3")


@pytest.mark.parametrize("status", [301, 303, 307, 308, 201, 204])
@respx.mock
async def test_ticket_only_accepts_302(cas_token, status):
    route = respx.get(SERVICE_URL).respond(
        status, headers={"location": "https://example.org"}
    )
    with pytest.raises(CasStatusError):
        await get_ticket_url(cas_token, SERVICE_URL)
    assert route.call_count == 1


@pytest.mark.parametrize("status", [400, 403, 500, 503])
@respx.mock
async def test_tfa_verify_http_error(status):
    token = TFAToken("114514", "exec", "session=old", "student", "password")
    respx.post(LOGIN_URL).respond(status, text="unexpected")
    with pytest.raises(CasStatusError) as error:
        await token.verify("123456")
    assert error.value.status_code == status


@pytest.mark.parametrize("status", [301, 303, 307, 308])
@respx.mock
async def test_other_tfa_redirects_are_not_success(status):
    token = TFAToken("114514", "exec", "session=old", "student", "password")
    respx.post(LOGIN_URL).respond(status, headers={"location": "/elsewhere"})
    assert await token.verify("123456") == ("expired", None)


@respx.mock
async def test_tfa_request_and_cookie_replacement():
    token = TFAToken("114514", "exec", "TGC=old; route=one", "student", "password")
    route = respx.post(LOGIN_URL).respond(
        302, headers={"set-cookie": "TGC=new; Path=/"}
    )
    status, cas = await token.verify("123456")
    assert status == "success"
    assert cas.cookie == "TGC=new; route=one"
    assert parse_qs(route.calls.last.request.content.decode()) == {
        "execution": ["exec"],
        "username": ["114514"],
        "recode": ["123456"],
        "reloginType": ["reloginPhone"],
        "_eventId": ["submit"],
    }
    assert route.calls.last.request.headers["cookie"] == token.cookie


@respx.mock
async def test_sms_request_uses_tfa_cookie():
    token = TFAToken("114514", "exec", "session=fake", "student", "password")
    route = respx.get(SMS_URL, params={"reloginType": "reloginPhone"}).respond(
        text="valid"
    )
    assert await token.send_sms() == "valid"
    assert route.calls.last.request.headers["cookie"] == token.cookie


@pytest.mark.parametrize(
    "data",
    [
        None,
        [],
        1,
        "key",
        {"modulus": 123, "exponent": "03"},
        {"modulus": "bf", "exponent": False},
        {"modulus": "0", "exponent": "03"},
    ],
)
@respx.mock
async def test_malformed_public_key_is_parse_error(data):
    respx.get(SERVICE_URL).respond(text="<form></form>")
    respx.get(PUBKEY_URL).respond(text=json.dumps(data))
    with pytest.raises(CasParseError):
        await acquire_by_login("student", "password")
    assert len(respx.calls) == 2


@respx.mock
async def test_missing_login_location():
    respx.get(SERVICE_URL).respond(text="<form></form>")
    respx.get(PUBKEY_URL).respond(json={"modulus": "bf", "exponent": "03"})
    respx.post(SERVICE_URL).respond(text="unrecognized page")
    with pytest.raises(CasLoginError):
        await acquire_by_login("student", "password")


@respx.mock
async def test_login_http_error_cannot_return_token():
    respx.get(SERVICE_URL).respond(text="<form></form>")
    respx.get(PUBKEY_URL).respond(json={"modulus": "bf", "exponent": "03"})
    respx.post(SERVICE_URL).respond(500, headers={"location": "/home"})
    with pytest.raises(CasStatusError):
        await acquire_by_login("student", "password")


@pytest.mark.parametrize("exponent,modulus", [("-1", "bf"), ("03", "-bf"), ("03", "0")])
def test_unsigned_rsa_parameters(exponent, modulus):
    assert rsa_encrypt("password", exponent, modulus) is None


def test_cas_token_hides_cookie():
    assert "private-cookie" not in repr(CasToken("private-cookie", "student"))
