"""研究生系统异常。"""


class YjsxtError(Exception):
    """研究生系统基础异常。"""


class YjsxtNetworkError(YjsxtError):
    """网络请求失败。"""


class YjsxtStatusError(YjsxtError):
    def __init__(self, status_code: int) -> None:
        self.status_code = status_code
        super().__init__(f"HTTP {status_code}")


class YjsxtParseError(YjsxtError):
    """响应不符合预期格式。"""


class YjsxtLoginError(YjsxtError):
    def __init__(self, message: str = "研究生系统登录失败") -> None:
        self.message = message
        super().__init__(message)


class TokenExpired(YjsxtError):
    """研究生系统会话已失效，需要重新登录。"""
