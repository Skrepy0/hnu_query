# 体测查询

[文档目录](../README.md) · [通用用法](../usage.md)

```python
from hnu_query.gym import GymClient, acquire_by_cas_login

token = await acquire_by_cas_login(cas_token)
async with GymClient(token) as client:
    appointments = await client.get_appointment()
    grade = await client.get_grade(2025)
```

也可使用 `acquire_by_direct_login(stu_id, password)` 直接登录体测账号。
预约查询会逐项获取详情，保持列表顺序。预约状态保留平台编号 0–4。
成绩合并摘要与明细，部分项目含附加分，原始显示单位保留在成绩数据中。

`get_grade(xn)` 的 `xn` 为学年开始年份，见 [字段约定](../fields.md)。
