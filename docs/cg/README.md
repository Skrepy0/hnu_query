# CG 编程平台

[文档目录](../README.md) · [通用用法](../usage.md)

CG 使用独立密码和图片验证码。`stu_id`、`cg_password` 由调用方提供：

```python
import asyncio
from pathlib import Path

from hnu_query.cg import CgClient, CgSession

session = await CgSession.new()
Path("cg-captcha.png").write_bytes(session.captcha_image)
code = await asyncio.to_thread(input, "打开 cg-captcha.png 后输入验证码：")
token = await session.login(stu_id, cg_password, code)

async with CgClient(token) as client:
    for course in await client.get_course_list() or []:
        for assignment in await client.get_assignment_list(course.id) or []:
            for problem in await client.get_problem_list(assignment.id) or []:
                print(problem.model_dump_json())
                # html = await client.get_problem_page(assignment.id, problem.index)
```

无课程、作业或题目时返回 `None`。`problem.index` 是作业内题目序号，获取页面应使用它；
`problem.id` 是题目 ID。`get_problem_page` 返回完整 HTML。

查询会切换服务端课程上下文，同一会话应按课程顺序查询。
验证码错误时重新创建 `CgSession` 获取图片，库不自动识别或重试登录。
密码和验证码错误分别抛出 `PasswordError`、`CaptchaError`，会话失效抛出 `TokenExpired`。
