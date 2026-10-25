"""与 Rust gym 对齐的纯解析函数。"""

import json
import re
from datetime import date

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .exceptions import GymParseError, TokenExpired
from .models import Appointment, EyeGrade, Grade, GradeItem, GradeItemColor


def gym_response(body: str):
    try:
        value = json.loads(body)
    except ValueError as exc:
        raise GymParseError("体测响应不是有效 JSON") from exc
    if not isinstance(value, dict) or not isinstance(value.get("info"), str):
        raise GymParseError("无法解析体测响应 info 字段")
    if "登录失效" in value["info"]:
        raise TokenExpired("体测会话已失效")
    if type(value.get("status")) is not int or value["status"] != 1:
        raise GymParseError("体测响应状态错误")
    if "data" not in value:
        raise GymParseError("体测响应缺少 data 字段")
    return value["data"]


class RawAppointment(BaseModel):
    model_config = ConfigDict(strict=True)

    class_id: int = Field(ge=0, le=2**32 - 1)
    button_status: int
    class_name: str
    class_time: str
    show_time: str
    test_time: str


def appointment_list(body: str) -> list[RawAppointment]:
    rows = gym_response(body)
    if not isinstance(rows, list):
        raise GymParseError("体测预约 data 应为列表")
    try:
        return [RawAppointment.model_validate(row) for row in rows]
    except ValidationError as exc:
        raise GymParseError("无法解析体测预约列表") from exc


def _field(data: dict, key: str, kind: type):
    value = data.get(key)
    # bool 在 Python 中是 int 的子类，但不是有效的服务端数值。
    valid = type(value) in (int, float) if kind is float else type(value) is kind
    if not valid:
        raise GymParseError(f"体测字段 {key} 类型不正确或缺失")
    return value


def appointment_item(raw_item: RawAppointment, detail_str: str) -> Appointment:
    detail = gym_response(detail_str)
    if not isinstance(detail, dict):
        raise GymParseError("体测预约详情 data 应为对象")
    try:
        day = date.fromisoformat(raw_item.class_time)
    except ValueError as exc:
        raise GymParseError("体测预约日期不正确") from exc
    return Appointment(
        name=raw_item.class_name,
        desc=_field(detail, "class_desc", str),
        show_date=raw_item.show_time,
        date=day,
        time=raw_item.test_time,
        test_type=_field(detail, "appo_type", int),
        status=raw_item.button_status,
    )


def _run_time(value: str) -> str:
    # Rust 使用 u32::parse，非整数秒字符串按 0 处理。
    seconds = int(value) if re.fullmatch(r"\+?[0-9]+", value) else 0
    if seconds > 2**32 - 1:
        seconds = 0
    minutes, seconds = divmod(seconds, 60)
    return f"{minutes}'{seconds}\"" if seconds else f"{minutes}'"


def grade(summary_str: str, detail_str: str) -> Grade:
    summary, detail = gym_response(summary_str), gym_response(detail_str)
    if not isinstance(summary, dict) or not isinstance(detail, dict):
        raise GymParseError("体测成绩 data 应为对象")
    # 即使摘要已有显示值，详情仍必须满足 Rust RawGradeDetail 的必填字段约定。
    for key in (
        "student_name",
        "student_num",
        "total_grade",
        "bmi_grade",
        "jump",
        "jump_grade",
        "pull_and_sit_grade",
        "50m",
        "50m_grade",
        "run",
        "run_grade",
        "sit_and_reach",
        "sit_and_reach_grade",
        "vc_grade",
        "height",
        "weight",
    ):
        _field(detail, key, str)
    for key in (
        "bmi_score",
        "vc_score",
        "jump_score",
        "sit_and_reach_score",
        "pull_and_sit_score",
        "50m_score",
        "run_score",
        "extra_score_pull_or_sit_up",
        "extra_score_run",
        "pull_and_sit",
        "vc",
    ):
        _field(detail, key, int)
    eye = EyeGrade(**{key: _field(detail, key, str) for key in EyeGrade.model_fields})
    items = {}
    for target, source in (
        ("short_run", "50m"),
        ("bmi", "bmi"),
        ("jump", "jump"),
        ("pull_and_sit", "pull_and_sit"),
        ("run", "run"),
        ("sit_and_reach", "sit_and_reach"),
        ("vc", "vc"),
    ):
        rank = _field(detail, source + "_grade", str)
        score = _field(detail, source + "_score", int)
        if source == "pull_and_sit":
            score += _field(detail, "extra_score_pull_or_sit_up", int)
        elif source == "run":
            score += _field(detail, "extra_score_run", int)
        color = summary.get(source + "_class")
        if color is not None and not isinstance(color, str):
            raise GymParseError("体测等级颜色应为字符串或 null")
        red = color == "red" if color is not None else rank in ("不及格", "缺项", "肥胖", "超重")
        key = source + "_score"
        if key not in summary:
            raise GymParseError(f"体测摘要缺少 {key}")
        measured = summary[key]
        if measured is not None and not isinstance(measured, str):
            # Rust none_to_zero 的实际行为：非字符串值变为字符串 "0"。
            measured = "0"
        if measured is None:
            if source == "bmi":
                measured = (
                    f"{_field(detail, 'height', str)}厘米/{_field(detail, 'weight', str)}千克"
                )
            elif source == "run":
                measured = _run_time(_field(detail, "run", str))
            else:
                kind = int if source in ("pull_and_sit", "vc") else str
                unit = {
                    "50m": "秒",
                    "jump": "厘米",
                    "pull_and_sit": "次",
                    "sit_and_reach": "厘米",
                    "vc": "毫升",
                }[source]
                measured = f"{_field(detail, source, kind)}{unit}"
        items[target] = GradeItem(
            color=GradeItemColor.Red if red else GradeItemColor.Green,
            rank=rank,
            grade=measured,
            score=score,
        )
    reports = {}
    for key in ("report_desc", "report_status", "report_type"):
        value = summary.get(key)
        if value is not None and not isinstance(value, str):
            raise GymParseError(f"体测摘要 {key} 应为字符串或 null")
        reports[key] = value if value is not None else "暂无"
    return Grade(
        name=_field(detail, "student_name", str),
        stu_id=_field(detail, "student_num", str),
        grade=_field(detail, "total_grade", str),
        score=_field(detail, "total_score", float),
        eye=eye,
        report_desc=reports["report_desc"],
        report_status=reports["report_status"],
        report_type=reports["report_type"],
        short_run=items["short_run"],
        bmi=items["bmi"],
        jump=items["jump"],
        pull_and_sit=items["pull_and_sit"],
        run=items["run"],
        sit_and_reach=items["sit_and_reach"],
        vc=items["vc"],
    )
