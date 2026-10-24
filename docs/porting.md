# 移植维护说明

[文档目录](README.md) · [移植进度](migration.md)

本文记录接口约定、兼容差异与离线验证方式，供维护者参考。
行为基准为 Rust 上游 [qnxg/hnu_query](https://github.com/qnxg/hnu_query)。

## 教务实现约定

- `HdjwToken.headers` 是不可变副本；repr 不输出 Cookie。
- `HdjwClient` 管理自己的连接，注入的 HTTP 客户端由调用者关闭。
- 模块函数保持 Rust 参数顺序，另提供同名客户端方法。
- 网络和解析异常分开；JSON `flag1=2` 和已知登录重定向抛出教务 `TokenExpired`。
- 登录依次预取 Cookie、向 CAS 请求票据、兑换票据、再次访问 SSO、访问目标页。
  Cookie 同名覆盖，支持相对重定向；目标页限定在教务域名。
- 课表按 `(week, day, place)` 合并节次；Python 额外排序，保证输出顺序稳定。
- 支持第 0 周、单双周、缺失教师、无课表课程和 `count=0` 不带 `data` 的响应。
- 成绩详情仅解析嵌入数据与列定义，不执行 JavaScript。
- 空教室使用响应中所选大节的列顺序判断占用；非法大节抛出 `ValueError`（对应 Rust 的 panic）。
- 课表、成绩、考试沿用 Rust 的第一页限制，不声称支持自动翻页。

## 体测实现约定

- 提供不可变 `GymToken`、可复用连接的 `GymClient` 和与 Rust 同名的模块函数。
- 支持 CAS `s_ticket` 登录和体测账号密码直接登录。CAS 跳转最多六次，合并同名 Cookie，
  支持相对 Location 与 URL 编码的票据；CAS Cookie 只发往 CAS 域。
- 预约先获取列表，再按 `class_id`、`class_time`、`test_time` 逐项查询详情，保留列表顺序。
- 成绩并发请求摘要和详情；请求失败或任务被取消时，先取消并等待另一个请求结束。
- `info` 包含“登录失效”时抛出体测 `TokenExpired`；其余响应要求整数 `status=1` 和 `data`。
- 保留 Rust 的摘要回退逻辑：显示值为 null 时使用详情加单位，非字符串显示值转为 `"0"`；
  等级颜色优先取摘要，摘要未提供时根据“不及格/缺项/肥胖/超重”推断红色。
- 保留长跑回退逻辑：详情秒数使用 u32 整数字符串解析；非整数（例如 `"273.0"`）按 0 处理。
  摘要已有显示值时优先使用摘要。长跑和引体向上/仰卧起坐项目得分加入额外分数。
- 未提供的报告描述、状态和类型默认“暂无”；视力字段完整保留。
- Python 登录成功但没有会话 Cookie 时抛出 `GymLoginError`，HTTP 非 2xx 抛出 `GymStatusError`。

## 大物实验平台实现约定

- 提供不可变 `LabToken(headers, stu_id)`、`LabClient` 和五个与 Rust 同名的查询函数。
- 密码使用 AES-128-ECB/PKCS7 和两次 Base64；加密结果与 Rust 测试向量一致。
  `cryptography` 从已有的间接依赖改为显式依赖。
- 验证码识别器接收图片字节并返回字符串；支持 Rust 风格的异步 `resolve` 对象，
  也支持同步或异步函数。不内置 OCR 服务，[实验平台指南](modules/lab.md)提供人工输入示例。
- 登录首次提交空验证码，仅 `RTNCode=-2` 重试；`max_tried` 包含首次提交，
  `max_tried=0` 直接抛出 `CaptchaError`。与 Rust 一样，最后一次验证码失败也调用识别器后退出。
- 密码错误、验证码耗尽、其他服务端拒绝分别抛出 `PasswordError`、`CaptchaError`、
  `OtherError`，继承 `LoginIssue`。其他错误消息保存在 `OtherError.message`。
- 合并登录响应和验证码响应的 Cookie，同名覆盖；空 Cookie 的登录成功响应视为错误。
- 学期支持 `-`、`_`、空格分隔；安排按日期部分与独立开始时间合并，不带时区。
- 实验成绩并发获取总分、明细和结构，通过实验 ID 与结构 ID 关联；失败或取消时收回其余任务。
  过滤未出分及地点含“虚拟”的实验，忽略空分数及无法关联的明细。
- 虚拟实验稳定按名称排序去重，同名保留第一条（包括尚未出分的第一条）。
- 保留 Rust 分页限制：课程、普通实验成绩、虚拟实验为第一页 15 条，安排为第一页 200 条。
  虚拟实验请求 `SemID=0`、`CourseID=0`，不额外承诺学期筛选能力。
- Rust 未定义统一的会话过期业务码，查询失败按网络、HTTP 或解析异常报告。
  Python 拒绝非 2xx 响应，避免把登录重定向误当作查询数据。

## 校园网流量实现约定

- 提供不可变 `NetflowToken`、可复用连接的 `NetflowClient` 和六个与 Rust 同名的查询函数。
- 复用 CAS `s_ticket` 获取流程，再向 `ll.hnu.edu.cn/login/validate` 发送 GET 请求，
  表单字段放在正文，保留 Rust 的 `s_ticket`、`login_id`、空 `password` 和空 `null` 字段。
  兑换请求携带 Rust 流程要求的合并 Cookie，不自动跟随响应跳转。
- 登录从 Set-Cookie 列表取第一条和最后一条，匹配 Rust 对多条 `.ASPXAUTH` 的处理；
  仅一条 Cookie 时同样重复首尾，空列表抛出 `NetflowLoginError`。
- 日期按 Rust 格式编码：月份 `YYYY-MM`，日期 `YYYYMMDD`。Python 额外验证有效日期，
  年份取 1–65535；非法日期抛出 `ValueError`，不发送请求。
- 明细流量单位 KB，账单下载/上传量为字节，账单超额量和套餐量为 GB，费用为元。
  比例保留服务端小数，不乘以 100。
- 账单下载/上传量缺失或 null 时为 0；按 Rust 常见 64 位平台的 float→usize 行为转换，
  小数截断，负数归零，超大值饱和至 `2**64-1`；日期按 `%Y-%m-%d %H:%M:%S` 解析。
- 本月总量、下载量和上传量仅在不以 `GB` 结尾时补后缀，保留“小于”文字。
  服务端返回的套餐剩余量原样保留，不重算，例如没有超额时也可能返回剩余额外套餐 20GB。
- 锁定码 0→Unlocked、1→Locked，其他有效 i64 整数→Unknown；字符串、布尔值和缺失为解析错误。
- 账单接口保留服务端默认分页范围，不自动翻页；Rust 没有统一的查询会话过期业务码，
  非 2xx 查询响应和不符合格式的响应分别报告 HTTP、解析错误。登录响应允许携带 Cookie 的跳转。

## 个人门户实现约定

- 提供不可变 `PtToken`、可复用连接的 `PtClient` 和三个与 Rust 同名的查询函数。
- CAS service 保留 `https://pt.hnu.edu.cn/` 末尾斜杠；兑换票据要求门户响应 302，
  读取全部 Set-Cookie 并拼接请求头，不跟随该跳转。Python 额外拒绝空 Cookie 和门户域外回调。
- 校园卡余额和交易总额由分除以 100 转为元；单笔 `fTranAmt` 与 `nowAmt` 已为元，
  不重复换算。交易后余额去掉首尾空白、逗号和内部普通空格，再转为浮点数。
- 交易地点存在时去掉首尾空白，不存在时为 None；存在但只含空白时保留空字符串。
- 交易时间 `effectdate`、记账时间 `jndatetime` 分别按 `%Y/%m/%d %H:%M:%S` 解析。
- 交易记录列表缺失或 null 时返回空列表；交易数量按 Rust f64→u32 转换，小数截断，
  负数归零，溢出饱和至 `2**32-1`。Python 拒绝非有限金额和计数。
- 每次历史查询均先获取 CSRF，再用 `X-XSRF-TOKEN` 提交表单；消费 trancode=15，充值=16。
  年份取 1–65535，月份取 1–12，在请求前验证。保留 Rust 的月底 31 日请求和页大小 100000，
  不自动翻页，不根据日历修改结束日。
- 未读邮件字段 `unReadCount` 缺失或 null 时为 None，0 仍为整数 0；有值时要求合法 u32。
- Rust 未定义门户查询统一的会话过期业务码；非 2xx 查询响应报告 HTTP 异常，
  登录 HTML 等异常数据报告解析错误，CAS 失效异常原样传递。

## 新门户实现约定

- 提供不可变 `IPortalToken`、可复用连接的 `IPortalClient` 和六个与 Rust 同名的查询函数。
- CAS 登录保持 Rust 的嵌套 service URL 编码，要求票据回调响应 302，再访问至多一个 Location。
  按 Cookie 名覆盖并保持首次出现顺序；允许 Cookie 仅由第二个响应提供。
  Python 支持相对 Location，并限制票据回调和下一跳属于 iportal 域。
- 查询 HTTP 302 抛出 `IPortalTokenExpired`；JSON 要求整数 `e=0`，返回 `d`，
  非零 e 报告包含服务端 m 的解析错误，其他 HTTP 错误与网络错误分开。
- 账号的 identity_id 从字符串转为 u64，性别 1→Male、2→Female，其他代码报错。
- 个人资料先查询项目 ID，再并发请求详情；任一请求失败或取消时取消并等待其他任务。
  支持 Rust 的五个 key，未知 key 报错；缺少项目保留 None。显示值可为字符串或数字，
  标签兼容 name/title；无效登录时间保留 None，无效网络用量按 0 处理。
- 网络流量按 G/GB、M/MB、K/KB 的 1024 进制转换，未知单位按字节；转换采用 u64 饱和行为。
  Python 对余额等应为有限数的字段拒绝非有限值。
- 学期时间参数必须为不带时区的 datetime，按 UTC 转换，与 Rust `and_utc().timestamp()` 一致。
  学期编码 1→Autumn、2→WinterVacation、3→Spring、4→SummerVacation。
- 校园卡余额原样以元返回，交易为带正负号的 i64 整数分。按 Rust 映射八种交易类型，
  未知类型报错。MoneyTransfer 只表示实体卡余额同步，统计收支时应排除。
- 交易响应 nextpage/rowcount 是 u32 字符串，nextpage 非零表示有下一页。
  交易查询接收 date 范围及 `(page_size, page)`；Python 在请求前检查范围与 u32 参数。
- 申请列表保留总记录数与当前页列表，使用 created 和可空 inst_finished 作为时间，
  inst_status 0/1/2 对应 Pending/Processing/Completed；未知状态报错。
  查询参数顺序为 `(page, page_size)`。两种分页接口均不自动翻页。

## 学工与宿舍电量实现约定

- 学工提供不可变 `XgxtToken`、`XgxtClient`、`get_person_info`。
  CAS service 保持原始 HTTP 地址，但兑换票据前只将 URL 的 scheme 改为 HTTPS。
  要求响应 302 且有 Cookie，不跟随跳转；Python 额外检查回调属于学工域。
- 并发请求个人、在校、联系方式，按此顺序合并同名条目；任一请求失败或取消时清理其余任务。
  提取 `data.groupFields[0].fields`，仅接收字符串或 i64 整数默认值，其他类型和无效字段跳过。
- 培养层次 1/2/3 对应 Doctoral/Postgraduate/Undergraduate，性别 1/2 对应 Male/Female。
  学制缺失或空字符串时为 None，其他可选条目缺失为 None、空字符串仍为空字符串。
  学院、专业、班级等代码保留原值。Python 班级属性为 `class_`，默认序列化别名为 `class`。
- 宿舍楼或房间号为空时 dormitory 为 None；有原始文字但无法识别时保留 Dormitory，
  park/build 可能为 None。按 Rust 的园区判断顺序和正则提取，不额外猜测南楼等名称。
  `Dormitory.from_parsed_value` 可用于手工确认的园区、楼栋与房间。
- 电量提供 `get_electricity` 和可复用连接的 `WxpayClient`，无需认证。
  七个园区和所有楼栋编码与 Rust 表对应；南校区 19 舍按首位分区及附楼 F 前缀处理，
  德智指定楼栋补楼号，其他房间保留原值。参数通过 httpx 编码，带原始 Referer/X-Requested-With。
- 望麓桥 2 栋依次请求 52/53，3 栋依次请求 54/55，只在恰好一次请求成功时选择响应再解析。
  与 Rust 一样，不按业务正文决定南北；两次 HTTP 200 即使其中正文异常，也会认为无法区分。
  两次都失败或都成功时抛出 `WxpayAmbiguityError`，取消操作直接传递，不继续请求另一侧。
- 电量仅返回 data.Balance 字符串，保留“度”“元”等单位；未解析宿舍对应 Rust panic 的情况
  在 Python 抛出 ValueError，未知映射或响应格式错误抛出 WxpayParseError。
- Rust 未定义学工查询统一的会话失效业务码；Python 将非 2xx 查询响应报告为 HTTP 异常。
  个人资料可能含较大表单字典，调用方应根据使用场景缓存。

## 研究生系统实现约定

- 提供不可变 `YjsxtToken(id)`、`YjsxtClient` 和 `get_semester`、`get_class_table`。
  查询将会话 ID 插入 `/gmis/{id}/...`，不使用其他系统的 Cookie 请求头。
- 登录兑换 CAS 票据，要求首次响应 302，从 Location 的 `/gmis/` 后提取一段会话 ID，
  再访问该 Location。若响应重定向到 `/home/err`，提取并解码 msg，抛出 `YjsxtLoginError`。
  Python 支持相对或绝对同域跳转，并拒绝空 ID 和跨域目标。
- 查询 HTTP 302 抛出研究生 `TokenExpired`，CAS 失效原样传递；其他非 2xx 查询响应报告 HTTP 异常。
- bindterm 和课表都是明文 JSON；学期名称映射秋/春/暑假/寒假小学期为 1/2/3/4，保持响应顺序。
- 课表行按 mc 节次、z1–z7 星期解析；null 或缺失单元格跳过。
  一个单元格可包含多段以“课程编号:”开头的五行课程块。行数、前缀、周次区间或周次类型异常时报错，
  不静默忽略未知课程块；按 Rust 规则去掉课程字段中的全部空白。
- 连续周/单周/双周及单周次区间按 Rust 展开；第 0 周保留。
  按 `(课程名称, 编号, 班级, 教师)` 区分课程，再按 `(周, 星期, 地点)` 合并节次。
  不同教师的阶段分别输出；“无节次”课程去重后 schedule=None。
- Python 对课程、安排和节次排序以稳定输出；同一节次重复出现时与 Rust 一样保留重复项。
  反向周次区间按 Rust 得到空安排，而不是额外推断周次。
- 支持注入 HTTP 客户端；库只关闭自己创建的连接，会话 ID 不出现在 token repr 中。

## CG 编程平台实现约定

- 提供 `CgSession.new()` 获取初始 Cookie 和验证码图片，`session.login()` 完成独立账号登录。
  Python `captcha_image` 为图片字节属性；会话和令牌请求头为不可变副本，repr 隐藏 Cookie/图片。
- 密码按 Rust 前端协议使用 `Client8Sess!06ID` 密钥做 AES-128-ECB/PKCS7 后一次 Base64，
  表单包含 IndexStyle=1、stid、pwd、captchaCode。验证码识别由调用者完成。
- 登录响应要求 302/Location；loginErr=1 为密码错误、6 为验证码错误、0 或缺失为成功，
  其他值抛出带 code 的 LoginFailed。Python 按 URL 查询参数解析错误码，兼容额外参数。
  成功后保留原始 Cookie 并追加响应 Cookie，与 Rust 一致；不自动跟随登录跳转或重试。
- 查询检测 302 Location 含 simple.jsp/login 时抛出 CG TokenExpired；
  Python 对 HTTP 错误显式抛出 CgStatusError，避免将错误页面误当成空列表。
- 课程列表 HTTP 200 解析列表链接，302 时固定读取 main.jsp 下拉菜单；课程按 ID 首次去重。
  作业查询依次进入 courselist.jsp?courseID、访问课程跳转页、获取 mainActiveAssigns.jsp。
- 元数据使用 selectolax CSS 选择器对应 Rust scraper 选择器，保留记录顺序、去掉首尾空白。
  无有效记录返回 None；缺少关键字段、非法 u32 或无效分值的条目跳过。Python 跳过非有限分值。
- 题目序号来自 proNum，题目 ID 来自 problemID，分数来自第二个 td。题目内容保留原始 HTML。
  跳转支持当前目录相对路径、根路径和同域 HTTPS 绝对地址；Python 拒绝跨域跳转，
  并检查第二次请求的登录失效和 HTTP 状态。
- 与 Rust 的一处有意差异：programList.jsp 直接返回 HTTP 200 时，Python 返回已有正文，
  避免 Rust 再次无参数请求同一路径时丢失 assignID/proNum。HTTP 302 仍跟随一跳获取题目页面。
- 提供可复用连接的 CgClient 和四个同名查询函数；注入客户端由调用方关闭。
  课程上下文是服务端会话状态，调用方应按课程顺序查询；范围与 Rust 一样为通用元数据和页面导航。

## 测试来源与限制

`tests/hdjw/fixtures` 从 Rust 对应模块的 `test_data` 原样复制，来源遵循仓库 AGPL-3.0 许可证。
测试直接使用 Python 目录的样本，避免 Rust 参考目录未纳入版本管理时影响 Python 测试。
断言涵盖 Rust 样例预期值，并补充无效响应、单/双周、会话过期、Cookie 合并、表单编码、
特殊字符参数、HTTP 错误和连接所有权。

`tests/gym/fixtures` 的两个成绩样本原样复制自 Rust `gym/grade/test_data`，
成绩断言与 Rust 测试预期一致。Rust 没有预约样本，预约测试按其原始结构定义构造。
新增测试还覆盖直接登录、CAS 票据跳转、Cookie 传递、预约表单、成绩回退和加分、
并发请求失败时取消另一请求、异常响应及客户端所有权。

`tests/lab/fixtures` 的六个样本原样复制自 Rust `lab/*/test_data`，断言覆盖 Rust 的预期值。
登录和虚拟实验响应按 Rust 字段定义构造。新增测试覆盖加密向量、UTF-8/填充、
验证码重试与次数上限、Cookie 更新、登录业务错误、识别器失败与取消、查询参数、
成绩合并和过滤、虚拟实验去重、并发任务清理及客户端所有权。

`tests/netflow/fixtures` 的五个样本原样复制自 Rust `netflow/*/test_data`，覆盖明细、账单、
欠费、本月用量及锁定状态的 Rust 预期值。日明细使用同构月明细样本；登录响应按 Rust 流程构造。
新增测试验证 GET 表单正文、首尾 Cookie、CAS 失效传递、单位保持、账单数值转换、
GB 后缀、未知锁定码、日期验证、请求参数、异常响应和客户端所有权。

`tests/pt/fixtures` 的五个样本原样复制自 Rust `pt/*/test_data`，覆盖校园卡信息、
消费和充值记录、已绑定和未绑定邮箱的 Rust 预期值；登录及 CSRF 响应按 Rust 流程构造。
新增测试验证 service 末尾斜杠、302 Cookie、CSRF 获取和刷新、请求表单、
金额换算与千分位余额、空列表、浮点计数转换、未绑定与零未读邮件、异常响应及客户端所有权。

`tests/iportal/fixtures` 按模块复制 Rust `iportal/**/test_data`，包含正常响应、
异常数据形状、错误日期和非法 JSON。断言覆盖账号、五项个人资料、学期、交易和申请记录。
额外测试验证 Cookie 覆盖、登录跳转边界、全部枚举映射、单位换算、分页参数与 URL 编码、
UTC 时间戳、会话失效、并发请求失败及取消时的清理和客户端所有权。

`tests/xgxt/fixtures` 的三份表单和 `tests/wxpay/fixtures/checkRoomNo.json` 原样复制自 Rust 对应 test_data。
断言对照 Rust 的个人信息及宿舍解析结果，逐项核对全部楼栋编码及特殊房间号。
额外测试覆盖 HTTPS 票据兑换、Cookie、字段类型过滤、枚举/缺失字段、JSON class 别名、
三请求合并与取消、电量请求参数和请求头、南北两侧所有选择分支及客户端所有权。

`tests/yjsxt/fixtures` 的四个样本原样复制自 Rust 对应 test_data，覆盖 56 个学期、
普通课表、单双周和多教师阶段课表。断言对照 Rust 的课程数量和完整周次/节次安排。
额外测试覆盖无节次课程去重、空教师、第 0 周、不同地点、重复节次、异常课程块、
URL 会话 ID、账号无权限消息、会话过期、表单编码和客户端所有权。

`tests/cg/fixtures` 的六份 HTML 原样复制自 Rust `cg/course/test_data`，
覆盖多课程/单课程列表、去重、作业、题目元数据和原始页面。额外测试验证密码加密及 UTF-8/填充、
验证码 Cookie、登录错误码、三请求课程上下文、相对/绝对跳转、直接返回题目页面、
无效条目跳过、会话失效、HTTP/网络错误及连接所有权。

所有测试均为离线验证；真实账号、校园网服务状态及线上响应变化尚未验证。
