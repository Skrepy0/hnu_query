import httpx

from . import parse
from ._http import request
from .models import Course, Semester
from .token import YjsxtToken


class YjsxtClient:
    """复用连接的研究生客户端；注入的 HTTP 客户端由调用方关闭。"""

    def __init__(
        self, token: YjsxtToken, *, client: httpx.AsyncClient | None = None
    ) -> None:
        self._token = token
        self._client = client if client is not None else httpx.AsyncClient(timeout=30.0)
        self._owns_client = client is None

    async def get_semester(self) -> list[Semester]:
        response = await request(
            self._client, "GET", f"/gmis/{self._token.id}/student/default/bindterm"
        )
        return parse.semester(response.text)

    async def get_class_table(self, semester_id: str) -> list[Course]:
        response = await request(
            self._client,
            "POST",
            f"/gmis/{self._token.id}/student/pygl/py_kbcx_ew",
            data={"kblx": "xs", "termcode": semester_id},
        )
        return parse.class_table(response.text)

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def __aenter__(self) -> "YjsxtClient":
        return self

    async def __aexit__(self, *exc) -> None:
        await self.aclose()
