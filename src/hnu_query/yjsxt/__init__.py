"""湖南大学研究生系统，对应 Rust yjsxt 模块。"""

from .class_table import get_class_table
from .client import YjsxtClient
from .exceptions import (
    TokenExpired,
    YjsxtError,
    YjsxtLoginError,
    YjsxtNetworkError,
    YjsxtParseError,
    YjsxtStatusError,
)
from .login import acquire_by_cas_login
from .models import Course, CourseSchedule, Semester
from .semester import get_semester
from .token import YjsxtToken

__all__ = [
    "Course",
    "CourseSchedule",
    "Semester",
    "TokenExpired",
    "YjsxtClient",
    "YjsxtError",
    "YjsxtLoginError",
    "YjsxtNetworkError",
    "YjsxtParseError",
    "YjsxtStatusError",
    "YjsxtToken",
    "acquire_by_cas_login",
    "get_class_table",
    "get_semester",
]
