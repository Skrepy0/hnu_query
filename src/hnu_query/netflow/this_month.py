from .client import NetflowClient
from .models import ThisMonthInfo
from .token import NetflowToken

__all__ = ["ThisMonthInfo", "get_this_month_info"]


async def get_this_month_info(netflow_token: NetflowToken) -> ThisMonthInfo:
    async with NetflowClient(netflow_token) as client:
        return await client.get_this_month_info()
