# 项目结构

[文档目录](README.md)

Python 包位于 `src/hnu_query`，按学校系统划分模块。

| 目录 | 内容 |
| --- | --- |
| `src/hnu_query/` | 按系统划分的异步查询接口 |
| `src/hnu_query/utils/` | Cookie、加密等共享辅助函数 |
| `tests/<模块>/` | 解析与模拟 HTTP 测试 |
| `tests/<模块>/fixtures/` | 响应样本及来源说明 |
| `tests/live/` | 从 `.env` 取参数的真实校园网请求测试 |
| `docs/<模块>/` | 模块使用指南和参考表 |
| `.local/` | pytest 临时文件和验证码图片，已被 Git 忽略 |
| `pyproject.toml` | 依赖组、Poe 任务、Ruff 和 mypy 配置 |
| `uv.lock` | uv 依赖锁文件 |
| `.env.example` | 真实请求测试的环境变量模板 |

开发环境和检查命令见 [测试](test.md)。运行时使用 `pip install -e .` 仅安装库依赖；
参与开发时使用 `uv sync` 安装默认开发依赖组。

## 模块内的常见文件

| 文件 | 职责 |
| --- | --- |
| `__init__.py` | 导出公开接口、模型和异常 |
| `login.py` | 登录、兑换票据或处理验证码 |
| `token.py` | 会话令牌及恢复方法 |
| `client.py` | 复用 HTTP 连接的查询客户端 |
| `models.py` | Pydantic 返回模型和枚举 |
| `parse.py` | 响应解析 |
| `exceptions.py` | 模块异常 |
| 其他功能文件 | 同名模块函数等查询入口 |

各模块按需包含这些文件。Python 的 `credential` 对应上游的 `ca`。
