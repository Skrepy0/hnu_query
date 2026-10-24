from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Mapping

from hnu_query.cas import CasToken


@dataclass(frozen=True, slots=True)
class HdjwToken:
    """教务系统请求头；与 CAS 会话独立。"""

    headers: Mapping[str, str] = field(repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "headers", MappingProxyType(dict(self.headers)))

    @classmethod
    def from_headers_unchecked(cls, headers: Mapping[str, str]) -> "HdjwToken":
        """恢复请求头，不向服务器验证其有效性。"""
        return cls(headers=headers)

    @classmethod
    async def acquire_by_cas_login(cls, cas_token: CasToken) -> "HdjwToken":
        from .login import acquire_by_cas_login

        return await acquire_by_cas_login(cas_token)
