"""体测系统异常。"""


class GymError(Exception):
    """体测系统基础异常。"""


class GymNetworkError(GymError):
    """网络请求失败。"""


class GymStatusError(GymError):
    def __init__(self, status_code: int) -> None:
        self.status_code = status_code
        super().__init__(f"HTTP {status_code}")


class GymParseError(GymError):
    """服务端响应不符合预期格式。"""


class GymLoginError(GymError):
    """体测登录失败。"""


class TokenExpired(GymError):
    """体测系统会话已失效。"""
