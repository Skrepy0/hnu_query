"""校园网流量系统异常。"""


class NetflowError(Exception):
    """流量系统基础异常。"""


class NetflowNetworkError(NetflowError):
    """网络请求失败。"""


class NetflowStatusError(NetflowError):
    def __init__(self, status_code: int) -> None:
        self.status_code = status_code
        super().__init__(f"HTTP {status_code}")


class NetflowParseError(NetflowError):
    """响应不符合预期格式。"""


class NetflowLoginError(NetflowError):
    """无法取得流量系统登录 Cookie。"""
