# 新门户 iportal

[文档目录](../README.md) · [通用用法](../usage.md)

```python
from datetime import datetime

from hnu_query.iportal import IPortalClient, acquire_by_cas_login

token = await acquire_by_cas_login(cas_token)
async with IPortalClient(token) as client:
    account = await client.get_account_info()
    person = await client.get_personal_data()
    term = await client.get_term_info(datetime(2026, 3, 10))
    card = await client.get_card_info()
    applications = await client.get_apply_list(1, 20)
```

`get_term_info()` 接受不带时区的 `datetime`，并按 UTC 解释。
校园卡余额以元返回，交易记录的 `transaction_amount` 保留整数分。
`MoneyTransfer` 为同步转账记录，统计消费时需按业务含义过滤。

交易记录使用 `get_card_transaction_records`，其分页参数顺序为 `page_size, page`；
申请记录 `get_apply_list` 的顺序为 `page, page_size`。
两种分页接口都不自动翻页，交易结果的 `has_next_page` 表示是否有后续页，申请结果的 `total` 为总条数。

交易记录方法的完整签名为 `get_card_transaction_records(account, start, end, page_size, page)`，
其中 `account` 为校园卡账号字符串，`start`、`end` 为 `datetime.date`，不是 `datetime`，且开始日期不能晚于结束日期。
