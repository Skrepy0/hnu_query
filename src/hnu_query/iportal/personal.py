from .client import IPortalClient
from .models import PersonalData
from .token import IPortalToken

__all__ = ["PersonalData", "get_personal_data"]


async def get_personal_data(token: IPortalToken) -> PersonalData:
    async with IPortalClient(token) as client:
        return await client.get_personal_data()
