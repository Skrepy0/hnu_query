# src/hnu_query/ca/token.py
from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType


@dataclass(frozen=True, slots=True)
class CaToken:
    """可信电子凭证平台的访问令牌。

    持有登录后获得的一组请求头：
      - X-Access-Token: <token>
      - Cookie: X-Access-Token=<token>
    """

    headers: Mapping[str, str] = field(default_factory=dict, repr=False)

    def __post_init__(self):
        object.__setattr__(self, "headers", MappingProxyType(dict(self.headers)))

    def is_empty(self) -> bool:
        return not self.headers

    @classmethod
    def from_headers_unchecked(cls, headers: Mapping[str, str]) -> "CaToken":
        """恢复请求头，不验证服务器会话。"""
        return cls(headers)
