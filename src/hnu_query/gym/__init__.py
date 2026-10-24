"""湖南大学体测系统，对应 Rust gym 模块。"""

from .appointment import get_appointment
from .client import GymClient
from .exceptions import (
    GymError,
    GymLoginError,
    GymNetworkError,
    GymParseError,
    GymStatusError,
    TokenExpired,
)
from .grade import get_grade
from .login import acquire_by_cas_login, acquire_by_direct_login
from .models import Appointment, EyeGrade, Grade, GradeItem, GradeItemColor
from .token import GymToken

__all__ = [
    "Appointment",
    "EyeGrade",
    "Grade",
    "GradeItem",
    "GradeItemColor",
    "GymClient",
    "GymError",
    "GymLoginError",
    "GymNetworkError",
    "GymParseError",
    "GymStatusError",
    "GymToken",
    "TokenExpired",
    "acquire_by_cas_login",
    "acquire_by_direct_login",
    "get_appointment",
    "get_grade",
]
