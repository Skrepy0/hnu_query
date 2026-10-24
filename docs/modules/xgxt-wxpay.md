# 学工资料与宿舍电量

[文档目录](../README.md) · [通用用法](../usage.md)

```python
from hnu_query.xgxt import XgxtClient, acquire_by_cas_login
from hnu_query.wxpay import get_electricity

token = await acquire_by_cas_login(cas_token)
async with XgxtClient(token) as client:
    person = await client.get_person_info()
    print(person.model_dump_json())

if person.dormitory is not None:
    print(await get_electricity(person.dormitory))
```

个人资料由多个请求合并；重复使用时建议缓存结果。
JSON 的 `class` 字段在 Python 中使用 `class_`，平台代码字段保留原值。
宿舍模型供 `hnu_query.wxpay.get_electricity(dormitory)` 使用，电量查询不需要登录。
调用前应从个人资料中确认宿舍信息完整，或使用宿舍模型工厂手动构造。

电量返回平台原始字符串，调用方应根据显示格式处理单位。
望麓桥部分楼栋需探测南北两侧；两侧均成功或均失败时无法唯一确定，抛出 `WxpayAmbiguityError`。
楼栋编码、特殊房间号及宿舍构造约定见 [维护说明](../porting.md)。
