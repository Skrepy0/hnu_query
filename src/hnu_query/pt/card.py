from .client import PtClient
from .models import CardHistory, CardHistoryItem, CardHistoryType, CardInfo
from .token import PtToken

__all__ = [
    "CardHistory",
    "CardHistoryItem",
    "CardHistoryType",
    "CardInfo",
    "get_card_history",
    "get_card_info",
]


async def get_card_info(pt_token: PtToken) -> CardInfo:
    async with PtClient(pt_token) as client:
        return await client.get_card_info()


async def get_card_history(
    pt_token: PtToken, year: int, month: int, history_type: CardHistoryType
) -> CardHistory:
    async with PtClient(pt_token) as client:
        return await client.get_card_history(year, month, history_type)
