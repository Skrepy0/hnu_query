from .client import IPortalClient
from .models import ApplyItem, ApplyList, ApplyStatus
from .token import IPortalToken

__all__ = ["ApplyItem", "ApplyList", "ApplyStatus", "get_apply_list"]


async def get_apply_list(token: IPortalToken, page: int, page_size: int) -> ApplyList:
    async with IPortalClient(token) as client:
        return await client.get_apply_list(page, page_size)
