"""个人门户异常。"""


class PtError(Exception):
    """个人门户基础异常。"""


class PtNetworkError(PtError):
    """网络请求失败。"""


class PtStatusError(PtError):
    def __init__(self, status_code: int) -> None:
        self.status_code = status_code
        super().__init__(f"HTTP {status_code}")


class PtParseError(PtError):
    """门户响应不符合预期格式。"""


class PtLoginError(PtError):
    """无法获取门户登录会话。"""
