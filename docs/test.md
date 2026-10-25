# 测试

[文档目录](README.md)

## 离线测试

在项目根目录通过 uv 安装依赖并运行全部检查：

```bash
uv sync
uv run poe check
```

开发依赖位于 `pyproject.toml` 的 `dependency-groups.dev`，`uv sync` 会默认安装。

`poe check` 按顺序执行以下任务，任一步失败都会停止：

| 命令 | 检查内容 |
| --- | --- |
| `uv run poe lint` | Ruff lint |
| `uv run poe fmt-check` | Ruff 格式检查，不修改文件 |
| `uv run poe typecheck` | mypy 检查 `src` |
| `uv run poe test` | 全部离线 pytest 测试 |

格式化代码用 `uv run poe format`；单独测试教务模块用 `uv run pytest tests/hdjw`。

测试使用静态响应样本与模拟 HTTP，不需要账号、校园网、Rust 工具链或本地 Rust 目录。
样本放在 `tests/<模块>/fixtures`，其中的 README 说明来源。
离线测试覆盖请求和解析行为，不保证线上接口、账号权限或平台当前状态不发生变化。

## 真实请求测试

复制配置模板，填写本机 `.env` 后运行：

```bash
cp .env.example .env
uv run --env-file .env poe test-live
```

PowerShell 可用 `Copy-Item .env.example .env`。`.env` 已被 Git 忽略。运行前需连接校园网或 VPN。
`poe check` 会排除 `live` 测试。

可按 pytest 节点选择单个平台，例如：

```bash
uv run --env-file .env pytest -m live -s tests/live/test_systems.py::test_hdjw
uv run --env-file .env pytest -m live -s tests/live/test_systems.py::test_cg
```

CAS 双因素认证会在终端询问短信验证码。实验平台和 CG 的验证码图片保存在
`TEST_CG_CAPTCHA_DIR`（默认 `.local`），识别后在终端输入。

| 模块 | 检查范围 |
| --- | --- |
| `cas` | 统一身份认证登录 |
| `hdjw` | 教务成绩 |
| `credential` | 本科主修成绩排名凭证 |
| `gym` | 体测成绩 |
| `lab` | 实验平台学期列表 |
| `netflow` | 本月流量信息 |
| `pt` | 校园卡资料 |
| `iportal` | 账号资料 |
| `xgxt` | 学工个人资料 |
| `wxpay` | 宿舍电量 |
| `cg` | 课程列表 |

这些用例只覆盖表中的查询，不代表模块的全部接口都已在线验证。

## 代理和直连

真实请求测试默认直连（`TEST_DIRECT=true`），测试期间设置 `NO_PROXY=*`，结束后自动恢复。
这样可避免系统代理把请求转到 WebVPN 验证页。
需要代理才能访问校园服务时，在 `.env` 中设置 `TEST_DIRECT=false`，沿用 HTTPX 的代理设置。
此配置仅影响真实请求测试；库本身仍使用调用方的网络配置。

pytest 只在终端报告结果，不保存接口响应。
