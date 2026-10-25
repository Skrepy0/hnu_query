from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from hnu_query.cas import CasToken


@dataclass(frozen=True, slots=True)
class PtToken:
    headers: Mapping[str, str] = field(repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "headers", MappingProxyType(dict(self.headers)))

    @classmethod
    def from_headers_unchecked(cls, headers: Mapping[str, str]) -> "PtToken":
        """恢复门户请求头，不向服务器验证有效性。"""
        return cls(headers)

    @classmethod
    async def acquire_by_cas_login(cls, cas_token: CasToken) -> "PtToken":
        from .login import acquire_by_cas_login

        return await acquire_by_cas_login(cas_token)
