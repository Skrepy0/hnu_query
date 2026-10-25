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

`preview_file` 返回 JSON 字符串，`preview_file_name` 负责解析文件名，`file` 返回文件字节。

连续请求可使用 `CaClient` 复用连接。
`CaToken.from_headers_unchecked(headers)` 可恢复令牌，不验证会话。

`get_grade_rank` 使用本科主修全部课程的固定成绩单模板，不统计辅修。
PDF 文本提取由 pdfplumber 完成；不含文本的扫描件或格式变化可能导致 `CaParseError`。
