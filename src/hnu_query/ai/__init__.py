"""湖南大学 AI/MaaS 平台，对应 Rust ai 模块。"""

from .client import AiClient
from .exceptions import (
    AiActionError,
    AiError,
    AiLoginError,
    AiNetworkError,
    AiParseError,
    AiStatusError,
    TokenExpired,
)
from .login import acquire_by_cas_login
from .management import create_token, delete_token, get_token_key, get_token_list
from .models import TokenInfo
from .token import AiToken
from .user_info import get_user_remaining_quota

__all__ = [
    "AiActionError",
    "AiClient",
    "AiError",
    "AiLoginError",
    "AiNetworkError",
    "AiParseError",
    "AiStatusError",
    "AiToken",
    "TokenExpired",
    "TokenInfo",
    "acquire_by_cas_login",
    "create_token",
    "delete_token",
    "get_token_key",
    "get_token_list",
    "get_user_remaining_quota",
]
