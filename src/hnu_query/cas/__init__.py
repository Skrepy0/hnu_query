"""hnu_query.cas —— 湖南大学统一身份认证（CAS）模块。"""

from .exceptions import (
    AccountIssue,
    AccountLocked,
    CasError,
    CasLoginError,
    CasNetworkError,
    CasParseError,
    CasStatusError,
    PasswordError,
    PasswordShouldChange,
    TFARequired,
    TokenExpired,
)
from .login import acquire_by_login
from .tfa import TFAToken
from .ticket import extract_ticket, get_sticket, get_ticket_url
from .token import CasToken

__all__ = [
    "CasToken",
    "acquire_by_login",
    "TFAToken",
    "get_ticket_url",
    "extract_ticket",
    "get_sticket",
    "CasError",
    "CasLoginError",
    "CasParseError",
    "CasNetworkError",
    "CasStatusError",
    "TokenExpired",
    "AccountIssue",
    "PasswordError",
    "PasswordShouldChange",
    "AccountLocked",
    "TFARequired",
]
