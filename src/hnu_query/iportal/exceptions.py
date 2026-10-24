"""新门户异常。"""


class IPortalError(Exception):
    """新门户基础异常。"""


class IPortalNetworkError(IPortalError):
    """网络请求失败。"""


class IPortalStatusError(IPortalError):
    def __init__(self, status_code: int) -> None:
        self.status_code = status_code
        super().__init__(f"HTTP {status_code}")


class IPortalParseError(IPortalError):
    """响应不符合预期格式。"""


class IPortalLoginError(IPortalError):
    """无法取得新门户会话。"""


class IPortalTokenExpired(IPortalError):
    """新门户会话已失效。"""
