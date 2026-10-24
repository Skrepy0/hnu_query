"""湖南大学学工系统，对应 Rust xgxt 模块。"""

from .client import XgxtClient
from .dormitory import Dormitory, parse_dormitory
from .exceptions import (
    XgxtError,
    XgxtLoginError,
    XgxtNetworkError,
    XgxtParseError,
    XgxtStatusError,
)
from .login import acquire_by_cas_login
from .models import Gender, Level, PersonalInfo
from .personal_info import get_person_info
from .token import XgxtToken

__all__ = [
    "Dormitory",
    "Gender",
    "Level",
    "PersonalInfo",
    "XgxtClient",
    "XgxtError",
    "XgxtLoginError",
    "XgxtNetworkError",
    "XgxtParseError",
    "XgxtStatusError",
    "XgxtToken",
    "acquire_by_cas_login",
    "get_person_info",
    "parse_dormitory",
]
