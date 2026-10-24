"""教务系统的网络、登录、解析和会话异常。"""


class HdjwError(Exception):
    """教务系统基础异常。"""


class HdjwNetworkError(HdjwError):
    """网络请求失败。"""


class HdjwStatusError(HdjwError):
    """服务端返回非预期 HTTP 状态。"""

    def __init__(self, status_code: int, body: str = "") -> None:
        self.status_code = status_code
        self.body = body
        super().__init__(f"HTTP {status_code}: {body}")


class HdjwParseError(HdjwError):
    """响应数据不符合预期格式。"""


class HdjwLoginError(HdjwError):
    """CAS 票据兑换教务会话失败。"""


class TokenExpired(HdjwError):
    """教务会话已失效，需要通过 CAS 重新登录。"""
