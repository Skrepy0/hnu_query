from .client import PtClient
from .token import PtToken

__all__ = ["get_unread_email_count"]


async def get_unread_email_count(pt_token: PtToken) -> int | None:
    async with PtClient(pt_token) as client:
        return await client.get_unread_email_count()
