from .client import NetflowClient
from .models import UnlockStatus
from .token import NetflowToken

__all__ = ["UnlockStatus", "get_unlock_status"]


async def get_unlock_status(netflow_token: NetflowToken) -> UnlockStatus:
    async with NetflowClient(netflow_token) as client:
        return await client.get_unlock_status()
