class CaError(Exception):
    """可信电子凭证模块基础异常。"""


class CaNetworkError(CaError):
    """网络层错误（连接失败、超时等）。"""


class CaStatusError(CaError):
    """HTTP 状态码异常。"""

    def __init__(self, status_code: int, body: str = "") -> None:
        self.status_code = status_code
        self.body = body
        super().__init__(f"HTTP {status_code}: {body}")


class CaParseError(CaError):
    """JSON 或 PDF 解析失败。"""


class CaLoginError(CaError):
    """CA 平台登录失败。"""
