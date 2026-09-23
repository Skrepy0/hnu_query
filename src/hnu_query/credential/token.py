from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class CaToken:
    """可信电子凭证平台的访问令牌。

    持有登录后获得的一组请求头（通常是 Cookie），
    后续所有请求都直接复用这组头。
    """
    headers: dict[str, str] = field(default_factory=dict)

    def is_empty(self) -> bool:
        return not self.headers