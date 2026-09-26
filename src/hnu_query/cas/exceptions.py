from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .tfa import TFAToken


class CasError(Exception):
    """CAS 模块基础异常。"""


class CasLoginError(CasError):
    """登陆失败"""


class CasNetworkError(CasError):
    """网络层错误。"""


class CasStatusError(CasError):
    """HTTP 状态码异常。"""

    def __init__(self, status_code: int, body: str = "") -> None:
        self.status_code = status_code
        self.body = body
        super().__init__(f"HTTP {status_code}: {body}")


class TokenExpired(CasError):
    """CAS 会话已过期，需要重新登录。"""


class AccountIssue(CasError):
    """由用户账号问题导致的登录失败。"""


class PasswordError(AccountIssue):
    """密码错误。"""


class PasswordShouldChange(AccountIssue):
    """需要前往个人门户修改密码。"""


class AccountLocked(AccountIssue):
    """账号因多次输错密码被锁定。"""


class TFARequired(AccountIssue):
    """需要双因子认证。

    ``tfa_token`` 用于后续 ``send_sms`` / ``verify``。
    """

    def __init__(self, tfa_token: "TFAToken") -> None:
        self.tfa_token = tfa_token
        super().__init__("需要双因子认证")
