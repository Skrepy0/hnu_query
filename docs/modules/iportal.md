# 新门户 iportal

[文档目录](../README.md) · [通用用法](../usage.md)

```python
from datetime import datetime, timezone

from hnu_query.iportal import IPortalClient, acquire_by_cas_login

token = await acquire_by_cas_login(cas_token)
async with IPortalClient(token) as client:
    account = await client.get_account_info()
    person = await client.get_personal_data()
    term = await client.get_term_info(datetime.now(timezone.utc))
    card = await client.get_card_info()
    applications = await client.get_apply_list(1, 20)
```

无时区的 `datetime` 按 UTC 解释，建议显式提供时区。
校园卡余额以元返回，交易记录的 `transaction_amount` 保留整数分。
`MoneyTransfer` 为同步转账记录，统计消费时需按业务含义过滤。

交易记录使用 `get_card_transaction_records`，其分页参数顺序为 `page_size, page`；
申请记录 `get_apply_list` 的顺序为 `page, page_size`。
查询收到 HTTP 302 时抛出模块的 `TokenExpired`。完整行为见 [维护说明](../porting.md)。
