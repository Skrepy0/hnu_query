# AI / MaaS 平台

[文档目录](../README.md) · [通用用法](../usage.md)

通过 CAS 登录，沿 DeepSeek OAuth 授权链到 MaaS 平台换取会话：

```python
from hnu_query.ai import AiClient, acquire_by_cas_login

token = await acquire_by_cas_login(cas_token)
async with AiClient(token) as client:
    tokens = await client.get_token_list()
    quota = await client.get_user_remaining_quota()
    for item in tokens:
        print(item.id, item.token_name)
    print(quota)
```

无 API Token 时返回空列表。名称可以重复，读取 key 和删除操作使用 ID：

| 方法 | 返回值 / 行为 |
| --- | --- |
| `get_token_list()` | `list[TokenInfo]`，每项含 `token_name` 和 `id` |
| `get_token_key(id)` | API key 字符串 |
| `create_token(name)` | 创建 API Token，成功返回 `None` |
| `delete_token(id)` | 删除指定 API Token，成功返回 `None` |
| `get_user_remaining_quota()` | 平台 `data.total_granted` 整数 |

这些方法也有同名模块函数，第一个参数为 `AiToken`。`create_token` 请求中的 `quota` 固定为
`2000000`；`get_user_remaining_quota()` 返回服务端的 `total_granted`。

`AiToken.from_headers_unchecked(headers)` 可恢复会话。API key 与会话令牌都应按凭据保存。

创建或删除失败抛出 `AiActionError`；API 登录失效抛出本模块的 `TokenExpired`。
CAS 会话失效则传递 `hnu_query.cas.TokenExpired`。

登录需要访问 CAS、`deepseek.hnu.edu.cn:5556` 和 `maas.nscc-cs.cn`。
