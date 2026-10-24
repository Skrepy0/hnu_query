# 样本来源

来源仓库：[qnxg/hnu_query](https://github.com/qnxg/hnu_query)（Rust）。以下路径相对于上游仓库根目录。

JSON 文件原样复制自 `src/lab/*/test_data`，遵循仓库 AGPL-3.0 许可证。
包含学期、课程、实验安排、实验成绩、成绩组成和评分结构样本。
解析断言对照 Rust 测试预期；Rust 未提供虚拟实验样本和登录响应，相关测试按其字段定义构造。
