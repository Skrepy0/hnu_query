import json

import pytest

from hnu_query.xgxt import (
    Dormitory,
    Gender,
    Level,
    XgxtParseError,
    parse,
    parse_dormitory,
)


def test_person_info_rust_fixtures(xgxt_entries):
    result = parse.person_info(xgxt_entries)
    assert result.model_dump() == {
        "name": "林政和",
        "enter_year": 2025,
        "xz": 4,
        "stu_id": "202506050175",
        "gender": Gender.Male,
        "level": Level.Undergraduate,
        "academy": "0004",
        "major": "0605",
        "class": "2025060501",
        "dormitory": {
            "park": "天马园区",
            "build": "三区13栋",
            "room": "123",
            "raw_dormitory": "天马三区13栋",
        },
        "politic": "",
        "race": "01",
        "hometown": "430104",
        "phone": "13000000000",
        "wechat": "my_wechat",
        "qq": "123456",
        "email": "qnxg@example.com",
    }
    assert result.class_ == "2025060501"
    assert result.dormitory.successfully_parsed()
    assert json.loads(result.model_dump_json())["class"] == result.class_
    assert "class_" not in result.model_dump()


@pytest.mark.parametrize(
    "code,expected",
    [("1", Level.Doctoral), ("2", Level.Postgraduate), ("3", Level.Undergraduate)],
)
def test_level_mapping_and_missing_xz(xgxt_entries, code, expected):
    xgxt_entries["培养层次"] = code
    xgxt_entries.pop("学制(年)")
    result = parse.person_info(xgxt_entries)
    assert result.level is expected and result.xz is None


def test_optional_blank_vs_absent(xgxt_entries):
    xgxt_entries.update({"性别": "2", "学制(年)": "", "寝室号": ""})
    xgxt_entries.pop("电子邮箱")
    result = parse.person_info(xgxt_entries)
    assert result.gender is Gender.Female
    assert result.dormitory is result.xz is result.email is None
    assert result.politic == ""


@pytest.mark.parametrize(
    "key",
    [
        "姓名",
        "年级",
        "学号",
        "性别",
        "培养层次",
        "学院",
        "专业",
        "班级",
        "寝室楼",
        "寝室号",
    ],
)
def test_missing_required_field(xgxt_entries, key):
    del xgxt_entries[key]
    with pytest.raises(XgxtParseError):
        parse.person_info(xgxt_entries)


@pytest.mark.parametrize(
    "key,value",
    [
        ("性别", "0"),
        ("培养层次", "4"),
        ("年级", "65536"),
        ("年级", "2025.0"),
        ("学制(年)", "256"),
        ("学制(年)", "-1"),
    ],
)
def test_invalid_values(xgxt_entries, key, value):
    xgxt_entries[key] = value
    with pytest.raises(XgxtParseError):
        parse.person_info(xgxt_entries)


def test_extract_supported_values_and_first_group_only():
    body = {
        "data": {
            "groupFields": [
                {
                    "fields": [
                        {"fieldName": "a", "defaultValue": "first"},
                        {"fieldName": "a", "defaultValue": 2},
                        {"fieldName": "b", "defaultValue": True},
                        {"fieldName": "c", "defaultValue": 2.0},
                        {"fieldName": "d", "defaultValue": None},
                        {"fieldName": "e", "defaultValue": []},
                        {"fieldName": "f", "defaultValue": 2**63},
                        {"fieldName": 1, "defaultValue": "x"},
                        None,
                    ]
                },
                {"fields": [{"fieldName": "ignored", "defaultValue": "x"}]},
            ]
        }
    }
    assert parse.extract_xgxt_entry(json.dumps(body)) == {"a": "2"}


@pytest.mark.parametrize(
    "body",
    [
        "<html>login</html>",
        "null",
        "{}",
        '{"data":{"groupFields":[]}}',
        '{"data":{"groupFields":[{"fields":null}]}}',
    ],
)
def test_malformed_form(body):
    with pytest.raises(XgxtParseError):
        parse.extract_xgxt_entry(body)


@pytest.mark.parametrize(
    "raw,park,build",
    [
        ("财院校区北12舍", "财院校区", "12"),
        ("南校区南10舍", "南校区", "10舍"),
        ("牛头山学生公寓3栋", "牛头山学生公寓", "3栋"),
        ("老留学生公寓", None, None),
        ("天马三区13栋", "天马园区", "三区13栋"),
        ("德智园区10栋", "德智园区", "10栋"),
        ("望麓桥学生公寓2栋", "望麓桥学生公寓", "2栋"),
        ("财院校区北A栋", "财院校区", "A"),
        ("南校区南楼", "南校区", None),
        ("天马未知楼栋", "天马园区", None),
    ],
)
def test_dormitory_rust_rules(raw, park, build):
    result = parse_dormitory(raw, "315")
    assert (result.park, result.build, result.room, result.raw_dormitory) == (
        park,
        build,
        "315",
        raw,
    )
    assert result.successfully_parsed() == (park is not None and build is not None)


def test_manual_dormitory():
    result = Dormitory.from_parsed_value("南校区", "南楼", "101")
    assert result.successfully_parsed()
    assert result.raw_dormitory == "南校区南楼"
