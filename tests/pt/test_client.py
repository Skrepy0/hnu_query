from urllib.parse import parse_qs

import httpx
import pytest
import respx

from hnu_query import pt
from hnu_query.pt._http import BASE_URL

CSRF_URL = BASE_URL + "/api/security/token"
HISTORY_URL = BASE_URL + "/api/hndxYkt/getAccHisConsubDzzfLog/detail"


@pytest.mark.parametrize(
    "method,path,fixture,expected",
    [
        (
            "get_card_info",
            "/api/hndxYkt/getCardUserInfo/info",
            "getCardUserInfo.json",
            None,
        ),
        (
            "get_unread_email_count",
            "/api/v1/email/unRead/count",
            "email_unread_success.json",
            6,
        ),
        (
            "get_unread_email_count",
            "/api/v1/email/unRead/count",
            "email_unread_fail.json",
            None,
        ),
    ],
)
@respx.mock
async def test_public_gets(pt_token, pt_data, method, path, fixture, expected):
    route = respx.get(BASE_URL + path).respond(200, json=pt_data(fixture))
    result = await getattr(pt, method)(pt_token)
    if method == "get_card_info":
        assert result.balance == 75.28
    else:
        assert result == expected
    request = route.calls.last.request
    assert request.headers["cookie"] == "SESSION=pt-test"
    assert not request.content
    assert not request.url.query


@pytest.mark.parametrize(
    "history_type,code,fixture,total",
    [
        (
            pt.CardHistoryType.Consumption,
            "15",
            "getAccHisConsubDzzfLog_Consumption.json",
            -51.0,
        ),
        (
            pt.CardHistoryType.Recharge,
            "16",
            "getAccHisConsubDzzfLog_Recharge.json",
            50.0,
        ),
    ],
)
@respx.mock
async def test_card_history_csrf_and_form(pt_token, pt_data, history_type, code, fixture, total):
    csrf = respx.get(CSRF_URL).respond(200, json={"data": "csrf&+token"})
    history = respx.post(HISTORY_URL).respond(200, json=pt_data(fixture))
    result = await pt.get_card_history(pt_token, 2026, 2, history_type)
    assert result.total == total
    assert respx.calls[0].request.url == CSRF_URL
    assert respx.calls[1].request.url == HISTORY_URL
    assert csrf.calls.last.request.headers["cookie"] == "SESSION=pt-test"
    request = history.calls.last.request
    assert request.headers["cookie"] == "SESSION=pt-test"
    assert request.headers["X-XSRF-TOKEN"] == "csrf&+token"
    assert parse_qs(request.content.decode()) == {
        "beginDate": ["2026-02-01"],
        "endDate": ["2026-02-31"],
        "pageSize": ["100000"],
        "trancode": [code],
    }


@respx.mock
async def test_csrf_refreshed_per_query_and_overrides_stale_header(pt_data):
    token = pt.PtToken({"Cookie": "SESSION=test", "x-xsrf-token": "old"})
    csrf = respx.get(CSRF_URL).mock(
        side_effect=[
            httpx.Response(200, json={"data": "fresh1"}),
            httpx.Response(200, json={"data": "fresh2"}),
        ]
    )
    history = respx.post(HISTORY_URL).respond(
        200, json=pt_data("getAccHisConsubDzzfLog_Recharge.json")
    )
    async with pt.PtClient(token) as client:
        await client.get_card_history(2026, 5, pt.CardHistoryType.Recharge)
        await client.get_card_history(2026, 6, pt.CardHistoryType.Recharge)
    assert csrf.call_count == 2
    assert [call.request.headers["X-XSRF-TOKEN"] for call in history.calls] == [
        "fresh1",
        "fresh2",
    ]
    assert token.headers["x-xsrf-token"] == "old"


@pytest.mark.parametrize("body", ["<html>login</html>", '{"data":null}', '{"data":123}'])
@respx.mock
async def test_bad_csrf_prevents_history_request(pt_token, body):
    respx.get(CSRF_URL).respond(200, text=body)
    with pytest.raises(pt.PtParseError):
        await pt.get_card_history(pt_token, 2026, 5, pt.CardHistoryType.Consumption)
    assert len(respx.calls) == 1


@pytest.mark.parametrize(
    "year,month,history_type",
    [
        (2026, 0, pt.CardHistoryType.Consumption),
        (2026, 13, pt.CardHistoryType.Consumption),
        (True, 1, pt.CardHistoryType.Consumption),
        (0, 1, pt.CardHistoryType.Consumption),
        (65536, 1, pt.CardHistoryType.Consumption),
        (2026, True, pt.CardHistoryType.Consumption),
        (2026, 1, "invalid"),
    ],
)
@respx.mock
async def test_invalid_selection_before_request(pt_token, year, month, history_type):
    with pytest.raises(ValueError):
        await pt.get_card_history(pt_token, year, month, history_type)
    assert len(respx.calls) == 0


@pytest.mark.parametrize("status", [302, 401, 403, 500])
@respx.mock
async def test_http_error(pt_token, status):
    respx.get(BASE_URL + "/api/hndxYkt/getCardUserInfo/info").respond(status)
    with pytest.raises(pt.PtStatusError) as caught:
        await pt.get_card_info(pt_token)
    assert caught.value.status_code == status


@respx.mock
async def test_network_error(pt_token):
    respx.get(BASE_URL + "/api/hndxYkt/getCardUserInfo/info").mock(
        side_effect=httpx.ConnectError("offline")
    )
    with pytest.raises(pt.PtNetworkError):
        await pt.get_card_info(pt_token)


async def test_client_ownership_and_injected_headers(pt_token):
    def handler(request):
        assert request.headers["cookie"] == "SESSION=pt-test"
        assert request.url.host == "pt.hnu.edu.cn"
        return httpx.Response(200, json={"data": {"unReadCount": 6}})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        async with pt.PtClient(pt_token, client=http) as client:
            assert await client.get_unread_email_count() == 6
        assert not http.is_closed
    owned = pt.PtClient(pt_token)
    async with owned:
        pass
    assert owned._client.is_closed


def test_token_immutable_and_private_cookie():
    headers = {"Cookie": "secret"}
    token = pt.PtToken.from_headers_unchecked(headers)
    headers["Cookie"] = "changed"
    assert token.headers["Cookie"] == "secret"
    assert "secret" not in repr(token)
    with pytest.raises(TypeError):
        token.headers["Cookie"] = "changed"
