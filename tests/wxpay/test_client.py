import asyncio

import httpx
import pytest
import respx

from hnu_query import wxpay
from hnu_query.wxpay.client import QUERY_URL
from hnu_query.xgxt import Dormitory, parse_dormitory


@respx.mock
async def test_request_headers_params_and_unit():
    route = respx.get(QUERY_URL).respond(200, json={"data": {"Balance": "146.88度"}})
    assert (
        await wxpay.get_electricity(Dormitory.from_parsed_value("天马园区", "三区13栋", "1&x=2"))
        == "146.88度"
    )
    request = route.calls.last.request
    assert dict(request.url.params) == {
        "parkNo": "3",
        "buildingNo": "42",
        "rechargeType": "2",
        "roomNo": "1&x=2",
    }
    assert request.headers["referer"] == "http://wxpay.hnu.edu.cn/electricCharge/home/"
    assert request.headers["x-requested-with"] == "XMLHttpRequest"
    assert "cookie" not in request.headers


@pytest.mark.parametrize("build,north,south", [("2栋", "52", "53"), ("3栋", "54", "55")])
@pytest.mark.parametrize("success_side", ["north", "south"])
@respx.mock
async def test_wangluqiao_sides(build, north, south, success_side):
    north_route = respx.get(
        QUERY_URL,
        params={
            "parkNo": "6",
            "buildingNo": north,
            "rechargeType": "2",
            "roomNo": "101",
        },
    ).respond(
        200 if success_side == "north" else 500,
        json={"data": {"Balance": "11.00元"}},
    )
    south_route = respx.get(
        QUERY_URL,
        params={
            "parkNo": "6",
            "buildingNo": south,
            "rechargeType": "2",
            "roomNo": "101",
        },
    ).respond(
        200 if success_side == "south" else 500,
        json={"data": {"Balance": "22.00度"}},
    )
    result = await wxpay.get_electricity(
        Dormitory.from_parsed_value("望麓桥学生公寓", build, "101")
    )
    assert result == ("11.00元" if success_side == "north" else "22.00度")
    assert north_route.call_count == south_route.call_count == 1
    assert respx.calls[0].request.url.params["buildingNo"] == north


@pytest.mark.parametrize("status", [200, 500])
@respx.mock
async def test_ambiguous_two_successes_or_two_failures(status):
    route = respx.get(QUERY_URL).respond(status, json={"data": {"Balance": "100度"}})
    with pytest.raises(wxpay.WxpayAmbiguityError):
        await wxpay.get_electricity(Dormitory.from_parsed_value("望麓桥学生公寓", "2栋", "101"))
    assert route.call_count == 2


@respx.mock
async def test_side_selection_uses_request_success_before_parsing():
    route = respx.get(QUERY_URL).mock(
        side_effect=[
            httpx.Response(200, json={"data": None}),
            httpx.Response(500),
        ]
    )
    with pytest.raises(wxpay.WxpayParseError):
        await wxpay.get_electricity(Dormitory.from_parsed_value("望麓桥学生公寓", "2栋", "101"))
    assert route.call_count == 2


@respx.mock
async def test_side_network_failure_then_success():
    respx.get(QUERY_URL).mock(
        side_effect=[
            httpx.ConnectError("offline"),
            httpx.Response(200, json={"data": {"Balance": "20度"}}),
        ]
    )
    assert (
        await wxpay.get_electricity(Dormitory.from_parsed_value("望麓桥学生公寓", "3栋", "101"))
        == "20度"
    )


@pytest.mark.parametrize("status", [302, 403, 500])
@respx.mock
async def test_http_error(status):
    respx.get(QUERY_URL).respond(status)
    with pytest.raises(wxpay.WxpayStatusError) as caught:
        await wxpay.get_electricity(Dormitory.from_parsed_value("南校区", "10舍", "101"))
    assert caught.value.status_code == status


@respx.mock
async def test_network_error():
    respx.get(QUERY_URL).mock(side_effect=httpx.ConnectError("offline"))
    with pytest.raises(wxpay.WxpayNetworkError):
        await wxpay.get_electricity(Dormitory.from_parsed_value("南校区", "10舍", "101"))


@respx.mock
async def test_unparsed_room_prevents_requests():
    with pytest.raises(ValueError):
        await wxpay.get_electricity(parse_dormitory("未知公寓", "101"))
    assert len(respx.calls) == 0


async def test_cancellation_propagates_without_trying_other_side():
    calls = []

    async def handler(request):
        calls.append(request)
        raise asyncio.CancelledError()

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        async with wxpay.WxpayClient(client=http) as client:
            with pytest.raises(asyncio.CancelledError):
                await client.get_electricity(
                    Dormitory.from_parsed_value("望麓桥学生公寓", "2栋", "101")
                )
        assert not http.is_closed
    assert len(calls) == 1


async def test_owned_client_closes():
    client = wxpay.WxpayClient()
    async with client:
        pass
    assert client._client.is_closed
