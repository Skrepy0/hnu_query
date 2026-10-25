# 大物实验平台

[文档目录](../README.md) · [通用用法](../usage.md)

使用实验平台独立账号密码。验证码识别器接收图片字节，可为同步函数、异步函数，或提供异步 `resolve` 方法的对象。人工输入示例：

```python
import asyncio
from pathlib import Path

from hnu_query.lab import LabClient, acquire_by_login


async def resolve(image):
    Path("lab-captcha.jpg").write_bytes(image)
    return await asyncio.to_thread(input, "打开 lab-captcha.jpg 后输入验证码：")


token = await acquire_by_login(stu_id, lab_password, resolve)
async with LabClient(token) as client:
    semesters = await client.get_semester()
    if semesters:
        courses = await client.get_course_list(semesters[0].id)
    schedule = await client.get_lab_schedule()
    virtual_grades = await client.get_virtual_lab_grade()
```

`stu_id`、`lab_password` 由调用方提供。获取学期后使用其 ID 调用 `get_course_list(semester_id)`，
再使用 `get_lab_grade(course_id, semester_id)` 查询实验成绩。学期 ID 与教务学期编号不能互换。

`max_tried` 包含首次空验证码提交，只重试验证码错误。
普通列表页大小为 15，实验安排页大小为 200，不自动翻页。空白成绩返回 `None`。
