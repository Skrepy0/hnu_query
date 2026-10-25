import calendar

import httpx

from . import parse
from ._http import request
from .models import Detail, OrderItem, ThisMonthInfo, UnlockStatus
from .token import NetflowToken


def _check_date(year: int, month: int, day: int = 1) -> None:
    if type(year) is not int or not 1 <= year <= 65535:
        raise ValueError("年份必须为 1 至 65535 的整数")
    if type(month) is not int or not 1 <= month <= 12:
        raise ValueError("月份必须为 1 至 12 的整数")
    if type(day) is not int or not 1 <= day <= calendar.monthrange(year, month)[1]:
        raise ValueError("日期在该年月中不存在")


class NetflowClient:
    """复用连接的异步流量客户端；调用方注入的 HTTP 客户端由调用方关闭。"""

    def __init__(self, token: NetflowToken, *, client: httpx.AsyncClient | None = None) -> None:
        self._token = token
        self._client = client if client is not None else httpx.AsyncClient(timeout=30.0)
        self._owns_client = client is None

    async def _text(self, path: str, **kwargs) -> str:
        response = await request(
            self._client, "GET", path, headers=dict(self._token.headers), **kwargs
        )
        return response.text

    async def get_month_detail(self, year: int, month: int) -> Detail:
        _check_date(year, month)
        return parse.detail(
            await self._text(
                "/api/v1/history/getfloatdetailbymonth",
                params={"month": f"{year}-{month:02}"},
            )
        )

    async def get_day_detail(self, year: int, month: int, day: int) -> Detail:
        _check_date(year, month, day)
        return parse.detail(
            await self._text(
                "/api/v1/history/getfloatdetailbyday",
                params={"day": f"{year}{month:02}{day:02}"},
            )
        )

    async def get_order(self) -> list[OrderItem]:
        return parse.order(await self._text("/api/v1/historyorder/getpagedlist"))

    async def get_overdue_payment(self) -> float:
        return parse.overdue_payment(await self._text("/api/v1/pay/getpayinfo"))

    async def get_this_month_info(self) -> ThisMonthInfo:
        return parse.this_month_info(await self._text("/api/v1/history/gettrafficinfobythismonth"))

    async def get_unlock_status(self) -> UnlockStatus:
        return parse.unlock_status(await self._text("/api/v1/account/getuserinfo"))

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def __aenter__(self) -> "NetflowClient":
        return self

    async def __aexit__(self, *exc) -> None:
        await self.aclose()
