"""湖南大学个人门户，对应 Rust pt 模块。"""

from .card import get_card_history, get_card_info
from .client import PtClient
from .email import get_unread_email_count
from .exceptions import (
    PtError,
    PtLoginError,
    PtNetworkError,
    PtParseError,
    PtStatusError,
)
from .login import acquire_by_cas_login
from .models import CardHistory, CardHistoryItem, CardHistoryType, CardInfo
from .token import PtToken

__all__ = [
    "CardHistory",
    "CardHistoryItem",
    "CardHistoryType",
    "CardInfo",
    "PtClient",
    "PtError",
    "PtLoginError",
    "PtNetworkError",
    "PtParseError",
    "PtStatusError",
    "PtToken",
    "acquire_by_cas_login",
    "get_card_history",
    "get_card_info",
    "get_unread_email_count",
]
