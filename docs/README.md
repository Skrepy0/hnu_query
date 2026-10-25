# 使用指南

安装和入门示例见 [项目首页](../README.md)，公共调用方式见 [通用用法](usage.md)。

| 模块 | 用途 | 指南 |
| --- | --- | --- |
| `cas` | 统一身份认证、票据、双因子验证 | [登录与认证](cas/README.md) |
| `credential` | 可信电子凭证、文件下载、成绩排名 | [可信电子凭证](credential/README.md) |
| `hdjw` | 课表、成绩、考试、排名、空教室 | [教务](hdjw/README.md) |
| `gym` | 体测预约与成绩 | [体测](gym/README.md) |
| `lab` | 学期、课程、实验安排与成绩 | [大物实验](lab/README.md) |
| `netflow` | 流量、账单、欠费与锁定状态 | [校园网](netflow/README.md) |
| `pt` | 校园卡、消费记录与未读邮件 | [个人门户](pt/README.md) |
| `iportal` | 个人资料、学期、校园卡与办事申请 | [新门户](iportal/README.md) |
| `xgxt` | 学工个人资料与宿舍信息 | [学工系统](xgxt/README.md) |
| `wxpay` | 宿舍电量 | [宿舍电量](wxpay/README.md) |
| `yjsxt` | 研究生学期与课表 | [研究生系统](yjsxt/README.md) |
| `cg` | 编程课程、作业、题目与页面 | [CG 编程平台](cg/README.md) |
| `ai` | OAuth 登录、API Token 管理与配额 | [AI / MaaS 平台](ai/README.md) |

## 其他

- [字段约定](fields.md)：学年学期、时间、单位和空值。
- [缓存](cache.md)：模型序列化与令牌恢复。
- [测试](test.md)：离线检查和基于 `.env` 的真实请求测试。
- [项目结构](structure.md)：代码与测试目录。
