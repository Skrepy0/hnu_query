import json
from datetime import datetime

import pytest

from hnu_query.netflow import NetflowParseError, UnlockStatus, parse


def test_detail_rust_fixture(netflow_data):
    result = parse.detail(json.dumps(netflow_data("getfloatdetailbymonth.json")))
    assert (result.download, result.upload, result.total) == (
        1751143.21,
        155597061.0,
        1948767711.0,
    )
    assert len(result.items) == 3
    assert result.items[0].model_dump() == {
        "app": "/网络游戏/steam平台",
        "total": 703434.19,
        "download": 678507.29,
        "upload": 24926.9,
        "percentage": 0.37,
    }


def test_order_rust_fixture(netflow_data):
    result = parse.order(json.dumps(netflow_data("getpagedlist.json")))
    assert len(result) == 3
    assert result[0].model_dump() == {
        "time": "2026-05",
        "download_usage": 1616764475,
        "upload_usage": 169202003,
        "over_usage": 0.0,
        "should_pay": 0.0,
        "update_time": datetime(2026, 6, 1, 0, 56, 54),
    }
    assert json.loads(result[0].model_dump_json())["update_time"] == "2026-06-01T00:56:54"


@pytest.mark.parametrize(
    "download,upload,expected",
    [
        (None, None, (0, 0)),
        (12.9, 3.1, (12, 3)),
        (-1, -3.5, (0, 0)),
        (1e30, 0, (2**64 - 1, 0)),
    ],
)
def test_order_byte_conversion(netflow_data, download, upload, expected):
    data = netflow_data("getpagedlist.json")
    data["data"][0].update(Download=download, Upload=upload)
    result = parse.order(json.dumps(data))[0]
    assert (result.download_usage, result.upload_usage) == expected


def test_order_missing_usage(netflow_data):
    data = netflow_data("getpagedlist.json")
    data["data"][0].pop("Download", None)
    data["data"][0].pop("Upload", None)
    result = parse.order(json.dumps(data))[0]
    assert result.download_usage == result.upload_usage == 0


def test_overdue_payment(netflow_data):
    assert parse.overdue_payment(json.dumps(netflow_data("getpayinfo.json"))) == 0.0
    assert parse.overdue_payment('{"data":{"Total":12.5}}') == 12.5


def test_this_month_rust_fixture(netflow_data):
    result = parse.this_month_info(json.dumps(netflow_data("gettrafficinfobythismonth.json")))
    assert result.model_dump() == {
        "total_usage": "1.81GB",
        "upload_usage": "0.14GB",
        "download_usage": "1.67GB",
        "base_package_amount": 40.0,
        "base_package_usage": 1.67,
        "base_package_usage_percentage": 0.04,
        "base_package_surplus": 38.33,
        "extend_package_amount": 0.0,
        "extend_package_usage": 0.0,
        "extend_package_usage_percentage": 0.0,
        "extend_package_surplus": 20.0,
    }


def test_gb_suffix_not_duplicated(netflow_data):
    data = netflow_data("gettrafficinfobythismonth.json")
    data["data"].update(allTraffic="小于0.01GB", uploadTraffic="0.01GB", downloadTraffic="小于0.01")
    result = parse.this_month_info(json.dumps(data))
    assert result.total_usage == "小于0.01GB"
    assert result.upload_usage == "0.01GB"
    assert result.download_usage == "小于0.01GB"


def test_unlock_status_rust_fixture(netflow_data):
    assert (
        parse.unlock_status(json.dumps(netflow_data("getuserinfo.json"))) is UnlockStatus.Unlocked
    )


@pytest.mark.parametrize(
    "value,expected",
    [
        (0, UnlockStatus.Unlocked),
        (1, UnlockStatus.Locked),
        (2, UnlockStatus.Unknown),
        (-1, UnlockStatus.Unknown),
    ],
)
def test_unlock_status_values(value, expected):
    assert parse.unlock_status(json.dumps({"data": {"IsLocked": value}})) is expected


@pytest.mark.parametrize("value", [True, "1", None, 1.0, 2**63])
def test_invalid_unlock_status(value):
    with pytest.raises(NetflowParseError):
        parse.unlock_status(json.dumps({"data": {"IsLocked": value}}))


@pytest.mark.parametrize(
    "parser",
    [
        parse.detail,
        parse.order,
        parse.overdue_payment,
        parse.this_month_info,
        parse.unlock_status,
    ],
)
@pytest.mark.parametrize("body", ["<html>login</html>", "null", "[]", "{}", '{"data":null}'])
def test_malformed_response(parser, body):
    with pytest.raises(NetflowParseError):
        parser(body)


@pytest.mark.parametrize(
    "fixture,parser,path,value",
    [
        ("getfloatdetailbymonth.json", parse.detail, "AllTotal", "10"),
        ("getfloatdetailbymonth.json", parse.detail, "AllUpload", True),
        ("getfloatdetailbymonth.json", parse.detail, "FloatDetailList", [None]),
        ("gettrafficinfobythismonth.json", parse.this_month_info, "allTraffic", 1.81),
        (
            "gettrafficinfobythismonth.json",
            parse.this_month_info,
            "basePackageUsed",
            "1.67",
        ),
        ("getpayinfo.json", parse.overdue_payment, "Total", False),
        ("getpayinfo.json", parse.overdue_payment, "Total", float("inf")),
    ],
)
def test_strict_fields(netflow_data, fixture, parser, path, value):
    data = netflow_data(fixture)
    data["data"][path] = value
    with pytest.raises(NetflowParseError):
        parser(json.dumps(data))


def test_bad_order_date(netflow_data):
    data = netflow_data("getpagedlist.json")
    data["data"][0]["UpdateTime"] = "2026-02-30 00:00:00"
    with pytest.raises(NetflowParseError):
        parse.order(json.dumps(data))


def test_empty_lists(netflow_data):
    assert parse.order('{"data":[]}') == []
    data = netflow_data("getfloatdetailbymonth.json")
    data["data"]["FloatDetailList"] = []
    assert parse.detail(json.dumps(data)).items == []
