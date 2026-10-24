import httpx

from . import parse
from ._http import request
from .models import CardHistory, CardHistoryType, CardInfo
from .token import PtToken


class PtClient:
    """复用连接的异步个人门户客户端；注入的 HTTP 客户端由调用方关闭。"""

    def __init__(
        self, token: PtToken, *, client: httpx.AsyncClient | None = None
    ) -> None:
        self._token = token
        self._client = client if client is not None else httpx.AsyncClient(timeout=30.0)
        self._owns_client = client is None

    async def _text(
        self, method: str, path: str, *, csrf_token: str | None = None, **kwargs
    ) -> str:
        headers = httpx.Headers(self._token.headers)
        if csrf_token is not None:
            headers["X-XSRF-TOKEN"] = csrf_token
        response = await request(self._client, method, path, headers=headers, **kwargs)
        return response.text

    async def get_card_info(self) -> CardInfo:
        return parse.card_info(
            await self._text("GET", "/api/hndxYkt/getCardUserInfo/info")
        )

    async def get_card_history(
        self, year: int, month: int, history_type: CardHistoryType
    ) -> CardHistory:
        """先获取 CSRF，再查询当月充值或消费；结束日沿用 Rust 的 31 日。"""
        if type(year) is not int or not 1 <= year <= 65535:
            raise ValueError("年份必须为 1 至 65535 的整数")
        if type(month) is not int or not 1 <= month <= 12:
            raise ValueError("月份必须为 1 至 12 的整数")
        selection = CardHistoryType(history_type)
        csrf = parse.csrf_token(await self._text("GET", "/api/security/token"))
        body = await self._text(
            "POST",
            "/api/hndxYkt/getAccHisConsubDzzfLog/detail",
            csrf_token=csrf,
            data={
                "beginDate": f"{year}-{month:02}-01",
                "endDate": f"{year}-{month:02}-31",
                "pageSize": "100000",
                "trancode": "15" if selection is CardHistoryType.Consumption else "16",
            },
        )
        return parse.card_history(body)

    async def get_unread_email_count(self) -> int | None:
        """返回未读数，None 表示尚未绑定邮箱。"""
        return parse.email_unread_count(
            await self._text("GET", "/api/v1/email/unRead/count")
        )

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def __aenter__(self) -> "PtClient":
        return self

    async def __aexit__(self, *exc) -> None:
        await self.aclose()
