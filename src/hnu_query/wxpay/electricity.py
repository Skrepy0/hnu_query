from hnu_query.xgxt.dormitory import Dormitory

from .client import WxpayClient

__all__ = ["get_electricity"]


async def get_electricity(dormitory: Dormitory) -> str:
    async with WxpayClient() as client:
        return await client.get_electricity(dormitory)
