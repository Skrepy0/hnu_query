# 样本来源

来源仓库：[qnxg/hnu_query](https://github.com/qnxg/hnu_query)（Rust）。以下路径相对于上游仓库根目录。

五个 JSON 文件原样复制自 `src/netflow/*/test_data`，遵循仓库 AGPL-3.0 许可证。
解析断言对照 Rust 的流量明细、账单、欠费、本月用量和锁定状态测试。
Rust 未提供日流量及登录样本，日流量使用与月流量相同的响应结构，登录响应在测试中构造。
