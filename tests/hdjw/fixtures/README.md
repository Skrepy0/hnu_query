# 样本来源

来源仓库：[qnxg/hnu_query](https://github.com/qnxg/hnu_query)（Rust）。以下路径相对于上游仓库根目录。

本目录 JSON/HTML 文件原样复制自 `src/hdjw/*/test_data`，
用于与 Rust 解析器的测试预期对照，遵循仓库的 AGPL-3.0 许可证。

- `xskb_list_*.json`：课表，含混合课程、第 0 周及纯无课表学期。
- `cjcx_list.json` / `pscj_list.html`：课程成绩及分数组成。
- `xsksap_list.json`：考试安排。
- `cjpmcx_list.json`：全部/必修/核心课程排名。
- `jsjy_query2.json`：选择五个大节的空教室响应。
