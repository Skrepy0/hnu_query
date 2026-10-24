import json
import re
from collections.abc import Mapping

from .dormitory import parse_dormitory
from .exceptions import XgxtParseError
from .models import Gender, Level, PersonalInfo


def extract_xgxt_entry(body: str) -> dict[str, str]:
    try:
        value = json.loads(body)
        fields = value["data"]["groupFields"][0]["fields"]
        if not isinstance(fields, list):
            raise TypeError("fields 应为数组")
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        raise XgxtParseError("无法解析学工表单字段") from exc
    entries = {}
    for field in fields:
        if not isinstance(field, dict) or not isinstance(field.get("fieldName"), str):
            continue
        value = field.get("defaultValue")
        if isinstance(value, str):
            entries[field["fieldName"]] = value
        elif type(value) is int and -(2**63) <= value < 2**63:
            entries[field["fieldName"]] = str(value)
    return entries


def _unsigned(value: str, maximum: int) -> int:
    try:
        if re.fullmatch(r"\+?[0-9]+", value) is None:
            raise ValueError("整数格式错误")
        number = int(value)
        if number > maximum:
            raise ValueError("整数超出范围")
        return number
    except ValueError as exc:
        raise XgxtParseError("学工系统整数格式错误或超出范围") from exc


def person_info(entries: Mapping[str, str]) -> PersonalInfo:
    if not isinstance(entries, Mapping) or any(
        not isinstance(value, str) for value in entries.values()
    ):
        raise XgxtParseError("学工表单条目必须为字符串映射")

    def required(key):
        if key not in entries:
            raise XgxtParseError(f"学工信息缺少 {key} 字段")
        return entries[key]

    genders = {"1": Gender.Male, "2": Gender.Female}
    levels = {"1": Level.Doctoral, "2": Level.Postgraduate, "3": Level.Undergraduate}
    gender, level = required("性别"), required("培养层次")
    if gender not in genders or level not in levels:
        raise XgxtParseError("未知性别或培养层次")
    xz = entries.get("学制(年)")
    raw_dorm, room = required("寝室楼"), required("寝室号")
    return PersonalInfo(
        name=required("姓名"),
        enter_year=_unsigned(required("年级"), 65535),
        xz=_unsigned(xz, 255) if xz else None,
        stu_id=required("学号"),
        gender=genders[gender],
        level=levels[level],
        academy=required("学院"),
        major=required("专业"),
        class_=required("班级"),
        dormitory=parse_dormitory(raw_dorm, room) if raw_dorm and room else None,
        politic=entries.get("政治面貌"),
        race=entries.get("民族"),
        hometown=entries.get("籍贯"),
        phone=entries.get("手机号码"),
        wechat=entries.get("微信号"),
        qq=entries.get("QQ号码"),
        email=entries.get("电子邮箱"),
    )
