from dataclasses import dataclass, field

from hnu_query.cas import CasToken


@dataclass(frozen=True, slots=True)
class YjsxtToken:
    """研究生系统 URL 路径中的会话 ID。"""

    id: str = field(repr=False)

    @classmethod
    def from_id_unchecked(cls, id: str) -> "YjsxtToken":
        """恢复会话 ID，不向服务端验证有效性。"""
        return cls(id)

    @classmethod
    async def acquire_by_cas_login(cls, cas_token: CasToken) -> "YjsxtToken":
        from .login import acquire_by_cas_login

        return await acquire_by_cas_login(cas_token)
