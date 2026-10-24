import httpx
import pytest
import respx

from hnu_query import netflow
from hnu_query.netflow._http import BASE_URL


@pytest.mark.parametrize(
    "method,path,fixture,args,params",
    [
        (
            "get_month_detail",
            "/api/v1/history/getfloatdetailbymonth",
            "getfloatdetailbymonth.json",
            (2026, 5),
            {"month": "2026-05"},
        ),
        (
            "get_day_detail",
            "/api/v1/history/getfloatdetailbyday",
            "getfloatdetailbymonth.json",
            (2026, 5, 3),
            {"day": "20260503"},
        ),
        ("get_order", "/api/v1/historyorder/getpagedlist", "getpagedlist.json", (), {}),
        ("get_overdue_payment", "/api/v1/pay/getpayinfo", "getpayinfo.json", (), {}),
        (
            "get_this_month_info",
            "/api/v1/history/gettrafficinfobythismonth",
            "gettrafficinfobythismonth.json",
            (),
            {},
        ),
        (
            "get_unlock_status",
            "/api/v1/account/getuserinfo",
            "getuserinfo.json",
            (),
            {},
        ),
    ],
)
@respx.mock
async def test_public_query_requests(
    netflow_token, netflow_data, method, path, fixture, args, params
):
    route = respx.get(BASE_URL + path).respond(200, json=netflow_data(fixture))
    result = await getattr(netflow, method)(netflow_token, *args)
    assert result is not None
    request = route.calls.last.request
    assert dict(request.url.params) == params
    assert not request.content
    assert request.headers["cookie"] == netflow_token.headers["Cookie"]


@respx.mock
async def test_leap_day(netflow_token, netflow_data):
    route = respx.get(BASE_URL + "/api/v1/history/getfloatdetailbyday").respond(
        200, json=netflow_data("getfloatdetailbymonth.json")
    )
    await netflow.get_day_detail(netflow_token, 2024, 2, 29)
    assert route.calls.last.request.url.params["day"] == "20240229"


@pytest.mark.parametrize(
    "year,month,day",
    [
        (True, 1, 1),
        (0, 1, 1),
        (65536, 1, 1),
        (2026, 0, 1),
        (2026, 13, 1),
        (2026, 1, True),
        (2026, 2, 29),
        (2026, 4, 31),
        (2026, 1, 0),
        (2026, 1, "1"),
    ],
)
async def test_invalid_dates(netflow_token, year, month, day):
    async with netflow.NetflowClient(netflow_token) as client:
        with pytest.raises(ValueError):
            await client.get_day_detail(year, month, day)


async def test_invalid_month(netflow_token):
    async with netflow.NetflowClient(netflow_token) as client:
        with pytest.raises(ValueError):
            await client.get_month_detail(2026, 13)


@pytest.mark.parametrize("status", [302, 401, 403, 500])
@respx.mock
async def test_http_error(netflow_token, status):
    respx.get(BASE_URL + "/api/v1/pay/getpayinfo").respond(status)
    with pytest.raises(netflow.NetflowStatusError) as caught:
        await netflow.get_overdue_payment(netflow_token)
    assert caught.value.status_code == status


@respx.mock
async def test_network_error(netflow_token):
    respx.get(BASE_URL + "/api/v1/pay/getpayinfo").mock(
        side_effect=httpx.ConnectError("offline")
    )
    with pytest.raises(netflow.NetflowNetworkError):
        await netflow.get_overdue_payment(netflow_token)


@respx.mock
async def test_login_html_is_parse_error(netflow_token):
    respx.get(BASE_URL + "/api/v1/pay/getpayinfo").respond(
        200, text="<html>login</html>"
    )
    with pytest.raises(netflow.NetflowParseError):
        await netflow.get_overdue_payment(netflow_token)


async def test_client_ownership(netflow_token):
    def handler(request):
        assert request.headers["cookie"] == netflow_token.headers["Cookie"]
        assert request.url.host == "ll.hnu.edu.cn"
        return httpx.Response(200, json={"data": {"Total": 0}})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        async with netflow.NetflowClient(netflow_token, client=http) as client:
            assert await client.get_overdue_payment() == 0.0
        assert not http.is_closed
    owned = netflow.NetflowClient(netflow_token)
    async with owned:
        pass
    assert owned._client.is_closed


def test_token_immutable_and_cookie_private():
    headers = {"Cookie": "secret"}
    token = netflow.NetflowToken.from_headers_unchecked(headers)
    headers["Cookie"] = "changed"
    assert token.headers["Cookie"] == "secret"
    assert "secret" not in repr(token)
    with pytest.raises(TypeError):
        token.headers["Cookie"] = "changed"
