import asyncio
import calendar
from datetime import date, datetime

import httpx

from . import parse
from ._http import request
from .models import (
    AccountInfo,
    ApplyList,
    CardInfo,
    CardTransactionDetail,
    PersonalData,
    TermInfo,
)
from .token import IPortalToken


def _u32(value: int) -> None:
    if type(value) is not int or not 0 <= value < 2**32:
        raise ValueError("分页参数必须为 0 至 4294967295 的整数")


class IPortalClient:
    """新门户异步客户端；注入的 HTTP 客户端由调用者关闭。"""

    def __init__(
        self, token: IPortalToken, *, client: httpx.AsyncClient | None = None
    ) -> None:
        self._token = token
        self._client = client if client is not None else httpx.AsyncClient(timeout=30.0)
        self._owns_client = client is None

    async def _text(self, path: str, **kwargs) -> str:
        response = await request(
            self._client, path, headers=dict(self._token.headers), **kwargs
        )
        return response.text

    async def get_account_info(self) -> AccountInfo:
        return parse.account_info(await self._text("/personal/frontend/data/info"))

    async def get_personal_data(self) -> PersonalData:
        types = parse.personal_data_query_ids(
            await self._text(
                "/personal/frontend/data/items", params={"type": "personal_data"}
            )
        )
        tasks = [
            asyncio.create_task(
                self._text("/personal/frontend/data/detail", params={"id": id})
            )
            for _, id in types
        ]
        try:
            bodies = await asyncio.gather(*tasks)
        except BaseException:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            raise
        return parse.personal_data((key, body) for (key, _), body in zip(types, bodies))

    async def get_term_info(self, time: datetime) -> TermInfo:
        """与 Rust 一样，将不带时区的时间视为 UTC 后生成秒级时间戳。"""
        if not isinstance(time, datetime) or time.utcoffset() is not None:
            raise ValueError("time 必须是不带时区的 datetime，按 UTC 解释")
        timestamp = calendar.timegm(time.timetuple())
        return parse.term_info(
            await self._text(
                "/hnu/frontend/term", params={"current_time": str(timestamp)}
            )
        )

    async def get_card_info(self) -> CardInfo:
        return parse.card_info(await self._text("/hnu/frontend/user/card-balance"))

    async def get_card_transaction_records(
        self,
        account: str,
        start: date,
        end: date,
        page_size: int,
        page: int,
    ) -> CardTransactionDetail:
        if not isinstance(account, str):
            raise ValueError("account 必须为校园卡账号字符串")
        if type(start) is not date or type(end) is not date or start > end:
            raise ValueError("start/end 必须为 date，且开始日期不晚于结束日期")
        _u32(page_size)
        _u32(page)
        body = await self._text(
            "/hnu/frontend/user/card-details",
            params={
                "query_start": start.isoformat(),
                "query_end": end.isoformat(),
                "page_size": str(page_size),
                "page": str(page),
                "account": account,
            },
        )
        return parse.card_transaction_records(body)

    async def get_apply_list(self, page: int, page_size: int) -> ApplyList:
        _u32(page)
        _u32(page_size)
        return parse.apply_list(
            await self._text(
                "/personal/frontend/task/apply",
                params={
                    "type": "all",
                    "page": str(page),
                    "pageSize": str(page_size),
                },
            )
        )

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def __aenter__(self) -> "IPortalClient":
        return self

    async def __aexit__(self, *exc) -> None:
        await self.aclose()
