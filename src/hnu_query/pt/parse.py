"""与 Rust pt 模块对应的纯解析函数。"""

import json
import math
from datetime import datetime
from typing import TypeVar

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .exceptions import PtParseError
from .models import CardHistory, CardHistoryItem, CardInfo


class _Raw(BaseModel):
    model_config = ConfigDict(strict=True, allow_inf_nan=False)


class _CardInfo(_Raw):
    account: int = Field(ge=0, le=2**32 - 1)
    balance: str


class _CardHistoryItem(_Raw):
    fTranAmt: str
    jndatetime: str
    effectdate: str
    jourName: str
    usedcardnum: int = Field(ge=0, le=2**32 - 1)
    nowAmt: str
    sysname1: str | None = None
    tranname: str


class _CardHistory(_Raw):
    amt: float
    count: float
    webTrjnDTO: list[_CardHistoryItem] | None = None


class _UnreadEmail(_Raw):
    unReadCount: int | None = Field(default=None, ge=0, le=2**32 - 1)


T = TypeVar("T", bound=BaseModel)


def _data(body: str):
    try:
        value = json.loads(body)
        if not isinstance(value, dict):
            raise TypeError("应为对象")
        return value["data"]
    except (ValueError, TypeError, KeyError) as exc:
        raise PtParseError("个人门户响应缺少有效 data 字段") from exc


def _validate(model: type[T], data) -> T:
    try:
        return model.model_validate(data)
    except ValidationError as exc:
        raise PtParseError("个人门户响应字段格式错误") from exc


def _amount(value: str) -> float:
    try:
        if value != value.strip() or "_" in value:
            raise ValueError("金额格式错误")
        amount = float(value)
        if not math.isfinite(amount):
            raise ValueError("金额不是有限数")
        return amount
    except ValueError as exc:
        raise PtParseError("无法解析校园卡金额") from exc


def csrf_token(body: str) -> str:
    token = _data(body)
    if not isinstance(token, str):
        raise PtParseError("无法解析个人门户 CSRF 令牌")
    return token


def card_info(body: str) -> CardInfo:
    raw = _validate(_CardInfo, _data(body))
    return CardInfo(id=raw.account, balance=_amount(raw.balance) / 100.0)


def card_history(body: str) -> CardHistory:
    raw = _validate(_CardHistory, _data(body))
    items = []
    for row in raw.webTrjnDTO or []:
        try:
            date_time = datetime.strptime(row.effectdate, "%Y/%m/%d %H:%M:%S")
            journal_time = datetime.strptime(row.jndatetime, "%Y/%m/%d %H:%M:%S")
        except ValueError as exc:
            raise PtParseError("无法解析校园卡交易或记账时间") from exc
        balance = row.nowAmt.strip().replace(",", "").replace(" ", "")
        items.append(
            CardHistoryItem(
                date_time=date_time,
                journal_time=journal_time,
                status=row.jourName,
                id=row.usedcardnum,
                now_balance=_amount(balance),
                amount=_amount(row.fTranAmt),
                location=row.sysname1.strip() if row.sysname1 is not None else None,
                name=row.tranname,
            )
        )
    # Rust f64 as u32：截断小数，负数归零，溢出饱和。
    count = min(max(int(raw.count), 0), 2**32 - 1)
    return CardHistory(total=raw.amt / 100.0, count=count, items=items)


def email_unread_count(body: str) -> int | None:
    return _validate(_UnreadEmail, _data(body)).unReadCount
