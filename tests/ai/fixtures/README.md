# 样本来源

四个 JSON 文件原样复制自 Rust 上游 [qnxg/hnu_query](https://github.com/qnxg/hnu_query)：

- `src/ai/token/test_data`：`tokens.json`、`key.json`、`apply-token.json`。
- `src/ai/user_info/test_data`：`user-info.json`。

遵循仓库 AGPL-3.0 许可证。解析断言与 Rust 测试一致；OAuth 登录响应由测试构造，不使用真实账号。
