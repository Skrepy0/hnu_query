# HNU Query（Python）

湖南大学校内系统异步查询库，从 Rust 项目 [qnxg/hnu_query](https://github.com/qnxg/hnu_query) 逐模块移植到 Python，使用 httpx 和 Pydantic。

支持教务、体测、实验平台、校园网流量、门户、学工、研究生系统、CG 和宿舍电量等查询。全量移植仍在进行，详见 [移植进度](docs/migration.md)。

## 安装

需要 Python 3.10+，在项目根目录执行：

```bash
pip install -e .
```

真实查询需要湖南大学校园网或 VPN，以及相应系统账号。

## 快速开始

通过统一身份认证登录教务系统，查询成绩：

```python
import asyncio
import getpass

from hnu_query.cas import acquire_by_login
from hnu_query.hdjw import HdjwClient, acquire_by_cas_login


async def main():
    cas_token = await acquire_by_login(input("学号："), getpass.getpass("个人门户密码："))
    token = await acquire_by_cas_login(cas_token)
    async with HdjwClient(token) as client:
        # 学年起始年份、教务系统学期编号；按需修改。
        for grade in await client.get_grade(2025, 1):
            print(grade.model_dump_json())


asyncio.run(main())
```

## 文档

- [使用指南与模块目录](docs/README.md)
- [登录、异常处理与通用用法](docs/usage.md)
- [移植进度](docs/migration.md) · [开发与维护](docs/porting.md)

## 开发

```bash
uv sync --extra dev
uv run pytest
```

测试使用离线样本和模拟 HTTP 响应，尚未进行真实校园网联调。

## 许可证

[AGPL-3.0](LICENSE)
