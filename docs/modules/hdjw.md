# 教务查询

[文档目录](../README.md) · [通用用法](../usage.md)

```python
from hnu_query.hdjw import HdjwClient, acquire_by_cas_login

token = await acquire_by_cas_login(cas_token)
async with HdjwClient(token) as client:
    grades = await client.get_grade(2025, 1)
    courses = await client.get_class_table(2025, 1)
    extra = await client.get_class_table_extra(2025, 1)
    exams = await client.get_exam_schedule(2025, 1)
    rank = await client.get_rank()
```

`xn` 为学年起始年份，`xq` 为教务系统学期编号。课表、成绩、考试沿用上游的第一页限制，页大小分别为 50、50、20，不自动翻页。
成绩详情用 `get_grade_detail(jx0404id)` 查询，需先确认成绩条目中存在对应 ID。
排名支持通过 `Range`、`DataSource`、`Display` 配置查询范围与统计口径。

`get_empty_classroom` 查询空教室，使用大节编号 1–5，与课表小节编号不同。
楼栋及时间定义见上游 [教学楼](https://github.com/qnxg/hnu_query/blob/main/docs/hdjw/building.md)、[节次](https://github.com/qnxg/hnu_query/blob/main/docs/hdjw/time.md)。
课表星期以 1–7 表示，7 为周日，允许第 0 周。

异常包括 `HdjwNetworkError`、`HdjwStatusError`、`HdjwParseError` 和 `TokenExpired`。
令牌过期的处理见通用用法；参数及解析约定见 [维护说明](../porting.md)。
