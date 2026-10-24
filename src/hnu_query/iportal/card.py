from datetime import date

from .client import IPortalClient
from .models import CardInfo, CardTransactionDetail, TransactionRecord, TransactionType
from .token import IPortalToken

__all__ = [
    "CardInfo",
    "CardTransactionDetail",
    "TransactionRecord",
    "TransactionType",
    "get_card_info",
    "get_card_transaction_records",
]


async def get_card_info(token: IPortalToken) -> CardInfo:
    async with IPortalClient(token) as client:
        return await client.get_card_info()


async def get_card_transaction_records(
    token: IPortalToken,
    account: str,
    start: date,
    end: date,
    page_size: int,
    page: int,
) -> CardTransactionDetail:
    async with IPortalClient(token) as client:
        return await client.get_card_transaction_records(
            account, start, end, page_size, page
        )
