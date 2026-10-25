import json
from datetime import date

import pytest

from hnu_query.hdjw import HdjwParseError, TokenExpired, parse


def test_class_table_mixed(fixture_text):
    text = fixture_text("xskb_list_mixed.json")
    courses = parse.class_table(text)
    assert len(courses) == 8
    by_name = {c.course_name: c for c in courses}
    first = by_name["形势与政策(5)"]
    assert first.course_id == "GE01159"
    assert first.credit == 0.25
    assert first.people == 69
    assert first.teacher == "教师1"
    assert first.class_name == "人工智能2301-02"
    assert {s.week for s in first.schedule} == {9, 10}
    assert all((s.day, s.place, s.time) == (1, "复403", [7, 8]) for s in first.schedule)
    algorithms = by_name["数据结构与算法"]
    assert len(algorithms.schedule) == 23
    assert {s.week for s in algorithms.schedule if s.day == 4} == set(range(1, 16, 2))
    assert {s.week for s in algorithms.schedule if s.day == 1} == {1, 2, *range(4, 17)}
    physics = by_name["普通物理A（1）"]
    assert physics.extra == "普通物理同一课堂"
    assert len(physics.schedule) == 5
    assert all(s.time == [2, 3, 4] and s.day == 6 for s in physics.schedule)
    assert {s.place for s in physics.schedule if s.week == 12} == {"东111"}
    extras = parse.class_table_extra(text)
    assert len(extras) == 2
    assert extras[0].course_name == "创新创业"
    assert extras[1].teacher == "教师4,教师5"


def test_week_zero_and_merged_periods(fixture_text):
    text = fixture_text("xskb_list_week0.json")
    courses = parse.class_table(text)
    assert len(courses) == 12
    by_name = {c.course_name: c for c in courses}
    drafting = by_name["机械制图A"]
    assert len(drafting.schedule) == 28
    assert {s.week for s in drafting.schedule if s.day == 1} == {0, 1, 2, *range(6, 17)}
    practice = by_name["电工电子训练A"]
    assert len(practice.schedule) == 8
    assert all(s.time == list(range(1, 9)) for s in practice.schedule)
    sunday = [s for s in by_name["机械工程导论"].schedule if s.day == 7]
    assert len(sunday) == 8
    assert all(s.place == "无" for s in sunday)
    assert len(parse.class_table_extra(text)) == 1


def test_no_schedule_and_no_teacher(fixture_text):
    text = fixture_text("xskb_list_all_no_schedule.json")
    assert parse.class_table(text) == []
    assert len(parse.class_table_extra(text)) == 4
    data = json.loads(text)
    data["data"][0].pop("jg0101mc", None)
    assert parse.class_table_extra(json.dumps(data))[0].teacher == ""
    assert parse.class_table('{"count":0}') == []
    assert parse.class_table_extra('{"count":0}') == []


@pytest.mark.parametrize(
    "suffix,weeks",
    [
        ("(单周)", [1, 3, 5]),
        ("(双周)", [0, 2, 4, 6]),
        ("", list(range(7))),
    ],
)
def test_week_parity(suffix, weeks):
    result = parse.course_schedule(f"星期七1-2、2节{{ 0-6周}}{suffix}", "复309")
    assert [s.week for s in result] == weeks
    assert all(s.day == 7 and s.time == [1, 2] for s in result)


def test_same_day_different_places():
    result = parse.course_schedule("星期一1节{1周};星期一2节{1周}", "A;B")
    assert [(s.place, s.time) for s in result] == [("A", [1]), ("B", [2])]


@pytest.mark.parametrize(
    "time,place",
    [
        ("星期一1节{1周}(前三周)", "A"),
        ("星期八1节{1周}", "A"),
        ("星期一3-1节{1周}", "A"),
        ("星期一1节{1周}", None),
        ("星期一1节{1周};星期二2节{2周}", "A"),
        ("garbage", "A"),
    ],
)
def test_bad_schedule(time, place):
    with pytest.raises(HdjwParseError):
        parse.course_schedule(time, place)


def test_grade(fixture_text):
    grades = parse.grade(fixture_text("cjcx_list.json"))
    assert len(grades) == 4
    assert grades[0].model_dump() == {
        "course_id": "TB001XK24B",
        "course_name": "计算与人工智能概论B",
        "credit": 4.0,
        "course_type1": "必修",
        "course_type2": "通识必修",
        "gpa": 4.0,
        "score": 92.0,
        "grade_tag": None,
        "grade_type": "主修",
        "jx0404id": "TB001XK24B-155",
    }


def test_grade_optional_fields(fixture_text):
    data = json.loads(fixture_text("cjcx_list.json"))
    for key in ("kcsx", "jd", "cjbs", "jx0404id"):
        data["data"][0].pop(key, None)
    grade = parse.grade(json.dumps(data))[0]
    assert grade.course_type1 is grade.gpa is grade.grade_tag is grade.jx0404id is None


def test_grade_detail(fixture_text):
    result = parse.grade_detail(fixture_text("pscj_list.html"))
    assert {r.name: (r.score, r.percentage) for r in result} == {
        "平时成绩1": ("99.83", "30%"),
        "平时成绩2": ("67.5", "20%"),
        "期中成绩": ("98", "10%"),
        "期末成绩": ("98", "40%"),
    }
    text = fixture_text("pscj_list.html").replace('"20%"', '"0%"')
    assert len(parse.grade_detail(text)) == 3


def test_exam_schedule(fixture_text):
    exams = parse.exam_schedule(fixture_text("xsksap_list.json"))
    assert len(exams) == 6
    assert exams[0].model_dump() == {
        "course_id": "TB006MY24",
        "course_name": "思想道德与法治",
        "date": date(2026, 6, 23),
        "time": "15:00~17:00",
        "area": "南校区(天马)",
        "classroom": "综301",
        "seat": "1",
    }
    minimal = parse.exam_schedule('{"data":[{"kch":"a","kskcmc":"体育理论"}]}')[0]
    assert minimal.date is minimal.time is minimal.classroom is minimal.seat is None


def test_rank(fixture_text):
    result = parse.rank(fixture_text("cjpmcx_list.json"))
    assert result.core.arithmetic == "85"
    assert result.core.gpa == "3.01"
    assert result.must.weighted_rank == "38/90"
    assert result.all.gpa_rank == "42/90"
    assert parse.rank('{"data":{}}').model_dump() == {
        "all": None,
        "must": None,
        "core": None,
    }
    data = json.loads(fixture_text("cjpmcx_list.json"))
    data["data"]["allPm"]["avgzcj"] = "3.0"
    assert parse.rank(json.dumps(data)).all.arithmetic == "3.0"


def test_empty_classroom(fixture_text):
    rooms = parse.empty_classroom(fixture_text("jsjy_query2.json"), [1, 2, 3, 4, 5])
    assert [r.room_name for r in rooms] == ["综B103", "综B104", "综B105", "综B109"]
    assert rooms[0].model_dump() == {
        "room_name": "综B103",
        "room_type": "计算机房",
        "seat_count": 70,
        "exam_seat_count": 51,
    }
    # 响应只含选中的大节列：选第 5 大节也要从第 1 列开始检查。
    assert len(parse.empty_classroom('[0,0,0,0,[["A",null,"","(10/5)","教室"]]]', [5])) == 1


PARSERS = [
    parse.class_table,
    parse.class_table_extra,
    parse.grade,
    parse.grade_detail,
    parse.exam_schedule,
    parse.rank,
    lambda text: parse.empty_classroom(text, [1]),
]


@pytest.mark.parametrize("parser", PARSERS)
def test_expired_session(parser):
    with pytest.raises(TokenExpired):
        parser('{"flag1":2,"msgContent":"乱码"}')


@pytest.mark.parametrize("parser", PARSERS)
@pytest.mark.parametrize("body", ["<html>login</html>", "null", "{}", '{"data": [null]}'])
def test_malformed_response(parser, body):
    with pytest.raises(HdjwParseError):
        parser(body)
