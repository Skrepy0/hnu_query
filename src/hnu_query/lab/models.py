from datetime import datetime

from pydantic import BaseModel


class Semester(BaseModel):
    xn: int
    xq: int
    id: str


class Course(BaseModel):
    name: str
    score: str | None = None
    id: str


class LabSchedule(BaseModel):
    seat: str
    name: str
    course: str
    teacher: str
    week: int
    day: int
    date_time: datetime
    place: str
    phone: str | None = None
    email: str | None = None


class LabGradeDetailItem(BaseModel):
    name: str
    score: float | None = None


class LabGrade(BaseModel):
    lab_name: str
    score: str
    attendance: str | None = None
    details: list[LabGradeDetailItem]


class VirtualLabGrade(BaseModel):
    lab_name: str
    score: str | None = None
