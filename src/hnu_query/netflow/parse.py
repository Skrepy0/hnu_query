"""与 Rust netflow 对齐的纯解析函数。"""

import json
from datetime import datetime
from typing import TypeVar

from pydantic import BaseModel, ConfigDict, ValidationError

from .exceptions import NetflowParseError
from .models import Detail, DetailItem, OrderItem, ThisMonthInfo, UnlockStatus


class _Raw(BaseModel):
    model_config = ConfigDict(strict=True, allow_inf_nan=False)


class _DetailItem(_Raw):
    App: str
    Download: float
    Per: float
    Total: float
    Upload: float


class _Detail(_Raw):
    AllDownload: float
    AllTotal: float
    AllUpload: float
    FloatDetailList: list[_DetailItem]


class _OrderItem(_Raw):
    Download: float | None = None
    Month: str
    RealOverTraffic: float
    ShouldPay: float
    UpdateTime: str
    Upload: float | None = None


class _PayInfo(_Raw):
    Total: float


class _ThisMonth(_Raw):
    allBasePackageAmount: float
    allExtendPackageAmount: float
    allTraffic: str
    basePackageUsed: float
    basePackageUsedPer: float
    downloadTraffic: str
    extendPackageUsed: float
    extendPackageUsedPer: float
    surplusBasePackage: float
    surplusExtendPackage: float
    uploadTraffic: str


T = TypeVar("T", bound=BaseModel)


def _data(body: str):
    try:
        value = json.loads(body)
        if not isinstance(value, dict):
            raise TypeError("应为对象")
        return value["data"]
    except (ValueError, TypeError, KeyError) as exc:
        raise NetflowParseError("流量响应不是有效的 data 对象") from exc


def _validate(model: type[T], data) -> T:
    try:
        return model.model_validate(data)
    except ValidationError as exc:
        raise NetflowParseError("校园网流量响应字段不正确") from exc


def detail(body: str) -> Detail:
    raw = _validate(_Detail, _data(body))
    return Detail(
        total=raw.AllTotal,
        upload=raw.AllUpload,
        download=raw.AllDownload,
        items=[
            DetailItem(
                app=row.App,
                total=row.Total,
                download=row.Download,
                upload=row.Upload,
                percentage=row.Per,
            )
            for row in raw.FloatDetailList
        ],
    )


def _usage_bytes(value: float | None) -> int:
    # Rust f64 as usize：缺失为 0，小数截断，负数和溢出饱和到 64 位无符号边界。
    if value is None:
        return 0
    return min(max(int(value), 0), 2**64 - 1)


def order(body: str) -> list[OrderItem]:
    data = _data(body)
    if not isinstance(data, list):
        raise NetflowParseError("流量账单 data 应为列表")
    result = []
    for item in data:
        raw = _validate(_OrderItem, item)
        try:
            updated = datetime.strptime(raw.UpdateTime, "%Y-%m-%d %H:%M:%S")
        except ValueError as exc:
            raise NetflowParseError("无法解析流量账单更新时间") from exc
        result.append(
            OrderItem(
                time=raw.Month,
                download_usage=_usage_bytes(raw.Download),
                upload_usage=_usage_bytes(raw.Upload),
                over_usage=raw.RealOverTraffic,
                should_pay=raw.ShouldPay,
                update_time=updated,
            )
        )
    return result


def overdue_payment(body: str) -> float:
    return _validate(_PayInfo, _data(body)).Total


def _gb(value: str) -> str:
    return value if value.endswith("GB") else value + "GB"


def this_month_info(body: str) -> ThisMonthInfo:
    raw = _validate(_ThisMonth, _data(body))
    return ThisMonthInfo(
        total_usage=_gb(raw.allTraffic),
        upload_usage=_gb(raw.uploadTraffic),
        download_usage=_gb(raw.downloadTraffic),
        base_package_amount=raw.allBasePackageAmount,
        base_package_usage=raw.basePackageUsed,
        base_package_usage_percentage=raw.basePackageUsedPer,
        base_package_surplus=raw.surplusBasePackage,
        extend_package_amount=raw.allExtendPackageAmount,
        extend_package_usage=raw.extendPackageUsed,
        extend_package_usage_percentage=raw.extendPackageUsedPer,
        extend_package_surplus=raw.surplusExtendPackage,
    )


def unlock_status(body: str) -> UnlockStatus:
    data = _data(body)
    if not isinstance(data, dict) or type(data.get("IsLocked")) is not int:
        raise NetflowParseError("无法解析流量锁定状态")
    value = data["IsLocked"]
    if not -(2**63) <= value < 2**63:
        raise NetflowParseError("流量锁定状态超出整数范围")
    return {0: UnlockStatus.Unlocked, 1: UnlockStatus.Locked}.get(
        value, UnlockStatus.Unknown
    )
