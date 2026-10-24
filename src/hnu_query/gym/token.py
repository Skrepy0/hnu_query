from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Mapping

from hnu_query.cas import CasToken


@dataclass(frozen=True, slots=True)
class GymToken:
    headers: Mapping[str, str] = field(repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "headers", MappingProxyType(dict(self.headers)))

    @classmethod
    def from_headers_unchecked(cls, headers: Mapping[str, str]) -> "GymToken":
        """恢复请求头，不向服务器验证有效性。"""
        return cls(headers)

    @classmethod
    async def acquire_by_cas_login(cls, cas_token: CasToken) -> "GymToken":
        from .login import acquire_by_cas_login

        return await acquire_by_cas_login(cas_token)

    @classmethod
    async def acquire_by_direct_login(cls, stu_id: str, password: str) -> "GymToken":
        from .login import acquire_by_direct_login

        return await acquire_by_direct_login(stu_id, password)
