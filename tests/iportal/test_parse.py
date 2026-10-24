import json
from datetime import datetime

import pytest

from hnu_query.iportal import (
    ApplyStatus,
    Gender,
    IPortalParseError,
    TermType,
    TransactionType,
    parse,
)


def test_account_rust_fixture(iportal_text):
    result = parse.account_info(iportal_text("info/info.json"))
    assert result.model_dump() == {
        "uid": "114514",
        "name": "电棍",
        "id": "191908100721",
        "identity": "本科生",
        "identity_id": 2002,
        "gender": Gender.Male,
        "depart": "神秘学院",
        "avatar": "http://filtered",
    }


@pytest.mark.parametrize(
    "key,value",
    [("sex", 0), ("sex", True), ("identity_id", "-1"), ("identity_id", str(2**64))],
)
def test_invalid_account_fields(iportal_data, key, value):
    data = iportal_data("info/info.json")
    data["d"]["info"][key] = value
    with pytest.raises(IPortalParseError):
        parse.account_info(json.dumps(data))


def test_female(iportal_data):
    data = iportal_data("info/info.json")
    data["d"]["info"]["sex"] = 2
    assert parse.account_info(json.dumps(data)).gender is Gender.Female


def test_personal_ids_and_aggregate_rust_fixtures(iportal_text):
    ids = parse.personal_data_query_ids(iportal_text("personal/ids.json"))
    assert len(ids) == 5
    assert ids[1:] == [
        ("mail.unread", "1919810"),
        ("card.balance", "114514"),
        ("statistic.lastLoginTime", "168"),
        ("net.used", "0d000721"),
    ]
    result = parse.personal_data(
        [
            (key, iportal_text("personal/id_data/" + name + ".json"))
            for key, name in [
                ("book.bookNum", "lib"),
                ("mail.unread", "email"),
                ("card.balance", "card"),
                ("statistic.lastLoginTime", "lastlogin"),
                ("net.used", "net"),
            ]
        ]
    )
    assert result.model_dump() == {
        "lib_borrow": 0,
        "email": "admin@hnu.edu.cn",
        "mail_unread": 1,
        "balance": 81.81,
        "last_login_time": datetime(2077, 6, 15, 16, 4),
        "net_used": 114514 * 1024**3,
    }
    assert all(value is None for value in parse.personal_data([]).model_dump().values())


@pytest.mark.parametrize(
    "unit,factor",
    [
        ("G", 1024**3),
        (" gb ", 1024**3),
        ("MB", 1024**2),
        ("m", 1024**2),
        ("KB", 1024),
        ("k", 1024),
        ("B", 1),
        (None, 1),
        ("unknown", 1),
    ],
)
def test_net_units(unit, factor):
    assert parse.net_convert_to_byte(2, unit) == 2 * factor


@pytest.mark.parametrize(
    "value,expected",
    [
        ("invalid", 0),
        ("-1", 0),
        ("1.9", 1),
        ("NaN", 0),
        ("inf", 2**64 - 1),
        ("1e30", 2**64 - 1),
    ],
)
def test_net_fallback_and_cast(value, expected):
    body = json.dumps({"e": 0, "d": {"data": {"name": "流量", "value": value}}})
    assert parse.personal_data([("net.used", body)]).net_used == expected


def test_invalid_last_login_is_none_and_title_alias():
    body = '{"e":0,"d":{"data":{"title":"登录时间","value":"invalid"}}}'
    assert (
        parse.personal_data([("statistic.lastLoginTime", body)]).last_login_time is None
    )
    body = '{"e":0,"d":{"data":{"title":"图书","value":"3"}}}'
    assert parse.personal_data([("book.bookNum", body)]).lib_borrow == 3


@pytest.mark.parametrize("value", [True, None, [], {}])
def test_invalid_personal_value(value):
    body = json.dumps({"e": 0, "d": {"data": {"name": "图书", "value": value}}})
    with pytest.raises(IPortalParseError):
        parse.personal_data([("book.bookNum", body)])


def test_unknown_personal_key():
    with pytest.raises(IPortalParseError):
        parse.personal_data_query_ids(
            '{"e":0,"d":{"data":[{"key":"unknown","id":"x"}]}}'
        )
    with pytest.raises(IPortalParseError):
        parse.personal_data(
            [("unknown", '{"e":0,"d":{"data":{"name":"x","value":1}}}')]
        )


def test_term_rust_fixture(iportal_text):
    result = parse.term_info(iportal_text("term/term.json"))
    assert result.model_dump() == {
        "start_date": datetime(2026, 7, 5),
        "end_date": datetime(2026, 9, 12),
        "term": TermType.SummerVacation,
        "year": "2025-2026",
        "week": 9,
    }


@pytest.mark.parametrize(
    "code,expected",
    [
        ("1", TermType.Autumn),
        ("2", TermType.WinterVacation),
        ("3", TermType.Spring),
        ("4", TermType.SummerVacation),
    ],
)
def test_term_codes(iportal_data, code, expected):
    data = iportal_data("term/term.json")
    data["d"]["term"] = code
    assert parse.term_info(json.dumps(data)).term is expected


def test_card_rust_fixtures(iportal_text):
    assert parse.card_info(iportal_text("card/balance.json")).model_dump() == {
        "account": "114514",
        "balance": 1919.81,
    }
    result = parse.card_transaction_records(iportal_text("card/transactions.json"))
    assert (
        result.has_next_page and result.total_count == 11 and len(result.records) == 10
    )
    assert result.records[0].model_dump() == {
        "merchant_name": "天马二食堂二楼",
        "merchant_account": 1000006,
        "pay_time": datetime(2026, 9, 13, 11, 47, 30),
        "transaction_amount": -200,
        "transaction_type": TransactionType.Consumption,
    }


@pytest.mark.parametrize(
    "code,expected",
    [
        (15, TransactionType.Consumption),
        (16, TransactionType.Recharge),
        (17, TransactionType.Benefit),
        (22, TransactionType.MoneyTransfer),
        (6, TransactionType.EAccountOpening),
        (1, TransactionType.HolderAccountOpening),
        (99, TransactionType.QRCodeConsumption),
        (27, TransactionType.Withholding),
    ],
)
def test_transaction_codes(iportal_data, code, expected):
    data = iportal_data("card/transactions.json")
    data["d"]["total"][0]["trancode"] = str(code)
    result = parse.card_transaction_records(json.dumps(data))
    assert result.records[0].transaction_type is expected


@pytest.mark.parametrize(
    "key,value",
    [
        ("trancode", "999"),
        ("mercacc", "-1"),
        ("mercacc", str(2**64)),
        ("sign_tranamt", str(2**63)),
        ("occtime", "20260230120000"),
    ],
)
def test_invalid_transactions(iportal_data, key, value):
    data = iportal_data("card/transactions.json")
    data["d"]["total"][0][key] = value
    with pytest.raises(IPortalParseError):
        parse.card_transaction_records(json.dumps(data))


def test_empty_transactions():
    result = parse.card_transaction_records(
        '{"e":0,"d":{"nextpage":"0","rowcount":"0","total":[]}}'
    )
    assert result.model_dump() == {
        "has_next_page": False,
        "total_count": 0,
        "records": [],
    }


def test_apply_rust_fixture(iportal_text):
    result = parse.apply_list(iportal_text("task/apply_list.json"))
    assert result.total == 1
    assert result.list[0].model_dump() == {
        "id": 100001,
        "app_name": "测试事项",
        "creator_name": "测试用户",
        "creator_department": "测试学院",
        "created": datetime(2024, 1, 1, 10, 0, 1),
        "finished": datetime(2024, 1, 1, 10, 30),
        "status": ApplyStatus.Completed,
    }


@pytest.mark.parametrize(
    "code,expected",
    [(0, ApplyStatus.Pending), (1, ApplyStatus.Processing), (2, ApplyStatus.Completed)],
)
def test_apply_status_and_unfinished(iportal_data, code, expected):
    data = iportal_data("task/apply_list.json")
    data["d"]["list"][0].update(inst_status=code, inst_finished=None)
    data["d"]["total"] = 50
    result = parse.apply_list(json.dumps(data))
    assert result.total == 50 and len(result.list) == 1
    assert result.list[0].status is expected
    assert result.list[0].finished is None


@pytest.mark.parametrize(
    "key,value",
    [("inst_status", 3), ("inst_finished", ""), ("created", "invalid"), ("id", True)],
)
def test_invalid_apply(iportal_data, key, value):
    data = iportal_data("task/apply_list.json")
    data["d"]["list"][0][key] = value
    with pytest.raises(IPortalParseError):
        parse.apply_list(json.dumps(data))


@pytest.mark.parametrize(
    "parser,fixture",
    [
        (parse.account_info, "info/info_invalid_shape.json"),
        (parse.term_info, "term/term_invalid_date.json"),
        (parse.card_transaction_records, "card/transactions_invalid_time.json"),
        (parse.card_transaction_records, "card/transactions_invalid_shape.json"),
        (parse.iportal_jsondata_precheck, "error.json"),
        (parse.iportal_jsondata_precheck, "malformed.json"),
    ],
)
def test_rust_invalid_fixtures(iportal_text, parser, fixture):
    with pytest.raises(IPortalParseError):
        parser(iportal_text(fixture))


@pytest.mark.parametrize(
    "parser",
    [
        parse.account_info,
        parse.personal_data_query_ids,
        parse.term_info,
        parse.card_info,
        parse.card_transaction_records,
        parse.apply_list,
    ],
)
@pytest.mark.parametrize(
    "body",
    [
        "<html>login</html>",
        "null",
        "{}",
        '{"e":true,"d":{}}',
        '{"e":1,"m":"失败","d":{}}',
        '{"e":0,"d":null}',
    ],
)
def test_bad_responses(parser, body):
    with pytest.raises(IPortalParseError):
        parser(body)
