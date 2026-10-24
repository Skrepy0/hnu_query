from datetime import datetime

from .client import IPortalClient
from .models import TermInfo, TermType
from .token import IPortalToken

__all__ = ["TermInfo", "TermType", "get_term_info"]


async def get_term_info(token: IPortalToken, time: datetime) -> TermInfo:
    async with IPortalClient(token) as client:
        return await client.get_term_info(time)
