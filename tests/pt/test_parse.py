import json
from datetime import datetime

import pytest

from hnu_query.pt import PtParseError, parse


def test_card_info_rust_fixture(pt_data):
    result = parse.card_info(json.dumps(pt_data("getCardUserInfo.json")))
    assert result.model_dump() == {"id": 123456, "balance": 75.28}


def test_consumption_rust_fixture(pt_data):
    history = parse.card_history(
        json.dumps(pt_data("getAccHisConsubDzzfLog_Consumption.json"))
    )
    assert (history.count, history.total, len(history.items)) == (7, -51.0, 7)
    assert history.items[0].model_dump() == {
        "date_time": datetime(2026, 5, 30, 17, 38, 44),
        "journal_time": datetime(2026, 5, 30, 17, 38, 42),
        "status": "正常",
        "id": 56,
        "now_balance": 71.43,
        "amount": -3.0,
        "location": "天马二食堂二楼",
        "name": "持卡人消费",
    }
    assert all(item.amount <= 0 for item in history.items)
    assert (
        json.loads(history.model_dump_json())["items"][0]["date_time"]
        == "2026-05-30T17:38:44"
    )


def test_recharge_rust_fixture(pt_data):
    history = parse.card_history(
        json.dumps(pt_data("getAccHisConsubDzzfLog_Recharge.json"))
    )
    assert (history.count, history.total, len(history.items)) == (3, 50.0, 3)
    assert history.items[0].model_dump() == {
        "date_time": datetime(2026, 5, 25, 11, 57, 41),
        "journal_time": datetime(2026, 5, 25, 11, 57, 41),
        "status": "正常",
        "id": 50,
        "now_balance": 90.78,
        "amount": 10.0,
        "location": None,
        "name": "银行转账",
    }


def test_history_formatted_balance_and_location(pt_data):
    data = pt_data("getAccHisConsubDzzfLog_Consumption.json")
    data["data"]["webTrjnDTO"][0].update(nowAmt=" \t1, 359.30 \n", sysname1="  食堂  ")
    first = parse.card_history(json.dumps(data)).items[0]
    assert first.now_balance == 1359.3
    assert first.location == "食堂"
    data["data"]["webTrjnDTO"][0]["sysname1"] = "  "
    assert parse.card_history(json.dumps(data)).items[0].location == ""


@pytest.mark.parametrize("variant", ["missing", "null", "empty"])
def test_empty_history(variant):
    data = {"amt": 0, "count": 0}
    if variant != "missing":
        data["webTrjnDTO"] = None if variant == "null" else []
    result = parse.card_history(json.dumps({"data": data}))
    assert result.model_dump() == {"total": 0.0, "count": 0, "items": []}


@pytest.mark.parametrize("count,expected", [(2.9, 2), (-1, 0), (1e30, 2**32 - 1)])
def test_rust_count_cast(count, expected):
    result = parse.card_history(json.dumps({"data": {"amt": 0, "count": count}}))
    assert result.count == expected


def test_email_fixtures(pt_data):
    assert (
        parse.email_unread_count(json.dumps(pt_data("email_unread_success.json"))) == 6
    )
    assert (
        parse.email_unread_count(json.dumps(pt_data("email_unread_fail.json"))) is None
    )
    assert parse.email_unread_count('{"data":{"unReadCount":0}}') == 0
    assert parse.email_unread_count('{"data":{"unReadCount":null}}') is None


@pytest.mark.parametrize("count", [True, -1, 2**32, "6", 6.0])
def test_invalid_email_count(count):
    with pytest.raises(PtParseError):
        parse.email_unread_count(json.dumps({"data": {"unReadCount": count}}))


def test_csrf_token():
    assert parse.csrf_token('{"data":"csrf-value"}') == "csrf-value"


@pytest.mark.parametrize(
    "parser",
    [parse.card_info, parse.card_history, parse.email_unread_count, parse.csrf_token],
)
@pytest.mark.parametrize(
    "body", ["<html>login</html>", "null", "[]", "{}", '{"data":null}']
)
def test_malformed_response(parser, body):
    with pytest.raises(PtParseError):
        parser(body)


@pytest.mark.parametrize(
    "account,balance",
    [
        (True, "100"),
        (-1, "100"),
        (2**32, "100"),
        (1, 100),
        (1, "wrong"),
        (1, "NaN"),
        (1, "1_000"),
    ],
)
def test_invalid_card_info(account, balance):
    with pytest.raises(PtParseError):
        parse.card_info(json.dumps({"data": {"account": account, "balance": balance}}))


@pytest.mark.parametrize(
    "key,value",
    [
        ("usedcardnum", True),
        ("usedcardnum", -1),
        ("fTranAmt", "bad"),
        ("nowAmt", None),
        ("effectdate", "2026/02/30 00:00:00"),
        ("jndatetime", "invalid"),
        ("sysname1", 10),
    ],
)
def test_invalid_history_item(pt_data, key, value):
    data = pt_data("getAccHisConsubDzzfLog_Consumption.json")
    data["data"]["webTrjnDTO"][0][key] = value
    with pytest.raises(PtParseError):
        parse.card_history(json.dumps(data))
