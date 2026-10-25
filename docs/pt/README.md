# 个人门户

[文档目录](../README.md) · [通用用法](../usage.md)

```python
from hnu_query.pt import CardHistoryType, PtClient, acquire_by_cas_login

token = await acquire_by_cas_login(cas_token)
async with PtClient(token) as client:
    card = await client.get_card_info()
    history = await client.get_card_history(2025, 9, CardHistoryType.Consumption)
    unread = await client.get_unread_email_count()
```

`get_card_history(year, month, history_type)` 查询消费或充值记录，记录类型使用 `CardHistoryType.Consumption` 或 `CardHistoryType.Recharge`。
客户端自动获取、刷新 CSRF。查询沿用平台月末日期 `YYYYMM31` 和页大小 100000。

金额统一为元。未绑定邮箱返回 `None`，已绑定但无未读邮件返回 `0`。
平台没有统一的会话失效码，登录页也可能表现为解析错误。
