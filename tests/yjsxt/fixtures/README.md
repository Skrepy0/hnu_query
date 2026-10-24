# 样本来源

来源仓库：[qnxg/hnu_query](https://github.com/qnxg/hnu_query)（Rust）。以下路径相对于上游仓库根目录。

四个 JSON 文件原样复制自 `src/yjsxt/*/test_data`，遵循仓库 AGPL-3.0 许可证。
包含学期、普通课表、单双周课表和多教师阶段课表。解析断言对照 Rust 测试预期。
登录响应、无节次课程和其他边界条件在测试中构造。
