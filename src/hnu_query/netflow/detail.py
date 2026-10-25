from .client import NetflowClient
from .models import Detail, DetailItem
from .token import NetflowToken

__all__ = ["Detail", "DetailItem", "get_day_detail", "get_month_detail"]


async def get_month_detail(network_token: NetflowToken, year: int, month: int) -> Detail:
    async with NetflowClient(network_token) as client:
        return await client.get_month_detail(year, month)


async def get_day_detail(network_token: NetflowToken, year: int, month: int, day: int) -> Detail:
    async with NetflowClient(network_token) as client:
        return await client.get_day_detail(year, month, day)
