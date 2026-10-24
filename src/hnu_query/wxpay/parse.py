import json

from hnu_query.xgxt.dormitory import Dormitory

from .exceptions import WxpayParseError

PARK_IDS = {
    "南校区": 1,
    "财院校区": 2,
    "天马园区": 3,
    "德智园区": 4,
    "德智留学生公寓": 5,
    "望麓桥学生公寓": 6,
    "牛头山学生公寓": 7,
}

BUILDING_IDS = {
    1: {
        "7舍": "19-1",
        "8舍": "20",
        "10舍": "21",
        "11舍": "21-0",
        "12舍": "21-1",
        "13舍": "21-2",
        "14舍": "22",
        "15舍": "23",
        "17舍": "24",
        "18舍": "25",
        "南楼": "26",
        "培训小楼": "27",
    },
    2: {
        "1": "01",
        "2": "02",
        "3": "02-01",
        "5": "03",
        "6": "04",
        "12": "05",
        "A": "06",
        "B": "07",
        "7": "08",
    },
    3: {
        "一区1栋": "28",
        "一区2栋": "29",
        "一区3栋": "30",
        "一区4栋": "30-1",
        "二区1栋": "31",
        "二区2栋": "32",
        "二区3栋": "33",
        "二区4栋": "34",
        "二区5栋": "35",
        "二区6栋": "36",
        "二区7栋": "37",
        "三区9栋": "38",
        "三区10栋": "39",
        "三区11栋": "40",
        "三区12栋": "41",
        "三区13栋": "42",
        "三区16栋": "43",
        "三区17栋": "44",
        "三区18栋": "45",
        "三区19栋": "46",
        "三区20栋": "46-1",
        "四区1栋": "47",
        "四区2栋": "48",
        "四区3栋": "49",
        "四区4栋": "50",
    },
    4: {
        "2栋": "09",
        "5栋": "10",
        "6栋": "11",
        "7栋": "12",
        "8栋": "13",
        "9栋": "14",
        "10栋": "15",
        "11栋": "16",
        "13栋": "17",
        "15栋": "17-01",
        "16栋": "17-02",
    },
    6: {"1栋": "51", "2栋": "#2栋", "3栋": "#3栋", "4栋": "57"},
    7: {"2栋": "60", "3栋": "61", "4栋": "62", "5栋": "63", "6栋": "64", "7栋": "65"},
}


def convert_dormitory(dormitory: Dormitory) -> tuple[int, str, str]:
    if not isinstance(dormitory, Dormitory) or not dormitory.successfully_parsed():
        raise ValueError("dormitory 必须成功解析出园区和楼栋")
    park = PARK_IDS.get(dormitory.park)
    if park is None:
        raise WxpayParseError("未知宿舍园区")
    build, room = dormitory.build, dormitory.room
    if park == 1 and build == "19舍":
        if not room or room[0] not in "1234":
            raise WxpayParseError("南校区 19 舍房间号前缀应为 1–4")
        build_id = "25-" + room[0]
        parts = room.split("-")
        if len(parts) != 2:
            raise WxpayParseError("南校区 19 舍房间号应为 分区-房间号")
        room_id = (
            "F" + parts[1].replace("附", "") if parts[1].startswith("附") else parts[1]
        )
        return park, build_id, room_id
    if park == 5:
        build_id = "18"
    else:
        build_id = BUILDING_IDS.get(park, {}).get(build)
        if build_id is None:
            raise WxpayParseError("未知宿舍楼栋")
    if park == 4 and build in {
        "2栋",
        "5栋",
        "6栋",
        "7栋",
        "8栋",
        "9栋",
        "10栋",
        "11栋",
    }:
        room = build.removesuffix("栋") + room
    return park, build_id, room


def electricity(body: str) -> str:
    try:
        value = json.loads(body)["data"]["Balance"]
        if not isinstance(value, str):
            raise TypeError("Balance 应为字符串")
        return value
    except (ValueError, TypeError, KeyError) as exc:
        raise WxpayParseError("无法解析宿舍电量 Balance 字段") from exc
