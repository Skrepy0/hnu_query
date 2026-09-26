"""hnu_query.ca —— 湖南大学可信电子凭证模块。

对应原 Rust 仓库的 ``ca`` 模块，提供凭证排名查询、
预览与文件下载能力。
"""
from hnu_query.credential.grade_rank import get_grade_rank
from hnu_query.credential.parse import preview_file_name
from .exceptions import (
    CaError,
    CaNetworkError,
    CaStatusError,
    CaParseError,
    CaLoginError,
)
from .file import preview_file, file
from .login import acquire_by_cas_login
from .token import CaToken

__all__ = [
    "CaToken",
    "acquire_by_cas_login",
    "get_grade_rank",
    "preview_file",
    "file",
    "preview_file_name",
    "CaError",
    "CaNetworkError",
    "CaStatusError",
    "CaParseError",
    "CaLoginError",
]
