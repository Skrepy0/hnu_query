"""湖南大学新门户，对应 Rust iportal 模块。"""

from .card import get_card_info, get_card_transaction_records
from .client import IPortalClient
from .exceptions import (
    IPortalError,
    IPortalLoginError,
    IPortalNetworkError,
    IPortalParseError,
    IPortalStatusError,
    IPortalTokenExpired,
)
from .info import get_account_info
from .login import acquire_by_cas_login
from .models import (
    AccountInfo,
    ApplyItem,
    ApplyList,
    ApplyStatus,
    CardInfo,
    CardTransactionDetail,
    Gender,
    PersonalData,
    TermInfo,
    TermType,
    TransactionRecord,
    TransactionType,
)
from .personal import get_personal_data
from .task import get_apply_list
from .term import get_term_info
from .token import IPortalToken

__all__ = [
    "AccountInfo",
    "ApplyItem",
    "ApplyList",
    "ApplyStatus",
    "CardInfo",
    "CardTransactionDetail",
    "Gender",
    "IPortalClient",
    "IPortalError",
    "IPortalLoginError",
    "IPortalNetworkError",
    "IPortalParseError",
    "IPortalStatusError",
    "IPortalToken",
    "IPortalTokenExpired",
    "PersonalData",
    "TermInfo",
    "TermType",
    "TransactionRecord",
    "TransactionType",
    "acquire_by_cas_login",
    "get_account_info",
    "get_apply_list",
    "get_card_info",
    "get_card_transaction_records",
    "get_personal_data",
    "get_term_info",
]
