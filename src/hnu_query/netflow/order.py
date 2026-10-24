from .client import NetflowClient
from .models import OrderItem
from .token import NetflowToken

__all__ = ["OrderItem", "get_order"]


async def get_order(netflow_token: NetflowToken) -> list[OrderItem]:
    async with NetflowClient(netflow_token) as client:
        return await client.get_order()
