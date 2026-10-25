"""纯解析函数：不访问网络，可用保存的 Rust 响应样本离线验证。"""

import json
import re
from collections import defaultdict
from datetime import date
from functools import wraps

from .exceptions import HdjwParseError, TokenExpired
from .models import (
    Course,
    CourseSchedule,
    EmptyClassroom,
    ExamSchedule,
    ExtraCourse,
    Grade,
    GradeDetailItem,
    Rank,
    RankDetail,
)


def _parser(function):
    @wraps(function)
    def wrapped(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except (KeyError, IndexError, TypeError, ValueError, AttributeError) as exc:
            # 不在异常中附加完整响应，避免意外记录个人成绩或会话内容。
            raise HdjwParseError(f"{function.__name__}: 响应格式不正确") from exc

    return wrapped


def hdjw_response(body: str):
    if "window.initQzTable" in body:
        return body
    try:
        value = json.loads(body)
    except ValueError as exc:
        raise HdjwParseError("教务响应不是有效 JSON") from exc
    if isinstance(value, dict) and value.get("flag1") == 2:
        raise TokenExpired("教务会话已过期")
    return value


def _rows(body: str, *, count_required: bool = False) -> list[dict]:
    value = hdjw_response(body)
    if not isinstance(value, dict):
        raise HdjwParseError("响应应为 JSON 对象")
    if count_required:
        count = value.get("count")
        if type(count) is not int or count < 0:
            raise HdjwParseError("无法解析课程数量")
        if count == 0:
            return []
    rows = value.get("data")
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise HdjwParseError("响应 data 应为对象列表")
    return rows


def _numbers(text: str, separator: str) -> set[int]:
    result: set[int] = set()
    for part in text.strip().split(separator):
        match = re.fullmatch(r"(\d+)(?:-(\d+))?", part.strip())
        if match is None:
            raise HdjwParseError("无法解析周次或节次区间")
        start = int(match[1])
        end = int(match[2]) if match[2] else start
        if not 0 <= start <= end <= 255:
            raise HdjwParseError("周次或节次区间超出范围")
        result.update(range(start, end + 1))
    return result


@_parser
def course_schedule(sktime: str, skddmc: str) -> list[CourseSchedule]:
    times, places = sktime.split(";"), skddmc.split(";")
    if len(times) != len(places):
        raise HdjwParseError("上课时间与地点数量不匹配")
    merged = defaultdict(set)
    for text, place in zip(times, places):
        match = re.fullmatch(r"星期([一二三四五六日七])(.*?)节.*?\{\s*(.*?)周\}(.*)", text.strip())
        if match is None:
            raise HdjwParseError("无法解析上课时间")
        day = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "日": 7, "七": 7}[match[1]]
        periods = _numbers(match[2], "、")
        weeks = _numbers(match[3], ",")
        suffix = match[4].strip()
        if suffix not in ("", "(全周)", "(单周)", "(双周)"):
            raise HdjwParseError("未知的周次后缀")
        for week in weeks:
            if suffix == "(单周)" and week % 2 == 0:
                continue
            if suffix == "(双周)" and week % 2 == 1:
                continue
            merged[(week, day, place)].update(periods)
    return [
        CourseSchedule(week=week, day=day, place=place, time=sorted(periods))
        for (week, day, place), periods in sorted(merged.items())
    ]


def _course_fields(row: dict) -> dict:
    teacher = row.get("jg0101mc")
    return dict(
        course_name=row["kc_mc"].strip(),
        course_id=row["kch"],
        course_type=row["kcxz"],
        class_name=row["kt_mc"],
        area=row["skxqmc"],
        teacher=teacher.strip() if teacher is not None else None,
        credit=row["xf"],
        extra=row.get("fz_mc"),
        people=row["xkrs"],
    )


@_parser
def class_table(body: str) -> list[Course]:
    return [
        Course(
            **_course_fields(row),
            schedule=course_schedule(row["sktime"], row["skddmc"]),
        )
        for row in _rows(body, count_required=True)
        if row.get("sktime") is not None
    ]


@_parser
def class_table_extra(body: str) -> list[ExtraCourse]:
    result = []
    for row in _rows(body, count_required=True):
        if row.get("sktime") is None:
            fields = _course_fields(row)
            fields["teacher"] = fields["teacher"] or ""
            result.append(ExtraCourse(**fields))
    return result


@_parser
def grade(body: str) -> list[Grade]:
    return [
        Grade(
            course_id=row["kch"],
            course_name=row["kc_mc"],
            credit=row["xf"],
            course_type1=row.get("kcsx"),
            course_type2=row["kcxzmc"],
            gpa=row.get("jd"),
            score=row["zcj"],
            grade_tag=row.get("cjbs"),
            grade_type=row["falb"],
            jx0404id=row.get("jx0404id"),
        )
        for row in _rows(body)
    ]


def _number_text(value) -> str:
    if isinstance(value, str):
        return value
    if type(value) is int:
        return str(value)
    if type(value) is float:
        return str(int(value)) if value.is_integer() else str(value)
    raise HdjwParseError("字段应为数字或字符串")


@_parser
def grade_detail(body: str) -> list[GradeDetailItem]:
    html = hdjw_response(body)
    if not isinstance(html, str):
        raise HdjwParseError("无法解析成绩详情 HTML")
    array = re.search(r"\blet\s+arr\s*=\s*", html)
    if array is None:
        raise HdjwParseError("找不到成绩详情数据")
    rows, _ = json.JSONDecoder().raw_decode(html[array.end() :])
    data = {key: _number_text(value) for key, value in rows[0].items()}
    # 只解析列定义，不执行服务端 JavaScript。
    columns = re.search(r"\bcols\s*:\s*\[\s*\[(.*?)\]\s*\]", html, re.S)
    if columns is None:
        raise HdjwParseError("找不到成绩详情表头")
    names = {}
    for column in re.findall(r"\{([^{}]*)\}", columns[1]):
        fields = dict(re.findall(r"""(?:["']?)(field|title)["']?\s*:\s*["']([^"']*)["']""", column))
        if "field" in fields:
            names[fields["field"]] = fields["title"]
    return [
        GradeDetailItem(name=names[key[:-2]], score=data[key[:-2]], percentage=value)
        for key, value in data.items()
        if key.endswith("bl") and value != "0%"
    ]


@_parser
def exam_schedule(body: str) -> list[ExamSchedule]:
    result = []
    for row in _rows(body):
        day = time = None
        if row.get("kssj") is not None:
            raw_date, time = row["kssj"].split()
            day = date.fromisoformat(raw_date)
        result.append(
            ExamSchedule(
                course_id=row["kch"],
                course_name=row["kskcmc"],
                area=row.get("ksxq"),
                classroom=row.get("js_mc"),
                date=day,
                time=time,
                seat=row.get("zwh"),
            )
        )
    return result


@_parser
def rank(body: str) -> Rank:
    value = hdjw_response(body)
    data = value["data"]
    if not isinstance(data, dict):
        raise HdjwParseError("无法解析排名数据")
    result = {}
    for target, key in (("all", "allPm"), ("must", "bxkcPm"), ("core", "hxkcPm")):
        if key in data:
            row = data[key]
            result[target] = RankDetail(
                arithmetic=_number_text(row["avgzcj"]),
                arithmetic_rank=row["avgzcjpm"],
                weighted=_number_text(row["pjxfj"]),
                weighted_rank=row["pjxfjpm"],
                gpa=_number_text(row["pjxfjd"]),
                gpa_rank=row["pjxfjdpm"],
            )
    return Rank(**result)


@_parser
def empty_classroom(body: str, time: list[int]) -> list[EmptyClassroom]:
    value = hdjw_response(body)
    if not isinstance(value, list) or len(value) < 5 or not isinstance(value[4], list):
        raise HdjwParseError("无法解析空教室信息")
    result = []
    for row in value[4]:
        if not isinstance(row, list) or len(row) < len(time) + 4:
            raise HdjwParseError("空教室信息列数不正确")
        if any(row[i] is not None for i in range(1, len(time) + 1)):
            continue
        seats = re.fullmatch(r"\((\d+)/(\d+)\)", row[2 + len(time)])
        if seats is None:
            raise HdjwParseError("无法解析教室座位数")
        result.append(
            EmptyClassroom(
                room_name=row[0],
                room_type=row[3 + len(time)],
                seat_count=int(seats[1]),
                exam_seat_count=int(seats[2]),
            )
        )
    return result
