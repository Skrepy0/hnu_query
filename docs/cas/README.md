# 统一身份认证（CAS）

[文档目录](../README.md) · [通用用法](../usage.md)

```python
import getpass

from hnu_query.cas import acquire_by_login

stu_id = input("学号：")
password = getpass.getpass("个人门户密码：")
cas_token = await acquire_by_login(stu_id, password)
```

多数系统通过自身模块的 `acquire_by_cas_login(cas_token)` 换取独立令牌，CAS 令牌不能直接代替系统令牌。
实验平台与 CG 使用独立密码，宿舍电量不需要认证，见对应指南。

## 双因子验证

CAS 登录可能抛出 `TFARequired`，异常的 `tfa_token` 用于发送短信和验证：

```python
from hnu_query.cas import TFARequired, acquire_by_login

try:
    cas_token = await acquire_by_login(stu_id, password)
except TFARequired as exc:
    tfa = exc.tfa_token
    # 可先查看 tfa.phone，确认用于验证的绑定手机号。
    sms_status = await tfa.send_sms()
    if sms_status not in ("success", "valid"):
        raise RuntimeError("短信发送失败")
    code = input("短信验证码：")
    status, token = await tfa.verify(code)
    if status == "success":
        cas_token = token
    elif status == "code_error":
        tfa = token  # 后续用这个新令牌再次 verify，不能继续使用旧 execution。
    else:
        # 验证会话过期，需要重新执行 acquire_by_login。
        pass
```

`send_sms()` 返回 `success`（发送成功）、`valid`（现有验证码仍有效）或其他服务端原文。
`verify()` 返回 `("success", CasToken)`、`("code_error", TFAToken)` 或 `("expired", None)`。
HTTP 错误抛异常，不作为验证成功返回。

## 异常

| 异常 | 含义 |
| --- | --- |
| `PasswordError` | 用户名或密码错误 |
| `AccountLocked` | 账号因多次失败被锁定 |
| `PasswordShouldChange` | 需要先在个人门户修改密码 |
| `TFARequired` | 需要双因子验证 |
| `CasNetworkError` | 网络请求失败 |
| `CasStatusError` | 非预期 HTTP 状态 |
| `CasParseError` | 公钥响应或加密参数无效 |
| `CasLoginError` | 登录响应缺少必要信息 |
| `TokenExpired` | CAS 令牌失效，需重新登录 |

异常均从 `hnu_query.cas` 导入。

## 票据和恢复

各系统登录函数会自行处理票据。需要直接调用时，`get_ticket_url()` 返回回调 URL，
`get_sticket()` 返回 `(s_ticket, cookies)`。

已有会话可用 `CasToken.from_cookie_unchecked(cookie, stu_id)` 恢复；构造方法不验证有效性，见 [缓存](../cache.md)。
