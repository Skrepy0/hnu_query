import httpx

from . import parse
from ._http import BASE_URL, request
from .exceptions import AiActionError
from .models import TokenInfo
from .token import AiToken


def _id(value: int) -> None:
    if type(value) is not int or not 0 <= value < 2**64:
        raise ValueError("Token ID 必须为 u64 整数")


class AiClient:
    """复用 AI 平台连接；注入的连接由调用方关闭。"""

    def __init__(self, token: AiToken, *, client: httpx.AsyncClient | None = None):
        self._token = token
        self._client = client if client is not None else httpx.AsyncClient(timeout=30.0)
        self._owns_client = client is None

    async def _text(self, method: str, path: str, **kwargs) -> str:
        response = await request(
            self._client,
            method,
            BASE_URL + path,
            headers=dict(self._token.headers),
            **kwargs,
        )
        return response.text

    async def get_token_list(self) -> list[TokenInfo]:
        return parse.token_list(await self._text("GET", "/api/tokens"))

    async def get_token_key(self, id: int) -> str:
        _id(id)
        return parse.token_key(await self._text("GET", f"/api/tokens/{id}/key"))

    async def create_token(self, name: str) -> None:
        if not isinstance(name, str):
            raise ValueError("Token 名称必须是字符串")
        text = await self._text("POST", "/api/apply-token", json={"name": name, "quota": 2000000})
        if not parse.check_action_success(text):
            raise AiActionError("创建 Token 失败")

    async def delete_token(self, id: int) -> None:
        _id(id)
        text = await self._text("DELETE", f"/api/tokens/{id}")
        if not parse.check_action_success(text):
            raise AiActionError("删除 Token 失败")

    async def get_user_remaining_quota(self) -> int:
        return parse.remaining_quota(await self._text("GET", "/api/user-info"))

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def __aenter__(self) -> "AiClient":
        return self

    async def __aexit__(self, *exc) -> None:
        await self.aclose()
