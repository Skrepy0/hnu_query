import asyncio

import httpx

from . import parse
from ._http import request
from .models import PersonalInfo
from .token import XgxtToken


class XgxtClient:
    """复用连接的学工客户端；注入的 HTTP 客户端由调用方关闭。"""

    def __init__(
        self, token: XgxtToken, *, client: httpx.AsyncClient | None = None
    ) -> None:
        self._token = token
        self._client = client if client is not None else httpx.AsyncClient(timeout=30.0)
        self._owns_client = client is None

    async def _text(self, name: str) -> str:
        response = await request(
            self._client,
            f"/zftal-xgxt-web/dynamic/form/group/{name}/default.zf",
            headers=dict(self._token.headers),
            params={"dataId": "null"},
        )
        return response.text

    async def get_person_info(self) -> PersonalInfo:
        """并发获取个人、在校、联系方式，按该顺序合并同名字段。"""
        tasks = [
            asyncio.create_task(self._text(name))
            for name in ("userInfo", "zxxx", "lxfs1")
        ]
        try:
            bodies = await asyncio.gather(*tasks)
        except BaseException:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            raise
        entries = {}
        for body in bodies:
            entries.update(parse.extract_xgxt_entry(body))
        return parse.person_info(entries)

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def __aenter__(self) -> "XgxtClient":
        return self

    async def __aexit__(self, *exc) -> None:
        await self.aclose()
