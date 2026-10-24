from .client import NetflowClient
from .token import NetflowToken

__all__ = ["get_overdue_payment"]


async def get_overdue_payment(netflow_token: NetflowToken) -> float:
    async with NetflowClient(netflow_token) as client:
        return await client.get_overdue_payment()
