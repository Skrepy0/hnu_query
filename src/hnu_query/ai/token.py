from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType


@dataclass(frozen=True, slots=True)
class AiToken:
    headers: Mapping[str, str] = field(repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "headers", MappingProxyType(dict(self.headers)))

    @classmethod
    def from_headers_unchecked(cls, headers: Mapping[str, str]) -> "AiToken":
        """恢复请求头，不验证服务器会话。"""
        return cls(headers)

    @classmethod
    async def acquire_by_cas_login(cls, cas_token) -> "AiToken":
        from .login import acquire_by_cas_login

        return await acquire_by_cas_login(cas_token)
