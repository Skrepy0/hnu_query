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

以上片段放在异步函数内运行，`cas_token` 的获取方式见通用用法。
无 API Token 时返回空列表。名称可以重复，读取 key 和删除操作使用 ID：

| 方法 | 返回值 / 行为 |
| --- | --- |
| `get_token_list()` | `list[TokenInfo]`，每项含 `token_name` 和 `id` |
| `get_token_key(id)` | API key 字符串 |
| `create_token(name)` | 创建 API Token，成功返回 `None` |
| `delete_token(id)` | 删除指定 API Token，成功返回 `None` |
| `get_user_remaining_quota()` | 平台 `data.total_granted` 整数 |

五个方法也提供同名模块函数，第一个参数为 `AiToken`。
`create_token` 沿用上游请求体中的固定 `quota=2000000`，不表示服务器一定按该值分配额度。
配额函数沿用 Rust 名称，但读取的是 `total_granted`，未根据使用量自行计算剩余额度。

`AiToken` 可通过 `from_headers_unchecked(headers)` 恢复，不验证会话有效性。
登录最多进行十次 OAuth GET 请求，跳转仅接受已知服务的 HTTPS 地址。
CAS 原始 Cookie 只发往 CAS，MaaS 令牌只保存 Bearer 与 MaaS API 可用 Cookie。
会话令牌与 API key 是两种凭据，读取 key 后请勿输出到日志或提交仓库。

异常包括 `AiNetworkError`、`AiStatusError`、`AiParseError`、`AiLoginError`、`AiActionError` 和 `TokenExpired`。
创建或删除响应为 `success=false` 时抛出 `AiActionError`。
API 请求发生登录跳转、401 或 403 时抛出 `TokenExpired`（403 也可能表示权限不足）；重新登录前应确认账号权限。
CAS 换票时的过期异常直接传递 `hnu_query.cas.TokenExpired`。

离线验证使用上游 JSON 样本和模拟 HTTP 响应。2026-10-25 已尝试真实联调，但本机无法连接
`deepseek.hnu.edu.cn:5556` 授权入口，尚未取得 Bearer Token 或验证真实配额接口。
MaaS 首页可访问，不等于 OAuth 授权入口可访问；具体探测范围见 [联调记录](../live-check.md)。
