# 可信电子凭证

[文档目录](../README.md) · [通用用法](../usage.md)

Python 模块名为 `credential`，对应 Rust 的 `ca`。通过 CAS 登录后可查询成绩排名：

```python
from hnu_query.credential import acquire_by_cas_login, get_grade_rank

token = await acquire_by_cas_login(cas_token)
rank = await get_grade_rank(token)
print(rank.model_dump_json())
```

## 文件预览与下载

使用平台模板 ID 请求预览，从预览结果提取文件名后下载：

```python
from pathlib import Path

from hnu_query.credential import file, preview_file, preview_file_name

preview = await preview_file(token, template_id)
file_name = preview_file_name(preview)
content = await file(token, file_name)
Path("credential.pdf").write_bytes(content)
```

`template_id` 由调用方提供，应使用平台实际支持的模板 ID。
`preview_file` 返回 JSON 字符串，`preview_file_name` 负责解析文件名，`file` 返回文件字节。
平台返回的文件名可能包含相对目录；下载保留 `/` 分隔符，编码空格、`?`、`#` 等字符。

连续预览或下载可使用模块导出的 `CaClient` 复用连接；它提供 `preview_file(template_id)` 和 `file(file_name)`。
注入的 `httpx.AsyncClient` 由调用方关闭，库仍会显式携带凭证认证头。
`CaToken.from_headers_unchecked(headers)` 可恢复令牌，不验证会话。

文件下载支持最多十次 HTTPS 重定向；跨域下载不携带 `X-Access-Token`、Cookie 或 Authorization。
登录换票仅允许凭证域内跳转，遇到 CAS 登录跳转抛出 `CaLoginError`。
HTTP 401/403 等错误仍使用原有 `CaStatusError`，调用方可根据 `status_code` 决定重新登录。

模块导出 `CaError` 及 `CaNetworkError`、`CaStatusError`、`CaParseError`、`CaLoginError`。
差异审计及离线验证已完成。排名提取使用 pdfplumber，与 Rust 的 PDF 引擎不同；2026-10-25 已通过一次真实成绩凭证 PDF 的下载与排名解析，其他模板仍需分别验证。
具体约定见 [维护说明](../porting.md)。
