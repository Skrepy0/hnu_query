# src/hnu_query/ca/token.py
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Mapping


@dataclass(frozen=True, slots=True)
class CaToken:
    """可信电子凭证平台的访问令牌。

    持有登录后获得的一组请求头：
      - X-Access-Token: <token>
      - Cookie: X-Access-Token=<token>
    """
    headers: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self):
        object.__setattr__(self, "headers", MappingProxyType(dict(self.headers)))

    def is_empty(self) -> bool:
        return not self.headers
