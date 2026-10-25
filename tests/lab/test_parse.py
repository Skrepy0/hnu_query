import json
from datetime import datetime

import pytest

from hnu_query.lab import LabParseError, parse


def test_semester_rust_fixture(lab_data):
    semesters = parse.semester(json.dumps(lab_data("GetSemDropDownList.json")))
    assert len(semesters) == 12
    assert semesters[0].model_dump() == {"xn": 2020, "xq": 3, "id": "5"}
    assert semesters[-1].model_dump() == {"xn": 2025, "xq": 2, "id": "18"}
    assert parse.semester('[{"id":"x","text":"2025 2026 1"}]')[0].xn == 2025


@pytest.mark.parametrize(
    "text", ["2025-1", "wrong", "2025-2026-256", "65536-65537-1", "2025--2026-1"]
)
def test_invalid_semester(text):
    with pytest.raises(LabParseError):
        parse.semester(json.dumps([{"id": "x", "text": text}]))


def test_course_rust_fixture(lab_data):
    data = lab_data("GetStudentScoreList.json")
    courses = parse.course_list(json.dumps(data))
    assert [c.model_dump() for c in courses] == [
        {"name": "普通物理实验AⅠ", "score": "83.8", "id": "68"}
    ]
    data["rows"][0]["CourseFinalScore"] = ""
    assert parse.course_list(json.dumps(data))[0].score is None


def test_schedule_rust_fixture(lab_data):
    data = lab_data("LoadTableInfo.json")
    schedules = parse.lab_schedule(json.dumps(data))
    assert len(schedules) == 2
    assert schedules[0].model_dump() == {
        "seat": "3",
        "name": "绪论",
        "course": "普通物理实验AⅠ",
        "teacher": "老师姓名",
        "week": 2,
        "day": 3,
        "date_time": datetime(2026, 3, 11, 19),
        "place": "研究生楼A栋111",
        "phone": "18888888888",
        "email": "qnxg@hnu.edu.cn",
    }
    data["rows"][0].update(MobileNum="", Email="", WeekName="星期日")
    first = parse.lab_schedule(json.dumps(data))[0]
    assert first.day == 7
    assert first.phone is first.email is None
    assert json.loads(first.model_dump_json())["date_time"] == "2026-03-11T19:00:00"


@pytest.mark.parametrize(
    "key,value",
    [
        ("Weeks", "256"),
        ("Weeks", "-1"),
        ("WeekName", "星期八"),
        ("StartTime", "25:00"),
        ("ClassDate", "2026/2/30 0:00:00"),
        ("MobileNum", None),
    ],
)
def test_invalid_schedule(lab_data, key, value):
    data = lab_data("LoadTableInfo.json")
    data["rows"][0][key] = value
    with pytest.raises(LabParseError):
        parse.lab_schedule(json.dumps(data))


def grade_inputs(lab_data):
    return (
        lab_data("GetStudentLabScore.json"),
        lab_data("ShowScore.json"),
        lab_data("GetLabScoreStructure.json"),
    )


def test_lab_grade_rust_fixture(lab_data):
    grades = parse.lab_grade(*(json.dumps(d) for d in grade_inputs(lab_data)))
    assert [(g.lab_name, g.score, g.attendance) for g in grades] == [
        ("绪论", "84.4", "正常"),
        ("物体密度测量", "87.5", "正常"),
        ("冷却法测量金属的比热容", "84", "正常"),
    ]
    assert [(d.name, d.score) for d in grades[0].details] == [
        ("预习", 100),
        ("纪律", 100),
        ("操作", 100),
        ("报告", 44),
    ]
    assert [(d.name, d.score) for d in grades[1].details] == [
        ("预习", 75),
        ("纪律", 100),
        ("操作", 80),
        ("报告", 75),
    ]
    assert grades[2].details == []


def test_grade_filters_and_unmatched_details(lab_data):
    grades, details, structures = grade_inputs(lab_data)
    grades["rows"][1]["LabScore"] = ""
    grades["rows"][2]["ClassRoom"] = "虚拟实验室"
    grades["rows"][0]["AttendanceName"] = ""
    details["Data"]["Lablist"][0]["LabStructureScore"] = None
    details["Data"]["Lablist"][1]["LabScoreStructureID"] = 9999
    details["Data"]["Lablist"][2]["LabID"] = 9999
    result = parse.lab_grade(*(json.dumps(d) for d in (grades, details, structures)))
    assert len(result) == 1
    assert result[0].attendance is None
    assert [(d.name, d.score) for d in result[0].details] == [("报告", 44)]


@pytest.mark.parametrize(
    "target,key,value",
    [
        ("grade", "LabID", "bad"),
        ("grade", "LabID", "2147483648"),
        ("detail", "LabID", "415"),
        ("detail", "LabStructureScore", "100"),
        ("detail", "LabStructureScore", True),
        ("structure", "LabScoreStructureID", False),
    ],
)
def test_invalid_grade_fields(lab_data, target, key, value):
    grades, details, structures = grade_inputs(lab_data)
    row = {
        "grade": grades["rows"][0],
        "detail": details["Data"]["Lablist"][0],
        "structure": structures["Data"][0],
    }[target]
    row[key] = value
    with pytest.raises(LabParseError):
        parse.lab_grade(*(json.dumps(d) for d in (grades, details, structures)))


def test_virtual_grade_sort_dedup_first_wins():
    result = parse.virtual_lab_grade(
        json.dumps(
            {
                "rows": [
                    {"LabName": "B", "LabScore": ""},
                    {"LabName": "A", "LabScore": "90"},
                    {"LabName": "B", "LabScore": "100"},
                    {"LabName": "A", "LabScore": "80"},
                ]
            }
        )
    )
    assert [r.model_dump() for r in result] == [
        {"lab_name": "A", "score": "90"},
        {"lab_name": "B", "score": None},
    ]


@pytest.mark.parametrize("parser", [parse.course_list, parse.lab_schedule, parse.virtual_lab_grade])
@pytest.mark.parametrize("body", ["<html>login</html>", "null", "[]", "{}", '{"rows":[null]}'])
def test_malformed_rows(parser, body):
    with pytest.raises(LabParseError):
        parser(body)


def test_empty_results():
    assert parse.semester("[]") == []
    assert parse.course_list('{"rows":[]}') == []
    assert parse.lab_schedule('{"rows":[]}') == []
    assert parse.virtual_lab_grade('{"rows":[]}') == []
    assert parse.lab_grade('{"rows":[]}', '{"Data":{"Lablist":[]}}', '{"Data":[]}') == []
