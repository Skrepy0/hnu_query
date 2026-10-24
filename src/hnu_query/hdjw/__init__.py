"""湖南大学教务系统，对应 Rust ``hdjw`` 模块。"""

from .class_table import get_class_table, get_class_table_extra
from .client import HdjwClient
from .empty_classroom import get_empty_classroom
from .exam_schedule import get_exam_schedule
from .exceptions import (
    HdjwError,
    HdjwLoginError,
    HdjwNetworkError,
    HdjwParseError,
    HdjwStatusError,
    TokenExpired,
)
from .grade import get_grade, get_grade_detail
from .login import acquire_by_cas_login
from .models import (
    Course,
    CourseSchedule,
    DataSource,
    Display,
    EmptyClassroom,
    ExamSchedule,
    ExtraCourse,
    Grade,
    GradeDetailItem,
    Range,
    Rank,
    RankDetail,
)
from .rank import get_rank
from .token import HdjwToken

__all__ = [
    "HdjwClient",
    "HdjwToken",
    "acquire_by_cas_login",
    "get_class_table",
    "get_class_table_extra",
    "get_empty_classroom",
    "get_exam_schedule",
    "get_grade",
    "get_grade_detail",
    "get_rank",
    "Course",
    "CourseSchedule",
    "ExtraCourse",
    "Grade",
    "GradeDetailItem",
    "ExamSchedule",
    "EmptyClassroom",
    "Rank",
    "RankDetail",
    "Range",
    "DataSource",
    "Display",
    "HdjwError",
    "HdjwLoginError",
    "HdjwNetworkError",
    "HdjwParseError",
    "HdjwStatusError",
    "TokenExpired",
]
