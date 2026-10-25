# 通用用法

[文档目录](README.md) · [安装与快速开始](../README.md)

## 统一身份认证

多数系统先获取 CAS 令牌，再通过各模块的 `acquire_by_cas_login` 换取系统令牌。
大物实验和 CG 使用独立密码及验证码，宿舍电量查询不需要认证。

```python
import getpass

from hnu_query.cas import acquire_by_login

cas_token = await acquire_by_login(input("学号："), getpass.getpass("个人门户密码："))
```

本文及模块指南中的 `await` 片段应放在异步函数内，通过 `asyncio.run(main())` 运行；
完整结构见项目首页。除另有说明，模块示例中的 `cas_token` 来自上述登录。

CAS 登录可能抛出 `PasswordError`、`AccountLocked`、`PasswordShouldChange` 或 `TFARequired`，
这些异常从 `hnu_query.cas` 导入。网络错误为 `CasNetworkError`，公钥解析或加密失败为 `CasParseError`，
异常 HTTP 状态为 `CasStatusError`，不完整登录响应为 `CasLoginError`。双因子验证流程如下：

1. 捕获 `TFARequired`，读取异常对象的 `tfa_token`。
2. 调用 `await tfa_token.send_sms()` 发送验证码。
3. 调用 `status, token = await tfa_token.verify(code)` 验证。
4. `success` 表示成功，可使用返回的 CAS 令牌；`code_error` 表示验证码错误；`expired` 表示验证会话过期，需重新登录。

验证码错误时，后续操作应使用返回的新 `TFAToken`，其中包含更新后的 `execution`。
`send_sms()` 返回 `success`、`valid` 或其他服务端原文；`valid` 表示已有验证码仍有效。
验证码验证仅在 HTTP 302 时返回成功，HTTP 4xx/5xx 抛出 `CasStatusError`，不会伪装成会话过期。

令牌包含会话凭据，不要提交到代码仓库或输出到日志。

## 查询与返回值

模块通常同时提供函数和客户端方法。模块函数的第一个参数为系统令牌；
连续查询时可用 `async with XxxClient(token) as client` 复用连接，具体名称见各模块指南。
客户端自行创建的 HTTP 连接会在退出上下文时关闭；注入的连接由调用者管理。

结构化结果使用 Pydantic 模型，可通过 `model_dump()` 获取字典，
或通过 `model_dump_json()` 序列化。列表、可空返回值及原始 HTML 等例外见模块说明。
各系统的金额、流量单位和学期编号不同，不宜直接混用。

## 异常处理

网络、HTTP 状态、解析及业务异常的具体类型见对应模块指南与导出接口。
例如教务模块提供 `HdjwNetworkError`、`HdjwStatusError`、`HdjwParseError` 和 `TokenExpired`。

出现 `hnu_query.hdjw.TokenExpired` 时重新兑换教务令牌。
如果兑换时抛出 `hnu_query.cas.TokenExpired`，则先重新登录 CAS。
多个模块都有同名异常，建议通过模块名引用，或在导入时使用别名。

## 本地开发

```bash
pip install -e ".[dev]"
python -m pytest
```

也可使用项目首页中的 uv 命令。测试使用离线样本和模拟请求，不需要账号、
校园网、Rust 工具链或本地 Rust 源码。验证限制见 [维护说明](porting.md)。
