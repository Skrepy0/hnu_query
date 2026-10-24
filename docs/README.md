# 使用指南

Python 版移植自 Rust 项目 [qnxg/hnu_query](https://github.com/qnxg/hnu_query)。
安装和完整入门示例见 [项目首页](../README.md)；登录流程和异常处理见 [通用用法](usage.md)。

| 模块 | 用途 | 指南 |
| --- | --- | --- |
| `cas` | 统一身份认证、票据、双因子验证 | [登录与认证](usage.md#统一身份认证) |
| `credential` | 可信电子凭证、文件下载、成绩排名 | [可信电子凭证](modules/credential.md) |
| `hdjw` | 课表、成绩、考试、排名、空教室 | [教务](modules/hdjw.md) |
| `gym` | 体测预约与成绩 | [体测](modules/gym.md) |
| `lab` | 学期、课程、实验安排与成绩 | [大物实验](modules/lab.md) |
| `netflow` | 流量、账单、欠费与锁定状态 | [校园网](modules/netflow.md) |
| `pt` | 校园卡、消费记录与未读邮件 | [个人门户](modules/pt.md) |
| `iportal` | 个人资料、学期、校园卡与办事申请 | [新门户](modules/iportal.md) |
| `xgxt`、`wxpay` | 学工资料、宿舍信息与电量 | [学工与电量](modules/xgxt-wxpay.md) |
| `yjsxt` | 研究生学期与课表 | [研究生系统](modules/yjsxt.md) |
| `cg` | 编程课程、作业、题目与页面 | [CG 编程平台](modules/cg.md) |

`ai` 尚未移植。各系统的登录方式、单位、分页和返回值差异见对应指南。

维护文档：[移植进度与剩余工作](migration.md) · [接口约定、兼容差异与测试来源](porting.md)。
