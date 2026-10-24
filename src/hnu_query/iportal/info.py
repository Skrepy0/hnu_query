from .client import IPortalClient
from .models import AccountInfo, Gender
from .token import IPortalToken

__all__ = ["AccountInfo", "Gender", "get_account_info"]


async def get_account_info(token: IPortalToken) -> AccountInfo:
    async with IPortalClient(token) as client:
        return await client.get_account_info()
