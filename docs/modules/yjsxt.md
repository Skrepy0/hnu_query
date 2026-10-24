# 研究生系统

[文档目录](../README.md) · [通用用法](../usage.md)

```python
from hnu_query.yjsxt import YjsxtClient, acquire_by_cas_login

token = await acquire_by_cas_login(cas_token)
async with YjsxtClient(token) as client:
    semesters = await client.get_semester()
    if semesters:
        courses = await client.get_class_table(semesters[0].id)
```

选取学期 ID 后，调用 `get_class_table(semester_id)` 查询课表。
平台学期编号为 1 秋、2 春、3 夏、4 冬，与其他系统的编号不通用。
不同教师和教学阶段拆分为独立安排；没有节次的课程保留为无安排课程，安排字段为 `None`。

会话 ID 位于 URL 中，不是 Cookie。HTTP 302 表示会话过期，抛出模块的 `TokenExpired`。
无权限及解析行为见 [维护说明](../porting.md)。
