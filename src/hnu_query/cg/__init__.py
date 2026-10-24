"""湖南大学 CG 编程平台，提供认证、页面导航和通用元数据。"""

from .client import CgClient
from .course import (
    get_assignment_list,
    get_course_list,
    get_problem_list,
    get_problem_page,
)
from .exceptions import (
    CaptchaError,
    CgError,
    CgLoginError,
    CgNavigationError,
    CgNetworkError,
    CgStatusError,
    LoginError,
    LoginFailed,
    PasswordError,
    TokenExpired,
)
from .login import CgSession
from .models import CgAssignment, CgCourse, CgProblem
from .token import CgToken

__all__ = [
    "CaptchaError",
    "CgAssignment",
    "CgClient",
    "CgCourse",
    "CgError",
    "CgLoginError",
    "CgNavigationError",
    "CgNetworkError",
    "CgProblem",
    "CgSession",
    "CgStatusError",
    "CgToken",
    "LoginError",
    "LoginFailed",
    "PasswordError",
    "TokenExpired",
    "get_assignment_list",
    "get_course_list",
    "get_problem_list",
    "get_problem_page",
]
