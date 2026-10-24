from datetime import datetime
from enum import Enum

from pydantic import BaseModel


class CardInfo(BaseModel):
    """校园卡账号和余额，余额单位为元。"""

    id: int
    balance: float


class CardHistoryType(str, Enum):
    Recharge = "Recharge"
    Consumption = "Consumption"


class CardHistoryItem(BaseModel):
    """交易项；金额和余额单位为元，时间不带时区。"""

    date_time: datetime
    journal_time: datetime
    status: str
    id: int
    now_balance: float
    amount: float
    location: str | None = None
    name: str


class CardHistory(BaseModel):
    """校园卡交易记录：金额单位为元，充值为正、消费为负。"""

    total: float
    count: int
    items: list[CardHistoryItem]
