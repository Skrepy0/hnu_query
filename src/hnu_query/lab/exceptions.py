"""大物实验平台异常。"""


class LabError(Exception):
    """实验平台基础异常。"""


class LabNetworkError(LabError):
    """网络请求失败。"""


class LabStatusError(LabError):
    def __init__(self, status_code: int) -> None:
        self.status_code = status_code
        super().__init__(f"HTTP {status_code}")


class LabParseError(LabError):
    """响应数据不符合预期格式。"""


class LabLoginError(LabError):
    """登录失败。"""


class LoginIssue(LabLoginError):
    """服务端登录失败，对应 Rust LoginIssue。"""


class PasswordError(LoginIssue):
    """账号或密码错误。"""


class CaptchaError(LoginIssue):
    """尝试次数耗尽，验证码仍未通过。"""


class OtherError(LoginIssue):
    def __init__(self, message: str | None = None) -> None:
        self.message = message
        super().__init__(message or "实验平台拒绝登录")


class CaptchaResolverError(LabLoginError):
    """调用方提供的验证码识别器失败。"""
