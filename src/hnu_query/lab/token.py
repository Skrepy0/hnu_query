from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType


@dataclass(frozen=True, slots=True)
class LabToken:
    headers: Mapping[str, str] = field(repr=False)
    stu_id: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "headers", MappingProxyType(dict(self.headers)))

    @classmethod
    def from_headers_unchecked(cls, headers: Mapping[str, str], stu_id: str) -> "LabToken":
        """恢复请求头和对应学号，不验证会话有效性。"""
        return cls(headers, stu_id)

    @classmethod
    async def acquire_by_login(
        cls,
        stu_id: str,
        password: str,
        captcha_resolver,
        max_tried: int = 3,
    ) -> "LabToken":
        from .login import acquire_by_login

        return await acquire_by_login(stu_id, password, captcha_resolver, max_tried)
