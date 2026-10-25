import json
from datetime import date

import pytest

from hnu_query.gym import GradeItemColor, GymParseError, TokenExpired, parse


def test_grade_rust_fixture(gym_data):
    result = parse.grade(
        json.dumps(gym_data("getStudentScore.json")),
        json.dumps(gym_data("getEyeDetails.json")),
    )
    assert (result.name, result.stu_id, result.grade, result.score) == (
        "林政和",
        "202506050175",
        "不及格",
        56.2,
    )
    assert (result.report_desc, result.report_status, result.report_type) == (
        "暂无",
        "部分体测值异常",
        "正常",
    )
    assert result.eye.model_dump() == {
        "eyesight_right": "--",
        "eyesight_left": "--",
        "eyesight_right_detail": "未测",
        "eyesight_left_detail": "未测",
        "eye_mirror_right": "9",
        "eye_mirror_left": "9",
        "eye_mirror_right_detail": "未测",
        "eye_mirror_left_detail": "未测",
        "eye_ametropia_right": "9",
        "eye_ametropia_left": "9",
        "eye_ametropia_right_detail": "未测",
        "eye_ametropia_left_detail": "未测",
    }
    expected = {
        "short_run": ("Red", "不及格", "9.3秒", 50),
        "bmi": ("Red", "超重", "178.6厘米/76.5千克", 80),
        "jump": ("Red", "不及格", "205.0厘米", 50),
        "pull_and_sit": ("Red", "不及格", "0次", 0),
        "run": ("Red", "不及格", "4'33''", 50),
        "sit_and_reach": ("Green", "及格", "12.5厘米", 72),
        "vc": ("Green", "良好", "4460毫升", 80),
    }
    for key, values in expected.items():
        item = getattr(result, key)
        assert (item.color.value, item.rank, item.grade, item.score) == values
    assert json.loads(result.model_dump_json())["short_run"]["color"] == "Red"


def test_grade_fallbacks_and_bonus(gym_data):
    summary, detail = gym_data("getStudentScore.json"), gym_data("getEyeDetails.json")
    for key in list(summary["data"]):
        if key.endswith(("_score", "_class")) or key.startswith("report_"):
            summary["data"][key] = None
    detail["data"].update(run="273", extra_score_run=5, extra_score_pull_or_sit_up=3)
    grade = parse.grade(json.dumps(summary), json.dumps(detail))
    assert grade.run.grade == "4'33\""
    assert grade.run.score == 55
    assert grade.pull_and_sit.score == 3
    assert grade.short_run.grade == "9.3秒"
    assert grade.bmi.grade == "178.6厘米/76.5千克"
    assert grade.jump.grade == "205.0厘米"
    assert grade.pull_and_sit.grade == "0次"
    assert grade.sit_and_reach.grade == "12.5厘米"
    assert grade.vc.grade == "4460毫升"
    assert grade.bmi.color is GradeItemColor.Red
    assert grade.vc.color is GradeItemColor.Green
    assert grade.report_status == "暂无"


@pytest.mark.parametrize("value", [0, 10.5, True, {}, []])
def test_summary_non_string_becomes_zero(gym_data, value):
    summary = gym_data("getStudentScore.json")
    summary["data"]["50m_score"] = value
    grade = parse.grade(json.dumps(summary), json.dumps(gym_data("getEyeDetails.json")))
    assert grade.short_run.grade == "0"


@pytest.mark.parametrize(
    "value,expected",
    [("240", "4'"), ("273.0", "0'"), ("bad", "0'"), ("4294967296", "0'")],
)
def test_rust_run_time_fallback(gym_data, value, expected):
    summary, detail = gym_data("getStudentScore.json"), gym_data("getEyeDetails.json")
    summary["data"]["run_score"] = None
    detail["data"]["run"] = value
    assert parse.grade(json.dumps(summary), json.dumps(detail)).run.grade == expected


def test_explicit_class_overrides_rank(gym_data):
    summary = gym_data("getStudentScore.json")
    summary["data"]["50m_class"] = "green"
    assert (
        parse.grade(json.dumps(summary), json.dumps(gym_data("getEyeDetails.json"))).short_run.color
        is GradeItemColor.Green
    )


@pytest.mark.parametrize(
    "section,key,value",
    [
        ("summary", "50m_class", 1),
        ("summary", "report_desc", []),
        ("detail", "50m_score", True),
        ("detail", "jump", None),
        ("detail", "eyesight_right", 1),
        ("detail", "total_score", "56.2"),
    ],
)
def test_invalid_grade_fields(gym_data, section, key, value):
    summary, detail = gym_data("getStudentScore.json"), gym_data("getEyeDetails.json")
    (summary if section == "summary" else detail)["data"][key] = value
    with pytest.raises(GymParseError):
        parse.grade(json.dumps(summary), json.dumps(detail))


def test_missing_summary_score(gym_data):
    summary = gym_data("getStudentScore.json")
    del summary["data"]["run_score"]
    with pytest.raises(GymParseError):
        parse.grade(json.dumps(summary), json.dumps(gym_data("getEyeDetails.json")))


def test_appointments(appointments):
    rows = parse.appointment_list(json.dumps(appointments))
    item = parse.appointment_item(
        rows[0],
        '{"info":"成功","status":1,"data":{"class_desc":"请准时到场","appo_type":8}}',
    )
    assert item.model_dump() == {
        "name": "体测预约",
        "desc": "请准时到场",
        "show_date": "2025年12月15号（周一）",
        "date": date(2025, 12, 15),
        "time": "10:00 - 11:30",
        "test_type": 8,
        "status": 1,
    }
    assert parse.appointment_list('{"info":"成功","status":1,"data":[]}') == []


@pytest.mark.parametrize("key,value", [("class_id", "42"), ("class_id", -1), ("class_name", None)])
def test_invalid_appointments(appointments, key, value):
    appointments["data"][0][key] = value
    with pytest.raises(GymParseError):
        parse.appointment_list(json.dumps(appointments))


def test_invalid_appointment_date(appointments):
    appointments["data"][0]["class_time"] = "2025-02-30"
    rows = parse.appointment_list(json.dumps(appointments))
    with pytest.raises(GymParseError):
        parse.appointment_item(rows[0], '{"info":"成功","status":1,"data":{}}')


@pytest.mark.parametrize(
    "body",
    [
        "<html>login</html>",
        "null",
        "[]",
        "{}",
        '{"info":"成功","status":true,"data":[]}',
        '{"info":"失败","status":0,"data":[]}',
        '{"info":"成功","status":1}',
    ],
)
def test_bad_response(body):
    with pytest.raises(GymParseError):
        parse.gym_response(body)


def test_expired_response():
    with pytest.raises(TokenExpired):
        parse.gym_response('{"info":"登录失效，请重新登录","status":-1,"data":[]}')
