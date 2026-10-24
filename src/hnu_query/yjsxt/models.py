from pydantic import BaseModel


class Semester(BaseModel):
    xn: int
    xq: int
    id: str


class CourseSchedule(BaseModel):
    week: int
    day: int
    place: str
    time: list[int]


class Course(BaseModel):
    course_name: str
    course_id: str
    class_name: str
    teacher: str | None = None
    schedule: list[CourseSchedule] | None = None
