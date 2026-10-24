import asyncio
from datetime import date, datetime, timezone

import httpx
import pytest
import respx

from hnu_query import iportal
from hnu_query.iportal._http import BASE_URL


@pytest.mark.parametrize(
    "method,path,fixture,args,params",
    [
        ("get_account_info", "/personal/frontend/data/info", "info/info.json", (), {}),
        (
            "get_card_info",
            "/hnu/frontend/user/card-balance",
            "card/balance.json",
            (),
            {},
        ),
        (
            "get_term_info",
            "/hnu/frontend/term",
            "term/term.json",
            (datetime(1970, 1, 1, 0, 0, 1),),
            {"current_time": "1"},
        ),
        (
            "get_apply_list",
            "/personal/frontend/task/apply",
            "task/apply_list.json",
            (2, 10),
            {"type": "all", "page": "2", "pageSize": "10"},
        ),
        (
            "get_card_transaction_records",
            "/hnu/frontend/user/card-details",
            "card/transactions.json",
            ("114514&x=1", date(2026, 5, 1), date(2026, 5, 31), 10, 2),
            {
                "query_start": "2026-05-01",
                "query_end": "2026-05-31",
                "page_size": "10",
                "page": "2",
                "account": "114514&x=1",
            },
        ),
    ],
)
@respx.mock
async def test_public_queries(
    iportal_token, iportal_data, method, path, fixture, args, params
):
    route = respx.get(BASE_URL + path).respond(200, json=iportal_data(fixture))
    result = await getattr(iportal, method)(iportal_token, *args)
    assert result is not None
    request = route.calls.last.request
    assert dict(request.url.params) == params
    assert request.headers["cookie"] == "session=iportal-test"
    assert not request.content


@respx.mock
async def test_personal_data_queries(iportal_token, iportal_data):
    ids = iportal_data("personal/ids.json")
    respx.get(
        BASE_URL + "/personal/frontend/data/items", params={"type": "personal_data"}
    ).respond(200, json=ids)
    files = {
        "book.bookNum": "lib",
        "mail.unread": "email",
        "card.balance": "card",
        "statistic.lastLoginTime": "lastlogin",
        "net.used": "net",
    }
    for item in ids["d"]["data"]:
        respx.get(
            BASE_URL + "/personal/frontend/data/detail", params={"id": item["id"]}
        ).respond(
            200,
            json=iportal_data("personal/id_data/" + files[item["key"]] + ".json"),
        )
    result = await iportal.get_personal_data(iportal_token)
    assert result.balance == 81.81 and result.mail_unread == 1
    assert result.net_used == 114514 * 1024**3
    assert len(respx.calls) == 6
    assert all(
        call.request.headers["cookie"] == "session=iportal-test" for call in respx.calls
    )


@respx.mock
async def test_empty_personal_data(iportal_token):
    respx.get(BASE_URL + "/personal/frontend/data/items").respond(
        200, json={"e": 0, "d": {"data": []}}
    )
    result = await iportal.get_personal_data(iportal_token)
    assert all(value is None for value in result.model_dump().values())
    assert len(respx.calls) == 1


@pytest.mark.parametrize("failure", ["http", "expired", "cancel"])
async def test_personal_concurrency_cleanup(iportal_token, failure):
    started, cancelled = asyncio.Event(), asyncio.Event()

    async def handler(request):
        if request.url.path.endswith("items"):
            return httpx.Response(
                200,
                json={
                    "e": 0,
                    "d": {
                        "data": [
                            {"key": "card.balance", "id": "first"},
                            {"key": "net.used", "id": "second"},
                        ]
                    },
                },
            )
        if request.url.params["id"] == "second":
            started.set()
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                cancelled.set()
                raise
        await started.wait()
        if failure == "cancel":
            raise asyncio.CancelledError()
        return httpx.Response(302 if failure == "expired" else 500)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        async with iportal.IPortalClient(iportal_token, client=http) as client:
            error = {
                "http": iportal.IPortalStatusError,
                "expired": iportal.IPortalTokenExpired,
                "cancel": asyncio.CancelledError,
            }[failure]
            with pytest.raises(error):
                await asyncio.wait_for(client.get_personal_data(), timeout=2)
    assert cancelled.is_set()


@pytest.mark.parametrize(
    "status,error",
    [
        (302, iportal.IPortalTokenExpired),
        (303, iportal.IPortalStatusError),
        (401, iportal.IPortalStatusError),
        (500, iportal.IPortalStatusError),
    ],
)
@respx.mock
async def test_query_http_errors(iportal_token, status, error):
    respx.get(BASE_URL + "/personal/frontend/data/info").respond(status)
    with pytest.raises(error):
        await iportal.get_account_info(iportal_token)


@respx.mock
async def test_query_network_error(iportal_token):
    respx.get(BASE_URL + "/personal/frontend/data/info").mock(
        side_effect=httpx.ConnectError("offline")
    )
    with pytest.raises(iportal.IPortalNetworkError):
        await iportal.get_account_info(iportal_token)


@pytest.mark.parametrize(
    "time", [date(2026, 1, 1), datetime(2026, 1, 1, tzinfo=timezone.utc), "2026-01-01"]
)
async def test_term_requires_naive_datetime(iportal_token, time):
    async with iportal.IPortalClient(iportal_token) as client:
        with pytest.raises(ValueError):
            await client.get_term_info(time)


@pytest.mark.parametrize("page,size", [(-1, 10), (True, 10), (1, 2**32), (1, "10")])
async def test_invalid_paging(iportal_token, page, size):
    async with iportal.IPortalClient(iportal_token) as client:
        with pytest.raises(ValueError):
            await client.get_apply_list(page, size)
        with pytest.raises(ValueError):
            await client.get_card_transaction_records(
                "id", date(2026, 1, 1), date(2026, 1, 2), size, page
            )


@pytest.mark.parametrize(
    "start,end",
    [(date(2026, 2, 1), date(2026, 1, 1)), (datetime(2026, 1, 1), date(2026, 1, 2))],
)
async def test_invalid_date_range(iportal_token, start, end):
    async with iportal.IPortalClient(iportal_token) as client:
        with pytest.raises(ValueError):
            await client.get_card_transaction_records("id", start, end, 10, 1)


async def test_connection_ownership(iportal_token):
    def handler(request):
        assert request.headers["cookie"] == "session=iportal-test"
        return httpx.Response(
            200, json={"e": 0, "d": {"account": "id", "balance": 10.0}}
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        async with iportal.IPortalClient(iportal_token, client=http) as client:
            assert (await client.get_card_info()).balance == 10.0
        assert not http.is_closed
    owned = iportal.IPortalClient(iportal_token)
    async with owned:
        pass
    assert owned._client.is_closed


def test_token_immutable_and_private():
    headers = {"Cookie": "secret"}
    token = iportal.IPortalToken.from_headers_unchecked(headers)
    headers["Cookie"] = "changed"
    assert token.headers["Cookie"] == "secret"
    assert "secret" not in repr(token)
    with pytest.raises(TypeError):
        token.headers["Cookie"] = "changed"
