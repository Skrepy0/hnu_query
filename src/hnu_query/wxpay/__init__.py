"""湖南大学宿舍电量查询，对应 Rust wxpay 模块。"""

from .client import WxpayClient
from .electricity import get_electricity
from .exceptions import (
    WxpayAmbiguityError,
    WxpayError,
    WxpayNetworkError,
    WxpayParseError,
    WxpayStatusError,
)

__all__ = [
    "WxpayAmbiguityError",
    "WxpayClient",
    "WxpayError",
    "WxpayNetworkError",
    "WxpayParseError",
    "WxpayStatusError",
    "get_electricity",
]
