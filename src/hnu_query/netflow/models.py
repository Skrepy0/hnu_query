from datetime import datetime
from enum import Enum

from pydantic import BaseModel


class DetailItem(BaseModel):
    """应用流量明细，流量单位为 KB，percentage 为 0–1 比例。"""

    app: str
    total: float
    download: float
    upload: float
    percentage: float


class Detail(BaseModel):
    """流量明细，流量单位为 KB。"""

    total: float
    upload: float
    download: float
    items: list[DetailItem]


class OrderItem(BaseModel):
    """账单：download/upload_usage 为字节，over_usage 为 GB，should_pay 为元。"""

    time: str
    download_usage: int
    upload_usage: int
    over_usage: float
    should_pay: float
    update_time: datetime


class ThisMonthInfo(BaseModel):
    """本月流量：usage 字符串带 GB 后缀，套餐量为 GB，percentage 为 0–1 比例。"""

    total_usage: str
    upload_usage: str
    download_usage: str
    base_package_amount: float
    base_package_usage: float
    base_package_usage_percentage: float
    base_package_surplus: float
    extend_package_amount: float
    extend_package_usage: float
    extend_package_usage_percentage: float
    extend_package_surplus: float


class UnlockStatus(str, Enum):
    Locked = "Locked"
    Unlocked = "Unlocked"
    Unknown = "Unknown"
