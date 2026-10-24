# 校园网流量查询

[文档目录](../README.md) · [通用用法](../usage.md)

```python
from hnu_query.netflow import NetflowClient, acquire_by_cas_login

token = await acquire_by_cas_login(cas_token)
async with NetflowClient(token) as client:
    month = await client.get_month_detail(2025, 9)
    day = await client.get_day_detail(2025, 9, 1)
    orders = await client.get_order()
    debt = await client.get_overdue_payment()
    usage = await client.get_this_month_info()
    status = await client.get_unlock_status()
```

不同接口保留不同单位：明细流量为 KB，账单流量为字节，套餐流量为 GB。
带 `GB` 后缀的字段按平台格式解析。锁定状态使用 `UnlockStatus` 枚举。
列表不自动翻页。参数验证、错误响应和 Cookie 约定见 [维护说明](../porting.md)。
