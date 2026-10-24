# 样本来源

来源仓库：[qnxg/hnu_query](https://github.com/qnxg/hnu_query)（Rust）。以下路径相对于上游仓库根目录。

五个 JSON 文件原样复制自 `src/pt/*/test_data`，遵循仓库 AGPL-3.0 许可证。
包含校园卡信息、消费和充值记录、已绑定及未绑定邮箱的响应。
解析断言对照 Rust 的测试预期；登录响应及 CSRF 响应按 Rust 的处理规则构造。
