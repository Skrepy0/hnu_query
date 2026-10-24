import json

import pytest

from hnu_query.yjsxt import YjsxtParseError, parse


def cell(id="1001", teacher="教师甲", weeks="1-2", suffix="连续周", place="教学楼101"):
    return f"<br/>课程编号:{id}<br/>课程名称: 示例 课程 <br/>班级:示例 班<br/>上课时间:[{weeks}周] {suffix}<br/>{teacher}[{place}]"


def schedule_map(course):
    return {(s.week, s.day, s.place): s.time for s in course.schedule}


def test_semester_rust_fixture(yjsxt_text):
    result = parse.semester(yjsxt_text("bindterm.json"))
    assert len(result) == 56
    assert [item.model_dump() for item in result[:4]] == [
        {"xn": 2026, "xq": 1, "id": "63"},
        {"xn": 2025, "xq": 3, "id": "64"},
        {"xn": 2025, "xq": 4, "id": "62"},
        {"xn": 2025, "xq": 2, "id": "61"},
    ]
    assert result[-1].model_dump() == {"xn": 2004, "xq": 1, "id": "5"}


@pytest.mark.parametrize(
    "name", ["2026", "2026-2027未知学期", "65536-65537秋学期", "x-2027秋学期"]
)
def test_bad_semester_name(name):
    with pytest.raises(YjsxtParseError):
        parse.semester(json.dumps([{"termcode": "63", "termname": name}]))


def test_regular_class_table_rust_fixture(yjsxt_text):
    result = parse.class_table(yjsxt_text("py_kbcx_ew.json"))
    assert len(result) == 5
    by_id = {course.course_id: course for course in result}
    configurations = {
        "1001": (
            "教师甲",
            [(1, 8, 1, "教学楼101", [1, 2]), (1, 8, 3, "教学楼101", [3, 4])],
        ),
        "1002": ("教师乙", [(1, 16, 4, "教学楼102", [2, 3, 4])]),
        "1003": (
            "教师丙",
            [(9, 16, 5, "教学楼103", [3, 4]), (9, 16, 4, "教学楼103", [9, 10])],
        ),
        "1004": ("教师丁", [(1, 11, 5, "教学楼104", [5, 6, 7])]),
        "1005": (
            "教师戊",
            [(1, 8, 4, "教学楼105", [7, 8]), (1, 8, 1, "教学楼105", [9, 10])],
        ),
    }
    for id, (teacher, slots) in configurations.items():
        course = by_id[id]
        assert course.course_name == "示例课程" + id[-1]
        assert course.class_name == "示例班" and course.teacher == teacher
        expected = {
            (week, day, place): periods
            for start, end, day, place, periods in slots
            for week in range(start, end + 1)
        }
        assert schedule_map(course) == expected


def test_multi_phase_rust_fixture(yjsxt_text):
    result = parse.class_table(yjsxt_text("py_kbcx_ew_multi_phase.json"))
    assert len(result) == 12
    phases = sorted(
        (course for course in result if course.course_id == "1018"),
        key=lambda c: min(s.week for s in c.schedule),
    )
    assert len(phases) == 2
    assert [p.teacher for p in phases] == ["教师辛", "教师未"]
    assert schedule_map(phases[0]) == {
        (w, 5, "文科楼101"): [9, 10] for w in range(1, 5)
    }
    assert schedule_map(phases[1]) == {
        (w, 5, "文科楼101"): [9, 10] for w in range(5, 9)
    }


def test_odd_even_rust_fixture(yjsxt_text):
    result = {
        course.course_id: course
        for course in parse.class_table(yjsxt_text("py_kbcx_ew_dsz.json"))
    }
    assert len(result) == 2
    assert schedule_map(result["1006"]) == {
        (w, 2, "教学楼106"): [1, 2] for w in range(1, 16, 2)
    }
    assert schedule_map(result["1007"]) == {
        (w, 3, "教学楼107"): [1, 2] for w in range(2, 17, 2)
    }


def test_no_period_deduplicates_and_missing_teacher():
    result = parse.class_table(
        json.dumps(
            {
                "rows": [
                    {"mc": "无节次", "z1": cell(teacher="")},
                    {"mc": "无节次", "z2": cell(teacher="")},
                ]
            }
        )
    )
    assert len(result) == 1
    assert result[0].model_dump() == {
        "course_name": "示例课程",
        "course_id": "1001",
        "class_name": "示例班",
        "teacher": None,
        "schedule": None,
    }


def test_week_zero_single_week_and_distinct_places():
    result = parse.class_table(
        json.dumps(
            {
                "rows": [
                    {"mc": "2", "z7": cell(weeks="0", place="A")},
                    {"mc": "1", "z7": cell(weeks="0", place="A")},
                    {"mc": "3", "z7": cell(weeks="0", place="B")},
                ]
            }
        )
    )
    assert len(result) == 1
    assert schedule_map(result[0]) == {(0, 7, "A"): [1, 2], (0, 7, "B"): [3]}


def test_duplicate_periods_preserved_like_rust():
    row = {"mc": "1", "z1": cell(weeks="1")}
    result = parse.class_table(json.dumps({"rows": [row, row]}))
    assert result[0].schedule[0].time == [1, 1]


def test_reversed_week_range_matches_rust_empty_schedule():
    result = parse.class_table(
        json.dumps({"rows": [{"mc": "1", "z1": cell(weeks="5-1")}]})
    )
    assert result[0].schedule == []


@pytest.mark.parametrize(
    "value",
    [
        cell(suffix="三周"),
        cell(weeks="1-2-3"),
        cell(weeks="1,3"),
        cell(weeks="256"),
        cell().replace("班级:", "教学班:"),
        "备注:未知内容<br/>" + cell(),
        cell() + "<br/>未知行",
        cell().replace("[1-2周]", "[1-2周]连续周[3-4周]"),
        cell().replace("教师甲[教学楼101]", "教师甲"),
        "",
        "<br/>",
    ],
)
def test_unrecognized_course_content_errors(value):
    with pytest.raises(YjsxtParseError):
        parse.class_table(json.dumps({"rows": [{"mc": "1", "z1": value}]}))


@pytest.mark.parametrize(
    "mc,value", [(1, None), ("256", cell()), ("invalid", cell()), ("1", 123)]
)
def test_bad_row(mc, value):
    with pytest.raises(YjsxtParseError):
        parse.class_table(json.dumps({"rows": [{"mc": mc, "z1": value}]}))


@pytest.mark.parametrize("parser", [parse.semester, parse.class_table])
@pytest.mark.parametrize(
    "body", ["<html>login</html>", "null", "{}", '{"rows":[null]}']
)
def test_invalid_response(parser, body):
    with pytest.raises(YjsxtParseError):
        parser(body)


def test_empty_results():
    assert parse.semester("[]") == []
    assert parse.class_table('{"rows":[]}') == []
    assert parse.class_table('{"rows":[{"mc":"1"}]}') == []
