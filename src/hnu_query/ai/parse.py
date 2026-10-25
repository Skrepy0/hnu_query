"""与 Rust 对齐的纯 JSON 解析，不在错误信息中输出响应凭据。"""

import json

from pydantic import ValidationError

from .exceptions import AiParseError
from .models import TokenInfo


def _object(text: str) -> dict:
    try:
        value = json.loads(text)
    except ValueError as exc:
        raise AiParseError("AI 响应不是有效 JSON") from exc
    if not isinstance(value, dict):
        raise AiParseError("AI 响应不是对象")
    return value


def token_list(text: str) -> list[TokenInfo]:
    data = _object(text).get("data")
    if data is None:
        return []
    if not isinstance(data, list):
        raise AiParseError("Token 列表不是数组")
    try:
        return [TokenInfo.model_validate(item) for item in data]
    except ValidationError as exc:
        raise AiParseError("Token 元数据无效") from exc


def _data(text: str) -> dict:
    data = _object(text).get("data")
    if not isinstance(data, dict):
        raise AiParseError("AI 响应缺少 data 对象")
    return data


def token_key(text: str) -> str:
    key = _data(text).get("key")
    if not isinstance(key, str):
        raise AiParseError("无法解析 Token key")
    return key


def check_action_success(text: str) -> bool:
    success = _object(text).get("success")
    if type(success) is not bool:
        raise AiParseError("无法解析操作结果")
    return success


def remaining_quota(text: str) -> int:
    quota = _data(text).get("total_granted")
    if type(quota) is not int or not 0 <= quota < 2**64:
        raise AiParseError("无法解析总配额")
    return quota


def bearer_token(text: str) -> str:
    token = _data(text).get("token")
    if (
        not isinstance(token, str)
        or not token
        or any(ord(char) < 33 or ord(char) > 126 for char in token)
    ):
        raise AiParseError("无法解析 Bearer Token")
    return token
