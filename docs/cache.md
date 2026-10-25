# 缓存

[文档目录](README.md)

库不缓存查询结果或令牌，缓存策略由调用方决定。

## 查询结果

Pydantic 模型支持字典与 JSON 序列化。以教务成绩为例，`grade` 是 `get_grade()` 返回的一项：

```python
from hnu_query.hdjw import Grade

payload = grade.model_dump_json()
restored = Grade.model_validate_json(payload)
```

`model_dump()` 返回字典；需要可直接写入 JSON 的日期等字段时使用 `model_dump(mode="json")`。
列表逐项序列化，可空结果需保留 `None` 的含义。

## 会话令牌

多数令牌可保存 `dict(token.headers)`，再用对应的 `from_headers_unchecked` 恢复：

```python
from hnu_query.hdjw import HdjwToken

headers = dict(hdjw_token.headers)
restored_token = HdjwToken.from_headers_unchecked(headers)
```

以下令牌需要不同字段：

| 令牌 | 恢复方法 |
| --- | --- |
| `CasToken` | `from_cookie_unchecked(cookie, stu_id)` |
| `LabToken` | `from_headers_unchecked(headers, stu_id)` |
| `YjsxtToken` | `from_id_unchecked(id)` |

这些方法只恢复本地状态，不验证令牌是否有效。缓存文件应按凭据管理，令牌失效后重新登录。
