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
楼栋及时间定义见 [教学楼](building.md)、[节次](time.md)。
课表星期以 1–7 表示，7 为周日，允许第 0 周。

令牌过期时抛出 `TokenExpired`。

## 空教室

```python
rooms = await client.get_empty_classroom(
    building_id="106",
    week=1,
    day=1,
    time=[1, 2],
    xn=2025,
    xq=1,
)
```

结果为所选大节均空闲的教室；`106` 是综合楼，完整 ID 见教学楼表。

## 排名选项

`get_rank(selection=(), range=Range.Major, data_source=DataSource.Total, display=Display.Max)`：

- `selection` 是 `(xn, xq)` 列表，空列表查询全部学期。
- `Range.Major` / `Range.Minor`：主修 / 辅修。
- `DataSource.Total` / `DataSource.Execution`：成绩总库 / 执行方案。
- `Display.Max` / `Display.Initial`：最高成绩 / 初修成绩。

这些枚举从 `hnu_query.hdjw` 导入，没有数据的排名分类可能返回 `None`。
