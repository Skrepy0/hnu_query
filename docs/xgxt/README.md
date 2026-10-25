# 学工系统

[文档目录](../README.md) · [通用用法](../usage.md)

```python
from hnu_query.xgxt import XgxtClient, acquire_by_cas_login

token = await acquire_by_cas_login(cas_token)
async with XgxtClient(token) as client:
    person = await client.get_person_info()
    print(person.model_dump_json())
```

个人资料包含基本资料、在校信息、联系方式和可选的宿舍信息。

`class_` 对应 JSON 字段 `class`，学院、专业、班级等代码保留原值；可选字段可能为 `None`。
没有宿舍资料时 `person.dormitory` 为 `None`；有宿舍文字但无法识别时，模型中的 `park` 或 `build` 可能为 `None`。
调用 `dormitory.successfully_parsed()` 可检查园区和楼栋是否识别成功。

宿舍信息可用于 [宿舍电量](../wxpay/README.md) 查询。
