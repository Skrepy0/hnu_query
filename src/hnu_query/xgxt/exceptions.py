"""学工系统异常。"""


class XgxtError(Exception):
    """学工系统基础异常。"""


class XgxtNetworkError(XgxtError):
    """网络请求失败。"""


class XgxtStatusError(XgxtError):
    def __init__(self, status_code: int) -> None:
        self.status_code = status_code
        super().__init__(f"HTTP {status_code}")


class XgxtParseError(XgxtError):
    """响应不符合预期格式。"""


class XgxtLoginError(XgxtError):
    """无法获取学工会话。"""
