import asyncio
import json

import httpx
import pytest
import respx

from hnu_query import xgxt
from hnu_query.xgxt._http import BASE_URL


@respx.mock
async def test_three_form_requests_and_merge_order(xgxt_token, xgxt_text):
    routes = []
    for group, file in (
        ("userInfo", "user_info.json"),
        ("zxxx", "in_school_info.json"),
        ("lxfs1", "contact_info.json"),
    ):
        data = json.loads(xgxt_text(file))
        if group == "lxfs1":
            data["data"]["groupFields"][0]["fields"].append(
                {"fieldName": "学号", "defaultValue": "last-wins"}
            )
        routes.append(
            respx.get(
                BASE_URL + f"/zftal-xgxt-web/dynamic/form/group/{group}/default.zf"
            ).respond(200, json=data)
        )
    result = await xgxt.get_person_info(xgxt_token)
    assert result.stu_id == "last-wins" and result.enter_year == 2025
    for route in routes:
        request = route.calls.last.request
        assert dict(request.url.params) == {"dataId": "null"}
        assert request.headers["cookie"] == "JSESSIONID=xgxt-test"


@pytest.mark.parametrize("failure", ["http", "network", "cancel"])
async def test_parallel_cleanup(xgxt_token, failure):
    started = [asyncio.Event(), asyncio.Event()]
    cancelled = [asyncio.Event(), asyncio.Event()]

    async def handler(request):
        group = request.url.path.split("/")[-2]
        if group == "userInfo":
            await asyncio.gather(*(event.wait() for event in started))
            if failure == "cancel":
                raise asyncio.CancelledError()
            if failure == "network":
                raise httpx.ConnectError("offline")
            return httpx.Response(500)
        index = 0 if group == "zxxx" else 1
        started[index].set()
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            cancelled[index].set()
            raise

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        async with xgxt.XgxtClient(xgxt_token, client=http) as client:
            error = {
                "http": xgxt.XgxtStatusError,
                "network": xgxt.XgxtNetworkError,
                "cancel": asyncio.CancelledError,
            }[failure]
            with pytest.raises(error):
                await asyncio.wait_for(client.get_person_info(), timeout=2)
        assert not http.is_closed
    assert all(event.is_set() for event in cancelled)


async def test_owned_client_closes(xgxt_token):
    client = xgxt.XgxtClient(xgxt_token)
    async with client:
        pass
    assert client._client.is_closed


def test_token_immutable_and_private():
    headers = {"Cookie": "secret"}
    token = xgxt.XgxtToken.from_headers_unchecked(headers)
    headers["Cookie"] = "changed"
    assert token.headers["Cookie"] == "secret"
    assert "secret" not in repr(token)
    with pytest.raises(TypeError):
        token.headers["Cookie"] = "changed"
