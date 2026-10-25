"""实验平台纯解析函数，字段与 Rust 原始结构严格对应。"""

import json
import re
from datetime import datetime
from typing import TypeVar

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .exceptions import LabParseError
from .models import (
    Course,
    LabGrade,
    LabGradeDetailItem,
    LabSchedule,
    Semester,
    VirtualLabGrade,
)


class _Raw(BaseModel):
    model_config = ConfigDict(strict=True)


class _Semester(_Raw):
    id: str
    text: str


class _Course(_Raw):
    CourseName: str
    CourseFinalScore: str
    CourseID: str


class _Schedule(_Raw):
    SeatNo: str
    LabName: str
    CourseName: str
    UserName: str
    Weeks: str
    WeekName: str
    ClassDate: str
    StartTime: str
    ClassRoom: str
    MobileNum: str
    Email: str


class _LabGrade(_Raw):
    AttendanceName: str
    LabName: str
    LabScore: str
    LabID: str
    ClassRoom: str


class _Detail(_Raw):
    LabScoreStructureID: int = Field(ge=-(2**31), le=2**31 - 1)
    LabID: int = Field(ge=-(2**31), le=2**31 - 1)
    LabStructureScore: float | None = None


class _Structure(_Raw):
    LabScoreStructureID: int = Field(ge=-(2**31), le=2**31 - 1)
    LabScoreStructureName: str


class _VirtualGrade(_Raw):
    LabName: str
    LabScore: str


T = TypeVar("T", bound=BaseModel)


def _rows(body: str, model: type[T], path: tuple[str, ...] = ()) -> list[T]:
    try:
        data = json.loads(body)
        for key in path:
            data = data[key]
        if not isinstance(data, list):
            raise TypeError("应为列表")
        return [model.model_validate(item) for item in data]
    except (ValueError, TypeError, KeyError, ValidationError) as exc:
        raise LabParseError("无法解析实验平台数据结构") from exc


def _integer(text: str, minimum: int, maximum: int) -> int:
    if re.fullmatch(r"[+-]?[0-9]+", text) is None:
        raise LabParseError("实验平台数字字段格式错误")
    try:
        number = int(text)
    except ValueError as exc:
        raise LabParseError("实验平台数字字段过长") from exc
    if not minimum <= number <= maximum:
        raise LabParseError("实验平台数字字段超出范围")
    return number


def semester(body: str) -> list[Semester]:
    result = []
    for row in _rows(body, _Semester):
        parts = re.split(r"[-_ ]", row.text)
        if len(parts) != 3:
            raise LabParseError("无法解析实验平台学期")
        result.append(
            Semester(
                xn=_integer(parts[0], 0, 65535),
                xq=_integer(parts[2], 0, 255),
                id=row.id,
            )
        )
    return result


def course_list(body: str) -> list[Course]:
    return [
        Course(name=row.CourseName, score=row.CourseFinalScore or None, id=row.CourseID)
        for row in _rows(body, _Course, ("rows",))
    ]


def lab_schedule(body: str) -> list[LabSchedule]:
    result = []
    days = {f"星期{char}": number for number, char in enumerate("一二三四五六日", 1)}
    for row in _rows(body, _Schedule, ("rows",)):
        if row.WeekName not in days:
            raise LabParseError("无法解析实验上课星期")
        try:
            day = datetime.strptime(row.ClassDate.split(" ", 1)[0], "%Y/%m/%d").date()
            time = datetime.strptime(row.StartTime, "%H:%M").time()
        except ValueError as exc:
            raise LabParseError("无法解析实验日期或开始时间") from exc
        result.append(
            LabSchedule(
                seat=row.SeatNo,
                name=row.LabName,
                course=row.CourseName,
                teacher=row.UserName,
                week=_integer(row.Weeks, 0, 255),
                day=days[row.WeekName],
                date_time=datetime.combine(day, time),
                place=row.ClassRoom,
                phone=row.MobileNum or None,
                email=row.Email or None,
            )
        )
    return result


def lab_grade(grade_str: str, detail_str: str, structure_str: str) -> list[LabGrade]:
    grades = _rows(grade_str, _LabGrade, ("rows",))
    details = _rows(detail_str, _Detail, ("Data", "Lablist"))
    structures = {
        row.LabScoreStructureID: row.LabScoreStructureName
        for row in _rows(structure_str, _Structure, ("Data",))
    }
    labs = {}
    result = []
    for row in grades:
        if row.LabScore == "" or "虚拟" in row.ClassRoom:
            continue
        lab_id = _integer(row.LabID, -(2**31), 2**31 - 1)
        item = LabGrade(
            lab_name=row.LabName,
            score=row.LabScore,
            attendance=row.AttendanceName or None,
            details=[],
        )
        result.append(item)
        labs[lab_id] = item
    for detail in details:
        if (
            detail.LabStructureScore is not None
            and detail.LabID in labs
            and detail.LabScoreStructureID in structures
        ):
            labs[detail.LabID].details.append(
                LabGradeDetailItem(
                    name=structures[detail.LabScoreStructureID],
                    score=detail.LabStructureScore,
                )
            )
    return result


def virtual_lab_grade(body: str) -> list[VirtualLabGrade]:
    # Rust 稳定排序后按名称去重，保留同名实验最先出现的成绩。
    unique = {}
    for row in _rows(body, _VirtualGrade, ("rows",)):
        if row.LabName not in unique:
            unique[row.LabName] = VirtualLabGrade(lab_name=row.LabName, score=row.LabScore or None)
    return [unique[name] for name in sorted(unique)]
