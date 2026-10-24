"""宿舍电量查询异常。"""


class WxpayError(Exception):
    """电量查询基础异常。"""


class WxpayNetworkError(WxpayError):
    """网络请求失败。"""


class WxpayStatusError(WxpayError):
    def __init__(self, status_code: int) -> None:
        self.status_code = status_code
        super().__init__(f"HTTP {status_code}")


class WxpayParseError(WxpayError):
    """宿舍无法映射或电量响应格式错误。"""


class WxpayAmbiguityError(WxpayError):
    """无法从南北两次请求中选出唯一成功的响应。"""
