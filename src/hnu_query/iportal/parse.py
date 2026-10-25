"""新门户纯解析函数，保留 Rust 的枚举映射、单位和回退行为。"""

import json
import math
import re
from datetime import datetime
from typing import TypeVar

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, ValidationError

from .exceptions import IPortalParseError
from .models import (
    AccountInfo,
    ApplyItem,
    ApplyList,
    ApplyStatus,
    CardInfo,
    CardTransactionDetail,
    Gender,
    PersonalData,
    TermInfo,
    TermType,
    TransactionRecord,
    TransactionType,
)

PERSONAL_KEYS = {
    "book.bookNum",
    "mail.unread",
    "card.balance",
    "statistic.lastLoginTime",
    "net.used",
}


class _Raw(BaseModel):
    model_config = ConfigDict(strict=True, allow_inf_nan=False)


class _Account(_Raw):
    uid: str
    name: str
    xgh: str
    identity: str
    identity_id: str
    sex: int = Field(ge=0, le=255)
    depart: str
    avatar: str


class _PersonalType(_Raw):
    key: str
    id: str


class _PersonalItem(_Raw):
    value: str | int | float
    unit: str | None = None
    name: str = Field(validation_alias=AliasChoices("name", "title"))
    email: str | None = None


class _Term(_Raw):
    start_date: str
    end_date: str
    dsc: str
    term: str
    year: str
    week: int = Field(ge=0, le=65535)


class _Card(_Raw):
    account: str
    balance: float


class _Transaction(_Raw):
    mercname: str
    mercacc: str
    occtime: str
    sign_tranamt: str
    trancode: str


class _Apply(_Raw):
    id: int = Field(ge=0, le=2**32 - 1)
    apps_id: int = Field(ge=-(2**31), le=2**31 - 1)
    app_name: str
    name: str
    creator: int = Field(ge=-(2**31), le=2**31 - 1)
    number: str
    inst_created: str
    inst_finished: str | None = None
    inst_status: int = Field(ge=-128, le=127)
    percent: int = Field(ge=0, le=255)
    created: str
    updated: str
    department_name: str
    department_id: int = Field(ge=-(2**31), le=2**31 - 1)
    department_sn: str
    form_url_view: str
    form_mobile_url_view: str
    process_pic_url: str
    process_log_url: str
    custom_status: str
    del_uid: int = Field(ge=-(2**31), le=2**31 - 1)
    del_time: str | None = None
    third_id: int = Field(ge=-(2**31), le=2**31 - 1)
    third_app_id: str
    third_app_name: str
    third_inst_id: str
    third_inst_name: str
    third_name: str


T = TypeVar("T", bound=BaseModel)


def iportal_jsondata_precheck(body: str):
    try:
        value = json.loads(body)
    except ValueError as exc:
        raise IPortalParseError("新门户响应不是有效 JSON") from exc
    if (
        not isinstance(value, dict)
        or type(value.get("e")) is not int
        or not -(2**63) <= value["e"] < 2**63
    ):
        raise IPortalParseError("无法解析新门户 e 字段")
    if value["e"] != 0:
        message = value.get("m")
        raise IPortalParseError(
            f"新门户返回业务错误：{message if isinstance(message, str) else '未知错误'}"
        )
    if "d" not in value:
        raise IPortalParseError("新门户响应缺少 d 字段")
    return value["d"]


def _field(data, key: str, kind: type):
    if not isinstance(data, dict) or type(data.get(key)) is not kind:
        raise IPortalParseError(f"无法解析新门户 {key} 字段")
    return data[key]


def _validate(model: type[T], data) -> T:
    try:
        return model.model_validate(data)
    except ValidationError as exc:
        raise IPortalParseError("新门户响应字段格式错误") from exc


def _integer(text: str, minimum: int, maximum: int) -> int:
    pattern = r"\+?[0-9]+" if minimum == 0 else r"[+-]?[0-9]+"
    try:
        if re.fullmatch(pattern, text) is None:
            raise ValueError("整数格式错误")
        value = int(text)
        if not minimum <= value <= maximum:
            raise ValueError("整数超出范围")
        return value
    except ValueError as exc:
        raise IPortalParseError("新门户整数格式错误或超出范围") from exc


def _datetime(value: str, pattern: str = "%Y-%m-%d %H:%M:%S") -> datetime:
    try:
        return datetime.strptime(value, pattern)
    except ValueError as exc:
        raise IPortalParseError("无法解析新门户日期时间") from exc


def _float(text: str, *, finite: bool = True) -> float:
    try:
        if text != text.strip() or "_" in text:
            raise ValueError("数字格式错误")
        value = float(text)
        if finite and not math.isfinite(value):
            raise ValueError("数字不是有限数")
        return value
    except ValueError as exc:
        raise IPortalParseError("无法解析新门户数值") from exc


def account_info(body: str) -> AccountInfo:
    data = iportal_jsondata_precheck(body)
    raw = _validate(_Account, _field(data, "info", dict))
    genders = {1: Gender.Male, 2: Gender.Female}
    if raw.sex not in genders:
        raise IPortalParseError("未知性别代码")
    return AccountInfo(
        uid=raw.uid,
        name=raw.name,
        id=raw.xgh,
        identity=raw.identity,
        identity_id=_integer(raw.identity_id, 0, 2**64 - 1),
        gender=genders[raw.sex],
        depart=raw.depart,
        avatar=raw.avatar,
    )


def personal_data_query_ids(body: str) -> list[tuple[str, str]]:
    data = iportal_jsondata_precheck(body)
    result = []
    for item in _field(data, "data", list):
        raw = _validate(_PersonalType, item)
        if raw.key not in PERSONAL_KEYS:
            raise IPortalParseError("未知个人数据类型")
        result.append((raw.key, raw.id))
    return result


def personal_data_single(body: str) -> _PersonalItem:
    data = iportal_jsondata_precheck(body)
    return _validate(_PersonalItem, _field(data, "data", dict))


def net_convert_to_byte(value: float, unit: str | None) -> int:
    factor = {
        "G": 1024**3,
        "GB": 1024**3,
        "M": 1024**2,
        "MB": 1024**2,
        "K": 1024,
        "KB": 1024,
    }.get((unit or "").strip().upper(), 1)
    value *= factor
    if math.isnan(value) or value <= 0:
        return 0
    if math.isinf(value) or value >= 2**64 - 1:
        return 2**64 - 1
    return int(value)


def personal_data(items) -> PersonalData:
    result = PersonalData()
    for key, body in items:
        item = personal_data_single(body)
        value = str(item.value)
        if key == "book.bookNum":
            result.lib_borrow = _integer(value, 0, 2**32 - 1)
        elif key == "mail.unread":
            result.email = item.email
            result.mail_unread = _integer(value, 0, 2**32 - 1)
        elif key == "card.balance":
            result.balance = _float(value)
        elif key == "statistic.lastLoginTime":
            try:
                result.last_login_time = _datetime(value)
            except IPortalParseError:
                pass
        elif key == "net.used":
            try:
                used = _float(value, finite=False)
            except IPortalParseError:
                used = 0.0
            result.net_used = net_convert_to_byte(used, item.unit)
        else:
            raise IPortalParseError("未知个人数据类型")
    return result


def term_info(body: str) -> TermInfo:
    raw = _validate(_Term, iportal_jsondata_precheck(body))
    terms = {
        "1": TermType.Autumn,
        "2": TermType.WinterVacation,
        "3": TermType.Spring,
        "4": TermType.SummerVacation,
    }
    if raw.term not in terms:
        raise IPortalParseError("未知学期类型")
    return TermInfo(
        start_date=_datetime(raw.start_date + " 00:00:00"),
        end_date=_datetime(raw.end_date + " 00:00:00"),
        term=terms[raw.term],
        year=raw.year,
        week=raw.week,
    )


def card_info(body: str) -> CardInfo:
    raw = _validate(_Card, iportal_jsondata_precheck(body))
    return CardInfo(account=raw.account, balance=raw.balance)


def card_transaction_records(body: str) -> CardTransactionDetail:
    data = iportal_jsondata_precheck(body)
    next_page = _integer(_field(data, "nextpage", str), 0, 2**32 - 1)
    count = _integer(_field(data, "rowcount", str), 0, 2**32 - 1)
    types = {
        15: TransactionType.Consumption,
        16: TransactionType.Recharge,
        17: TransactionType.Benefit,
        22: TransactionType.MoneyTransfer,
        6: TransactionType.EAccountOpening,
        1: TransactionType.HolderAccountOpening,
        99: TransactionType.QRCodeConsumption,
        27: TransactionType.Withholding,
    }
    records = []
    for item in _field(data, "total", list):
        raw = _validate(_Transaction, item)
        code = _integer(raw.trancode, 0, 2**32 - 1)
        if code not in types:
            raise IPortalParseError("未知校园卡交易类型")
        if not re.fullmatch(r"[0-9]{14}", raw.occtime):
            raise IPortalParseError("校园卡交易时间必须为 14 位数字")
        records.append(
            TransactionRecord(
                merchant_name=raw.mercname,
                merchant_account=_integer(raw.mercacc, 0, 2**64 - 1),
                pay_time=_datetime(raw.occtime, "%Y%m%d%H%M%S"),
                transaction_amount=_integer(raw.sign_tranamt, -(2**63), 2**63 - 1),
                transaction_type=types[code],
            )
        )
    return CardTransactionDetail(has_next_page=next_page != 0, total_count=count, records=records)


def apply_list(body: str) -> ApplyList:
    data = iportal_jsondata_precheck(body)
    total = _field(data, "total", int)
    if not 0 <= total < 2**32:
        raise IPortalParseError("申请记录总数超出范围")
    statuses = {
        0: ApplyStatus.Pending,
        1: ApplyStatus.Processing,
        2: ApplyStatus.Completed,
    }
    items = []
    for item in _field(data, "list", list):
        raw = _validate(_Apply, item)
        if raw.inst_status not in statuses:
            raise IPortalParseError("未知申请状态代码")
        items.append(
            ApplyItem(
                id=raw.id,
                app_name=raw.app_name,
                creator_name=raw.name,
                creator_department=raw.department_name,
                created=_datetime(raw.created),
                finished=_datetime(raw.inst_finished) if raw.inst_finished is not None else None,
                status=statuses[raw.inst_status],
            )
        )
    return ApplyList(total=total, list=items)
