from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CasToken:
    """统一身份认证系统的令牌。"""
    cookie: str
    stu_id: str

    @classmethod
    def from_cookie_unchecked(cls, cookie: str, stu_id: str) -> "CasToken":
        """从 Cookie 字符串创建 CasToken。

        对应 Rust ``CasToken::from_cookie_unchecked``。

        Preconditions:
            ``cookie`` 必须是合法的 CAS Cookie，
            ``stu_id`` 必须与之对应，否则行为未定义。
        """
        return cls(cookie=cookie, stu_id=stu_id)
