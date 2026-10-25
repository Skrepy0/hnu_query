"""AI 平台请求、解析及业务异常。"""


class AiError(Exception):
    """AI 平台基础异常。"""


class AiNetworkError(AiError):
    """网络请求失败。"""


class AiStatusError(AiError):
    def __init__(self, status_code: int) -> None:
        self.status_code = status_code
        super().__init__(f"HTTP {status_code}")


class AiParseError(AiError):
    """响应数据不符合预期。"""


class AiLoginError(AiError):
    """OAuth 登录链路不符合预期。"""


class AiActionError(AiError):
    """创建或删除 API Token 失败。"""


class TokenExpired(AiError):
    """AI 平台会话失效。"""
