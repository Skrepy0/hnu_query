"""编程平台异常。"""


class CgError(Exception):
    """CG 基础异常。"""


class CgNetworkError(CgError):
    """网络请求失败。"""


class CgStatusError(CgError):
    def __init__(self, status_code: int) -> None:
        self.status_code = status_code
        super().__init__(f"HTTP {status_code}")


class CgNavigationError(CgError):
    """页面跳转缺失或不符合预期。"""


class LoginError(CgError):
    """CG 登录失败，对应 Rust LoginError。"""


class CgLoginError(LoginError):
    """登录响应不符合预期。"""


class CaptchaError(LoginError):
    """验证码错误。"""


class PasswordError(LoginError):
    """账号或密码错误。"""


class LoginFailed(LoginError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(f"CG 登录失败，错误码: {code}")


class TokenExpired(CgError):
    """CG 会话已失效。"""
