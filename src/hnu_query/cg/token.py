from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType


@dataclass(frozen=True, slots=True)
class CgToken:
    headers: Mapping[str, str] = field(repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "headers", MappingProxyType(dict(self.headers)))

    @classmethod
    def from_headers_unchecked(cls, headers: Mapping[str, str]) -> "CgToken":
        """恢复请求头，不向服务器验证有效性。"""
        return cls(headers)
