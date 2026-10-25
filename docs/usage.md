# 通用用法

[文档目录](README.md) · [安装与快速开始](../README.md)

## 异步调用与登录

网络接口均为异步函数。模块文档中的代码片段应放在异步函数内运行。

多数系统先登录 [CAS](cas/README.md)，再调用自身模块的 `acquire_by_cas_login(cas_token)`。
系统令牌不能混用。实验平台和 CG 使用独立密码及验证码，宿舍电量无需认证。

## 函数与客户端

单次查询可直接调用模块函数：

```python
from hnu_query.hdjw import get_grade

grades = await get_grade(hdjw_token, 2025, 1)
```

连续查询时使用客户端复用连接：

```python
from hnu_query.hdjw import HdjwClient

async with HdjwClient(hdjw_token) as client:
    grades = await client.get_grade(2025, 1)
    exams = await client.get_exam_schedule(2025, 1)
```

退出上下文时会关闭客户端自行创建的连接。外部传入的 `httpx.AsyncClient` 仍由调用方关闭。

## 返回值

结构化结果使用 Pydantic 模型。`model_dump()` 返回字典，`model_dump_json()` 返回 JSON；
日期等字段可用 `model_dump(mode="json")` 转为 JSON 类型。

金额、流量单位和学期编号见 [字段约定](fields.md)。

## 异常处理

HTTP 异常可通过 `status_code` 读取状态码。多个模块都导出 `TokenExpired`，可用别名区分：

```python
from hnu_query.cas import TokenExpired as CasTokenExpired
from hnu_query.hdjw import HdjwClient, acquire_by_cas_login
from hnu_query.hdjw import TokenExpired as HdjwTokenExpired

try:
    hdjw_token = await acquire_by_cas_login(cas_token)
    async with HdjwClient(hdjw_token) as client:
        grades = await client.get_grade(2025, 1)
except HdjwTokenExpired:
    # CAS 尚有效时，重新兑换教务令牌并创建客户端。
    pass
except CasTokenExpired:
    # 需要重新登录 CAS 后，再兑换系统令牌。
    pass
```

没有统一失效码的系统可能在会话过期后抛出解析错误，具体见模块文档。
