from pathlib import Path

import pytest

from hnu_query.wxpay import WxpayParseError
from hnu_query.wxpay.parse import convert_dormitory, electricity
from hnu_query.xgxt import Dormitory, parse_dormitory


@pytest.mark.parametrize(
    "park,build,expected",
    [
        ("南校区", "7舍", "19-1"),
        ("南校区", "8舍", "20"),
        ("南校区", "10舍", "21"),
        ("南校区", "11舍", "21-0"),
        ("南校区", "12舍", "21-1"),
        ("南校区", "13舍", "21-2"),
        ("南校区", "14舍", "22"),
        ("南校区", "15舍", "23"),
        ("南校区", "17舍", "24"),
        ("南校区", "18舍", "25"),
        ("南校区", "南楼", "26"),
        ("南校区", "培训小楼", "27"),
        ("财院校区", "1", "01"),
        ("财院校区", "2", "02"),
        ("财院校区", "3", "02-01"),
        ("财院校区", "5", "03"),
        ("财院校区", "6", "04"),
        ("财院校区", "12", "05"),
        ("财院校区", "A", "06"),
        ("财院校区", "B", "07"),
        ("财院校区", "7", "08"),
        ("天马园区", "一区1栋", "28"),
        ("天马园区", "一区2栋", "29"),
        ("天马园区", "一区3栋", "30"),
        ("天马园区", "一区4栋", "30-1"),
        ("天马园区", "二区1栋", "31"),
        ("天马园区", "二区2栋", "32"),
        ("天马园区", "二区3栋", "33"),
        ("天马园区", "二区4栋", "34"),
        ("天马园区", "二区5栋", "35"),
        ("天马园区", "二区6栋", "36"),
        ("天马园区", "二区7栋", "37"),
        ("天马园区", "三区9栋", "38"),
        ("天马园区", "三区10栋", "39"),
        ("天马园区", "三区11栋", "40"),
        ("天马园区", "三区12栋", "41"),
        ("天马园区", "三区13栋", "42"),
        ("天马园区", "三区16栋", "43"),
        ("天马园区", "三区17栋", "44"),
        ("天马园区", "三区18栋", "45"),
        ("天马园区", "三区19栋", "46"),
        ("天马园区", "三区20栋", "46-1"),
        ("天马园区", "四区1栋", "47"),
        ("天马园区", "四区2栋", "48"),
        ("天马园区", "四区3栋", "49"),
        ("天马园区", "四区4栋", "50"),
        ("德智园区", "2栋", "09"),
        ("德智园区", "5栋", "10"),
        ("德智园区", "6栋", "11"),
        ("德智园区", "7栋", "12"),
        ("德智园区", "8栋", "13"),
        ("德智园区", "9栋", "14"),
        ("德智园区", "10栋", "15"),
        ("德智园区", "11栋", "16"),
        ("德智园区", "13栋", "17"),
        ("德智园区", "15栋", "17-01"),
        ("德智园区", "16栋", "17-02"),
        ("德智留学生公寓", "已确认楼栋", "18"),
        ("望麓桥学生公寓", "1栋", "51"),
        ("望麓桥学生公寓", "2栋", "#2栋"),
        ("望麓桥学生公寓", "3栋", "#3栋"),
        ("望麓桥学生公寓", "4栋", "57"),
        ("牛头山学生公寓", "2栋", "60"),
        ("牛头山学生公寓", "3栋", "61"),
        ("牛头山学生公寓", "4栋", "62"),
        ("牛头山学生公寓", "5栋", "63"),
        ("牛头山学生公寓", "6栋", "64"),
        ("牛头山学生公寓", "7栋", "65"),
    ],
)
def test_rust_building_codes(park, build, expected):
    park_id, building_id, room = convert_dormitory(Dormitory.from_parsed_value(park, build, "101"))
    assert building_id == expected
    assert (
        park_id
        == {
            "南校区": 1,
            "财院校区": 2,
            "天马园区": 3,
            "德智园区": 4,
            "德智留学生公寓": 5,
            "望麓桥学生公寓": 6,
            "牛头山学生公寓": 7,
        }[park]
    )
    assert room == (
        build[:-1] + "101"
        if park == "德智园区"
        and build in {"2栋", "5栋", "6栋", "7栋", "8栋", "9栋", "10栋", "11栋"}
        else "101"
    )


@pytest.mark.parametrize(
    "room,building,converted",
    [
        ("1-附204", "25-1", "F204"),
        ("2-320", "25-2", "320"),
        ("3-101", "25-3", "101"),
        ("4-附101", "25-4", "F101"),
    ],
)
def test_south_19_special_room(room, building, converted):
    assert convert_dormitory(Dormitory.from_parsed_value("南校区", "19舍", room)) == (
        1,
        building,
        converted,
    )


@pytest.mark.parametrize("room", ["", "5-101", "101", "1-2-101"])
def test_bad_south_19_room(room):
    with pytest.raises(WxpayParseError):
        convert_dormitory(Dormitory.from_parsed_value("南校区", "19舍", room))


def test_unparsed_and_unknown_dormitories():
    with pytest.raises(ValueError):
        convert_dormitory(parse_dormitory("老留学生公寓", "101"))
    with pytest.raises(WxpayParseError):
        convert_dormitory(Dormitory.from_parsed_value("未知校区", "1栋", "101"))
    with pytest.raises(WxpayParseError):
        convert_dormitory(Dormitory.from_parsed_value("天马园区", "一区99栋", "101"))


def test_rust_electricity_fixture():
    body = (Path(__file__).parent / "fixtures/checkRoomNo.json").read_text(encoding="utf-8")
    assert electricity(body) == "283.75度"
    assert electricity('{"data":{"Balance":"12.34元"}}') == "12.34元"


@pytest.mark.parametrize(
    "body",
    ["<html>error</html>", "null", "{}", '{"data":{"Balance":12}}', '{"data":null}'],
)
def test_invalid_response(body):
    with pytest.raises(WxpayParseError):
        electricity(body)
