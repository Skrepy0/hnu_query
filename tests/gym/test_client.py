import asyncio
from urllib.parse import parse_qs

import httpx
import pytest
import respx

from hnu_query import gym
from hnu_query.gym._http import API_URL


@respx.mock
async def test_grade_requests(gym_token, gym_data):
    summary = respx.post(API_URL + "/Report/getStudentScore").respond(
        200, json=gym_data("getStudentScore.json")
    )
    detail = respx.post(API_URL + "/Report/getEyeDetails").respond(
        200, json=gym_data("getEyeDetails.json")
    )
    result = await gym.get_grade(gym_token, 2025)
    assert result.score == 56.2
    for route in (summary, detail):
        request = route.calls.last.request
        assert parse_qs(request.content.decode()) == {"year_num": ["2025"]}
        assert request.headers["cookie"] == "PHPSESSID=gym-test"


@respx.mock
async def test_appointment_requests(gym_token, appointments):
    respx.post(API_URL + "/Appoint/getStudentClass").respond(200, json=appointments)
    detail = respx.post(API_URL + "/Appoint/getSchoolFitClassDetail").respond(
        200,
        json={
            "status": 1,
            "info": "成功",
            "data": {"class_desc": "预约说明", "appo_type": 0},
        },
    )
    result = await gym.get_appointment(gym_token)
    assert len(result) == 2
    assert result[1].status == 2
    assert detail.call_count == 2
    for call, row in zip(detail.calls, appointments["data"]):
        assert parse_qs(call.request.content.decode()) == {
            "class_id": [str(row["class_id"])],
            "class_time": [row["class_time"]],
            "test_time": [row["test_time"]],
        }
        assert call.request.headers["cookie"] == "PHPSESSID=gym-test"


@respx.mock
async def test_empty_appointments(gym_token):
    respx.post(API_URL + "/Appoint/getStudentClass").respond(
        200, json={"info": "成功", "status": 1, "data": []}
    )
    assert await gym.get_appointment(gym_token) == []
    assert len(respx.calls) == 1


@pytest.mark.parametrize(
    "status,error", [(500, gym.GymStatusError), (302, gym.GymStatusError)]
)
@respx.mock
async def test_http_error(gym_token, status, error):
    respx.post(API_URL + "/Appoint/getStudentClass").respond(status)
    with pytest.raises(error):
        await gym.get_appointment(gym_token)


@respx.mock
async def test_network_error(gym_token):
    respx.post(API_URL + "/Appoint/getStudentClass").mock(
        side_effect=httpx.ConnectError("offline")
    )
    with pytest.raises(gym.GymNetworkError):
        await gym.get_appointment(gym_token)


@respx.mock
async def test_expired_detail(gym_token, appointments):
    respx.post(API_URL + "/Appoint/getStudentClass").respond(200, json=appointments)
    route = respx.post(API_URL + "/Appoint/getSchoolFitClassDetail").respond(
        200,
        json={
            "info": "登录失效",
            "status": -1,
            "data": [],
        },
    )
    with pytest.raises(gym.TokenExpired):
        await gym.get_appointment(gym_token)
    assert route.call_count == 1


async def test_connection_ownership(gym_token):
    def handler(request):
        assert request.headers["cookie"] == "PHPSESSID=gym-test"
        return httpx.Response(200, json={"info": "成功", "status": 1, "data": []})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        async with gym.GymClient(gym_token, client=http) as client:
            assert await client.get_appointment() == []
        assert not http.is_closed
    owned = gym.GymClient(gym_token)
    async with owned:
        pass
    assert owned._client.is_closed


async def test_concurrent_requests_cancel_sibling_on_error(gym_token):
    detail_started = asyncio.Event()
    detail_cancelled = asyncio.Event()

    async def handler(request):
        if request.url.path.endswith("getEyeDetails"):
            detail_started.set()
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                detail_cancelled.set()
                raise
        await detail_started.wait()
        return httpx.Response(500)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        async with gym.GymClient(gym_token, client=http) as client:
            with pytest.raises(gym.GymStatusError):
                await asyncio.wait_for(client.get_grade(2025), timeout=2)
        assert detail_cancelled.is_set()


@pytest.mark.parametrize("year", [-1, 65536, True, "2025"])
async def test_invalid_year(gym_token, year):
    async with gym.GymClient(gym_token) as client:
        with pytest.raises(ValueError):
            await client.get_grade(year)


def test_token_immutable():
    headers = {"Cookie": "secret"}
    token = gym.GymToken.from_headers_unchecked(headers)
    headers["Cookie"] = "changed"
    assert token.headers["Cookie"] == "secret"
    assert "secret" not in repr(token)
    with pytest.raises(TypeError):
        token.headers["Cookie"] = "changed"
