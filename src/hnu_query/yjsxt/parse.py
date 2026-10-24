"""研究生系统明文 JSON 解析，对齐 Rust 的课程块和周次规则。"""

import json
import re
from collections import defaultdict
from typing import NamedTuple

from pydantic import BaseModel, ConfigDict, ValidationError

from .exceptions import YjsxtParseError
from .models import Course, CourseSchedule, Semester


class _Semester(BaseModel):
    model_config = ConfigDict(strict=True)
    termcode: str
    termname: str


class _CourseKey(NamedTuple):
    course_name: str
    course_id: str
    class_name: str
    teacher: str | None


def _json(body: str):
    try:
        return json.loads(body)
    except ValueError as exc:
        raise YjsxtParseError("研究生系统响应不是有效 JSON") from exc


def _unsigned(value: str, maximum: int) -> int:
    try:
        if re.fullmatch(r"\+?[0-9]+", value) is None:
            raise ValueError("数字格式错误")
        number = int(value)
        if number > maximum:
            raise ValueError("数字超出范围")
        return number
    except ValueError as exc:
        raise YjsxtParseError("研究生系统数字格式错误或超出范围") from exc


def semester(body: str) -> list[Semester]:
    data = _json(body)
    if not isinstance(data, list):
        raise YjsxtParseError("学期响应应为列表")
    result = []
    for item in data:
        try:
            raw = _Semester.model_validate(item)
        except ValidationError as exc:
            raise YjsxtParseError("学期字段格式错误") from exc
        if "-" not in raw.termname:
            raise YjsxtParseError("无法解析学期名称")
        year, rest = raw.termname.split("-", 1)
        term = next(
            (
                number
                for name, number in (
                    ("秋学期", 1),
                    ("春学期", 2),
                    ("暑假学期", 3),
                    ("寒假小学期", 4),
                )
                if name in rest
            ),
            None,
        )
        if term is None:
            raise YjsxtParseError("未知研究生学期")
        result.append(Semester(xn=_unsigned(year, 65535), xq=term, id=raw.termcode))
    return result


def _compact(value: str) -> str:
    return "".join(value.split())


def _course_block(lines: list[str]) -> tuple[_CourseKey, set[int], str]:
    if len(lines) != 5:
        raise YjsxtParseError("课程块必须为五行")
    values = []
    for line, prefix in zip(lines[:3], ("课程编号:", "课程名称:", "班级:")):
        if not line.startswith(prefix):
            raise YjsxtParseError("课程块行前缀或顺序不正确")
        values.append(_compact(line[len(prefix) :]))
    match = re.fullmatch(r"上课时间:\[([0-9\-]+)周\](.*)", _compact(lines[3]))
    if match is None:
        raise YjsxtParseError("无法解析上课周次")
    parts = match[1].split("-")
    if len(parts) not in (1, 2):
        raise YjsxtParseError("上课周次只能为单周次或一个连续区间")
    start = _unsigned(parts[0], 255)
    end = _unsigned(parts[-1], 255)
    parity = {"连续周": None, "单周": 1, "双周": 0}
    if match[2] not in parity:
        raise YjsxtParseError("未知上课周次类型")
    required_parity = parity[match[2]]
    weeks = {
        week
        for week in range(start, end + 1)
        if required_parity is None or week % 2 == required_parity
    }
    teacher_place = re.search(r"(.*)\[(.*)\]", _compact(lines[4]))
    if teacher_place is None:
        raise YjsxtParseError("无法解析教师和上课地点")
    course_id, course_name, class_name = values
    key = _CourseKey(course_name, course_id, class_name, teacher_place[1] or None)
    return key, weeks, teacher_place[2]


def parse_course_info(cell_text: str) -> list[tuple[_CourseKey, set[int], str]]:
    parts = [line.strip() for line in cell_text.split("<br/>") if line.strip()]
    if not parts or not parts[0].startswith("课程编号:"):
        raise YjsxtParseError("课程块前存在无法识别的内容或缺少课程编号")
    blocks = []
    for line in parts:
        if line.startswith("课程编号:"):
            blocks.append([])
        blocks[-1].append(line)
    return [_course_block(block) for block in blocks]


def class_table(body: str) -> list[Course]:
    data = _json(body)
    if not isinstance(data, dict) or not isinstance(data.get("rows"), list):
        raise YjsxtParseError("无法解析研究生课表行")
    courses = {}
    extra_courses = {}
    for row in data["rows"]:
        if not isinstance(row, dict) or not isinstance(row.get("mc"), str):
            raise YjsxtParseError("课表节次必须为字符串")
        for day in range(1, 8):
            cell = row.get(f"z{day}")
            if cell is None:
                continue
            if not isinstance(cell, str):
                raise YjsxtParseError("课表单元格必须为字符串或 null")
            for course, weeks, place in parse_course_info(cell):
                if row["mc"] == "无节次":
                    extra_courses[course] = None
                else:
                    period = _unsigned(row["mc"], 255)
                    schedules = courses.setdefault(course, defaultdict(list))
                    for week in sorted(weeks):
                        schedules[(week, day, place)].append(period)
    result = []

    def order(key):
        return key.course_id, key.course_name, key.class_name, key.teacher or ""

    for key in sorted(courses, key=order):
        schedule = [
            CourseSchedule(week=week, day=day, place=place, time=sorted(periods))
            for (week, day, place), periods in sorted(courses[key].items())
        ]
        result.append(Course(**key._asdict(), schedule=schedule))
    for key in sorted(extra_courses, key=order):
        result.append(Course(**key._asdict(), schedule=None))
    return result
