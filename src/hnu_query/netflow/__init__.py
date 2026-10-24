"""湖南大学校园网流量系统，对应 Rust netflow 模块。"""

from .client import NetflowClient
from .detail import get_day_detail, get_month_detail
from .exceptions import (
    NetflowError,
    NetflowLoginError,
    NetflowNetworkError,
    NetflowParseError,
    NetflowStatusError,
)
from .login import acquire_by_cas_login
from .models import Detail, DetailItem, OrderItem, ThisMonthInfo, UnlockStatus
from .order import get_order
from .pay_info import get_overdue_payment
from .this_month import get_this_month_info
from .token import NetflowToken
from .user_info import get_unlock_status

__all__ = [
    "Detail",
    "DetailItem",
    "NetflowClient",
    "NetflowError",
    "NetflowLoginError",
    "NetflowNetworkError",
    "NetflowParseError",
    "NetflowStatusError",
    "NetflowToken",
    "OrderItem",
    "ThisMonthInfo",
    "UnlockStatus",
    "acquire_by_cas_login",
    "get_day_detail",
    "get_month_detail",
    "get_order",
    "get_overdue_payment",
    "get_this_month_info",
    "get_unlock_status",
]
