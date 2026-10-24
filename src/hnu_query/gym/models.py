from datetime import date as Date
from enum import Enum

from pydantic import BaseModel


class Appointment(BaseModel):
    """预约信息；status 和 test_type 保留服务端整数编码。"""

    name: str
    desc: str
    show_date: str
    date: Date
    time: str
    test_type: int
    status: int


class GradeItemColor(str, Enum):
    Green = "Green"
    Red = "Red"


class GradeItem(BaseModel):
    color: GradeItemColor
    rank: str
    grade: str
    score: int


class EyeGrade(BaseModel):
    eyesight_right: str
    eyesight_left: str
    eyesight_right_detail: str
    eyesight_left_detail: str
    eye_mirror_right: str
    eye_mirror_right_detail: str
    eye_mirror_left: str
    eye_mirror_left_detail: str
    eye_ametropia_right: str
    eye_ametropia_right_detail: str
    eye_ametropia_left: str
    eye_ametropia_left_detail: str


class Grade(BaseModel):
    name: str
    stu_id: str
    grade: str
    score: float
    report_desc: str
    report_status: str
    report_type: str
    eye: EyeGrade
    short_run: GradeItem
    bmi: GradeItem
    jump: GradeItem
    pull_and_sit: GradeItem
    run: GradeItem
    sit_and_reach: GradeItem
    vc: GradeItem
