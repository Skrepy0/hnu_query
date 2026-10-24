"""湖南大学大物实验平台，对应 Rust lab 模块。"""

from .client import LabClient
from .course import get_course_list
from .exceptions import (
    CaptchaError,
    CaptchaResolverError,
    LabError,
    LabLoginError,
    LabNetworkError,
    LabParseError,
    LabStatusError,
    LoginIssue,
    OtherError,
    PasswordError,
)
from .grade import get_lab_grade, get_virtual_lab_grade
from .login import CaptchaResolver, acquire_by_login
from .models import (
    Course,
    LabGrade,
    LabGradeDetailItem,
    LabSchedule,
    Semester,
    VirtualLabGrade,
)
from .schedule import get_lab_schedule
from .semester import get_semester
from .token import LabToken

__all__ = [
    "CaptchaError",
    "CaptchaResolver",
    "CaptchaResolverError",
    "Course",
    "LabClient",
    "LabError",
    "LabGrade",
    "LabGradeDetailItem",
    "LabLoginError",
    "LabNetworkError",
    "LabParseError",
    "LabSchedule",
    "LabStatusError",
    "LabToken",
    "LoginIssue",
    "OtherError",
    "PasswordError",
    "Semester",
    "VirtualLabGrade",
    "acquire_by_login",
    "get_course_list",
    "get_lab_grade",
    "get_lab_schedule",
    "get_semester",
    "get_virtual_lab_grade",
]
