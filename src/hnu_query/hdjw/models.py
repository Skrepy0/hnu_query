"""字段含义与 Rust hdjw 模块一致，结果支持 Pydantic JSON 序列化。"""

from datetime import date as Date
from enum import Enum

from pydantic import BaseModel


class CourseSchedule(BaseModel):
    week: int
    day: int
    place: str
    time: list[int]


class ExtraCourse(BaseModel):
    course_name: str
    course_id: str
    course_type: str
    class_name: str
    area: str
    teacher: str
    credit: float
    extra: str | None = None
    people: int


class Course(BaseModel):
    course_name: str
    course_id: str
    course_type: str
    class_name: str
    area: str
    teacher: str | None = None
    credit: float
    extra: str | None = None
    people: int
    schedule: list[CourseSchedule]


class Grade(BaseModel):
    course_id: str
    course_name: str
    credit: float
    course_type1: str | None = None
    course_type2: str
    gpa: float | None = None
    score: float
    grade_tag: str | None = None
    grade_type: str
    jx0404id: str | None = None


class GradeDetailItem(BaseModel):
    name: str
    score: str
    percentage: str


class ExamSchedule(BaseModel):
    course_id: str
    course_name: str
    area: str | None = None
    classroom: str | None = None
    date: Date | None = None
    time: str | None = None
    seat: str | None = None


class RankDetail(BaseModel):
    arithmetic: str
    arithmetic_rank: str
    weighted: str
    weighted_rank: str
    gpa: str
    gpa_rank: str


class Rank(BaseModel):
    all: RankDetail | None = None
    must: RankDetail | None = None
    core: RankDetail | None = None


class Range(str, Enum):
    Major = "0"
    Minor = "1"


class DataSource(str, Enum):
    Total = "1"
    Execution = "2"


class Display(str, Enum):
    Max = "0"
    Initial = "1"


class EmptyClassroom(BaseModel):
    room_name: str
    room_type: str
    seat_count: int
    exam_seat_count: int
