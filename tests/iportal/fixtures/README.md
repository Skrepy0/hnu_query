# 样本来源

来源仓库：[qnxg/hnu_query](https://github.com/qnxg/hnu_query)（Rust）。以下路径相对于上游仓库根目录。

JSON 文件原样复制自 `src/iportal/**/test_data`（包括个人数据的 id_data 子目录），
遵循仓库 AGPL-3.0 许可证。目录按 info、personal、term、card、task 分类，公共异常样本位于本目录。
测试断言对照 Rust 预期，登录响应和额外边界条件使用模拟数据。
