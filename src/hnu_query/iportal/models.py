from datetime import datetime
from enum import Enum

from pydantic import BaseModel


class Gender(str, Enum):
    Male = "Male"
    Female = "Female"


class AccountInfo(BaseModel):
    uid: str
    name: str
    id: str
    identity: str
    identity_id: int
    gender: Gender
    depart: str
    avatar: str


class PersonalData(BaseModel):
    lib_borrow: int | None = None
    email: str | None = None
    mail_unread: int | None = None
    balance: float | None = None
    last_login_time: datetime | None = None
    net_used: int | None = None


class TermType(str, Enum):
    Autumn = "Autumn"
    Spring = "Spring"
    WinterVacation = "WinterVacation"
    SummerVacation = "SummerVacation"


class TermInfo(BaseModel):
    start_date: datetime
    end_date: datetime
    term: TermType
    year: str
    week: int


class CardInfo(BaseModel):
    """余额单位为元。"""

    account: str
    balance: float


class TransactionType(str, Enum):
    Consumption = "Consumption"
    QRCodeConsumption = "QRCodeConsumption"
    Recharge = "Recharge"
    MoneyTransfer = "MoneyTransfer"
    Benefit = "Benefit"
    EAccountOpening = "EAccountOpening"
    HolderAccountOpening = "HolderAccountOpening"
    Withholding = "Withholding"


class TransactionRecord(BaseModel):
    """交易金额为整数分；MoneyTransfer 只是余额同步，不是额外收支。"""

    merchant_name: str
    merchant_account: int
    pay_time: datetime
    transaction_amount: int
    transaction_type: TransactionType


class CardTransactionDetail(BaseModel):
    has_next_page: bool
    total_count: int
    records: list[TransactionRecord]


class ApplyStatus(str, Enum):
    Pending = "Pending"
    Processing = "Processing"
    Completed = "Completed"


class ApplyItem(BaseModel):
    id: int
    app_name: str
    creator_name: str
    creator_department: str
    created: datetime
    finished: datetime | None = None
    status: ApplyStatus


class ApplyList(BaseModel):
    total: int
    list: list[ApplyItem]
