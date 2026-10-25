# HNU Query（Python）

湖南大学校内系统异步查询库，由 Rust 项目 [qnxg/hnu_query](https://github.com/qnxg/hnu_query) 移植而来。

支持教务、体测、实验平台、校园网流量、门户、学工、研究生系统、CG、AI 平台和宿舍电量等查询。

## 安装

需要 Python 3.10+，在项目根目录执行：

```bash
pip install -e .
```

真实查询需连接湖南大学校园网或 VPN，并拥有相应系统权限。

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
- [字段约定](docs/fields.md) · [测试方法](docs/test.md)

## 开发

```bash
uv sync
uv run poe check
```

包含 lint、格式、类型检查和离线测试，详见 [测试方法](docs/test.md)。
真实请求测试通过 `.env` 配置，运行 `uv run --env-file .env poe test-live`。

## 许可证

[AGPL-3.0](LICENSE)
