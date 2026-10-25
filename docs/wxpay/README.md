# 宿舍电量

[文档目录](../README.md) · [学工资料](../xgxt/README.md)

电量接口不需要登录，接收 `hnu_query.xgxt.Dormitory`。已有学工个人资料 `person` 时：

```python
from hnu_query.wxpay import get_electricity

dormitory = person.dormitory
if dormitory is not None and dormitory.successfully_parsed():
    balance = await get_electricity(dormitory)
    print(balance)
```

也可手工构造宿舍信息：

```python
from hnu_query.xgxt import Dormitory
from hnu_query.wxpay import get_electricity

dormitory = Dormitory.from_parsed_value("天马园区", "一区1栋", "101")
balance = await get_electricity(dormitory)
```

园区与楼栋需使用平台名称，例如“天马园区 / 一区1栋”或“德智园区 / 2栋”。

返回平台原始字符串，可能含“度”“元”等单位，不自动转换为数字。
房间号请保留前导零和字母；南校区 19 舍、德智部分楼栋由库按平台编码规则转换。

望麓桥 2、3 栋无法确定南北侧时抛出 `WxpayAmbiguityError`；园区或楼栋未识别时抛出 `ValueError`。
