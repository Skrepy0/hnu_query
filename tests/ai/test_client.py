import json

import httpx
import pytest
import respx

from hnu_query import ai
from hnu_query.ai._http import BASE_URL


@respx.mock
async def test_requests_and_rust_responses(ai_token, sample):
    routes = [
        respx.get(BASE_URL + "/api/tokens").respond(text=sample("tokens.json")),
        respx.get(BASE_URL + "/api/tokens/3296/key").respond(text=sample("key.json")),
        respx.post(BASE_URL + "/api/apply-token").respond(
            text=sample("apply-token.json")
        ),
        respx.delete(BASE_URL + "/api/tokens/3296").respond(json={"success": True}),
        respx.get(BASE_URL + "/api/user-info").respond(text=sample("user-info.json")),
    ]
    async with ai.AiClient(ai_token) as client:
        assert (await client.get_token_list())[0].id == 3296
        assert await client.get_token_key(3296) == "zF0Asilc5eRnGbwafZ5gDzIH"
        assert await client.create_token("\u6d4b\u8bd5") is None
        assert await client.delete_token(3296) is None
        assert await client.get_user_remaining_quota() == 114514
    assert client._client.is_closed
    assert json.loads(routes[2].calls.last.request.content) == {
        "name": "\u6d4b\u8bd5",
        "quota": 2000000,
    }
    for route in routes:
        assert route.call_count == 1
        assert route.calls.last.request.headers["authorization"] == "Bearer test-bearer"
        assert route.calls.last.request.headers["cookie"] == "session=test"


@pytest.mark.parametrize(
    "method,path,function,args,result",
    [
        ("GET", "/api/tokens", ai.get_token_list, (), {"data": []}),
        ("GET", "/api/tokens/1/key", ai.get_token_key, (1,), {"data": {"key": "key"}}),
        ("POST", "/api/apply-token", ai.create_token, ("name",), {"success": True}),
        ("DELETE", "/api/tokens/1", ai.delete_token, (1,), {"success": True}),
        (
            "GET",
            "/api/user-info",
            ai.get_user_remaining_quota,
            (),
            {"data": {"total_granted": 1}},
        ),
    ],
)
@respx.mock
async def test_module_functions(ai_token, method, path, function, args, result):
    route = respx.route(method=method, url=BASE_URL + path).respond(json=result)
    await function(ai_token, *args)
    assert route.call_count == 1


@pytest.mark.parametrize(
    "method,args", [("create_token", ("name",)), ("delete_token", (1,))]
)
@respx.mock
async def test_action_failure(ai_token, method, args):
    respx.route().respond(json={"success": False})
    async with ai.AiClient(ai_token) as client:
        with pytest.raises(ai.AiActionError):
            await getattr(client, method)(*args)


@pytest.mark.parametrize(
    "status,error",
    [
        (302, ai.TokenExpired),
        (401, ai.TokenExpired),
        (403, ai.TokenExpired),
        (500, ai.AiStatusError),
        (404, ai.AiStatusError),
    ],
)
@respx.mock
async def test_http_errors_do_not_follow_redirect(ai_token, status, error):
    respx.get(BASE_URL + "/api/tokens").respond(
        status, headers={"location": "https://example.org"}
    )
    async with httpx.AsyncClient(follow_redirects=True) as http:
        async with ai.AiClient(ai_token, client=http) as client:
            with pytest.raises(error):
                await client.get_token_list()
        assert not http.is_closed
    assert len(respx.calls) == 1


@respx.mock
async def test_network_and_parse_failures(ai_token):
    route = respx.get(BASE_URL + "/api/tokens")
    route.mock(side_effect=httpx.ConnectError("offline"))
    async with ai.AiClient(ai_token) as client:
        with pytest.raises(ai.AiNetworkError):
            await client.get_token_list()
        route.respond(text="invalid")
        with pytest.raises(ai.AiParseError):
            await client.get_token_list()


@pytest.mark.parametrize("id", [-1, 2**64, True, "1", 1.0])
@pytest.mark.parametrize("method", ["get_token_key", "delete_token"])
async def test_bad_id_before_request(ai_token, id, method):
    async with ai.AiClient(ai_token) as client:
        with pytest.raises(ValueError):
            await getattr(client, method)(id)


async def test_bad_name_and_connection_lifecycle(ai_token):
    client = ai.AiClient(ai_token)
    with pytest.raises(ValueError):
        async with client:
            await client.create_token(None)
    assert client._client.is_closed


def test_token_snapshot_and_redaction():
    headers = {"Authorization": "Bearer secret", "Cookie": "private"}
    token = ai.AiToken.from_headers_unchecked(headers)
    headers.clear()
    assert token.headers["Cookie"] == "private"
    assert "secret" not in repr(token) and "private" not in repr(token)
    with pytest.raises(TypeError):
        token.headers["Cookie"] = "changed"
