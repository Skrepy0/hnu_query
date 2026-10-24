"""hnu_query.cas —— 湖南大学统一身份认证（CAS）模块。"""
from .exceptions import (
    CasError,
    CasNetworkError,
    CasStatusError,
    TokenExpired,
    AccountIssue,
    PasswordError,
    PasswordShouldChange,
    AccountLocked,
    TFARequired,
)
from .login import acquire_by_login
from .tfa import TFAToken
from .ticket import get_ticket_url, extract_ticket, get_sticket
from .token import CasToken

__all__ = [
    "CasToken",
    "acquire_by_login",
    "TFAToken",
    "get_ticket_url",
    "extract_ticket",
    "get_sticket",
    "CasError",
    "CasNetworkError",
    "CasStatusError",
    "TokenExpired",
    "AccountIssue",
    "PasswordError",
    "PasswordShouldChange",
    "AccountLocked",
    "TFARequired",
]
