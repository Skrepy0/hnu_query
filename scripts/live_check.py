"""校园网交互联调：凭据只在本机输入，报告不包含响应正文。"""

import argparse
import asyncio
import getpass
import importlib
import json
import os
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

MODULES = (
    "cas",
    "hdjw",
    "credential",
    "gym",
    "lab",
    "netflow",
    "pt",
    "iportal",
    "xgxt",
    "yjsxt",
    "wxpay",
    "cg",
    "ai",
)
INDEPENDENT = {"lab", "cg"}
QUERIES = {
    "hdjw": ("HdjwClient", "get_rank"),
    "gym": ("GymClient", "get_appointment"),
    "netflow": ("NetflowClient", "get_this_month_info"),
    "pt": ("PtClient", "get_card_info"),
    "iportal": ("IPortalClient", "get_account_info"),
    "xgxt": ("XgxtClient", "get_person_info"),
    "yjsxt": ("YjsxtClient", "get_semester"),
    "ai": ("AiClient", "get_user_remaining_quota"),
}


@contextmanager
def connection_mode(direct: bool):
    """仅在当前联调过程中跳过代理，不修改系统配置。"""
    previous = os.environ.get("NO_PROXY")
    if direct:
        os.environ["NO_PROXY"] = "*"
    try:
        yield
    finally:
        if direct:
            if previous is None:
                os.environ.pop("NO_PROXY", None)
            else:
                os.environ["NO_PROXY"] = previous


def select_modules(text: str) -> list[str]:
    names = list(
        dict.fromkeys(name.strip() for name in text.split(",") if name.strip())
    )
    if not names or any(name not in MODULES for name in names):
        raise ValueError("请输入列表中的模块名，以英文逗号分隔")
    return names


def write_report(path: Path, report: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    temporary.replace(path)


def failure(exc: Exception) -> dict:
    # 不保存 str(exc) / traceback / 响应正文，避免票据和个人资料进入报告。
    result = {
        "status": "failed",
        "error": f"{type(exc).__module__}.{type(exc).__name__}",
    }
    code = getattr(exc, "status_code", None)
    if type(code) is int:
        result["http_status"] = code
    causes = []
    cause = exc.__cause__
    while cause is not None and len(causes) < 3:
        causes.append(f"{type(cause).__module__}.{type(cause).__name__}")
        cause = cause.__cause__
    if causes:
        result["causes"] = causes
    return result


async def login_cas(stu_id: str):
    from hnu_query.cas import TFARequired, acquire_by_login

    password = getpass.getpass("个人门户密码（输入不显示）：")
    try:
        return await acquire_by_login(stu_id, password)
    except TFARequired as required:
        tfa = required.tfa_token
    finally:
        del password
    if input("需要短信验证，发送验证码？[y/N]：").strip().lower() != "y":
        raise RuntimeError("用户未进行短信验证")
    sms_result = await tfa.send_sms()
    if sms_result not in ("success", "valid"):
        raise RuntimeError("短信发送失败")
    for _ in range(3):
        code = getpass.getpass("短信验证码（输入不显示）：")
        status, token = await tfa.verify(code)
        if status == "success":
            return token
        if status != "code_error":
            raise RuntimeError("短信验证会话失效")
        tfa = token
        print("验证码错误，请重新输入。")
    raise RuntimeError("短信验证未完成")


async def captcha(image: bytes, folder: Path, name: str) -> str:
    path = folder / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(image)
    print(f"请查看验证码图片：{path}")
    if os.name == "nt":
        os.startfile(str(path))
    return input("图片验证码：").strip()


async def query(name: str, context: dict, folder: Path):
    module = importlib.import_module(f"hnu_query.{name}")
    if name == "credential":
        token = await module.acquire_by_cas_login(context["cas"])
        return await module.get_grade_rank(token)
    if name == "lab":
        password = getpass.getpass("实验平台密码（输入不显示）：")

        async def resolve(image):
            return await captcha(image, folder, "lab-captcha.jpg")

        token = await module.acquire_by_login(context["stu_id"], password, resolve)
        async with module.LabClient(token) as client:
            return await client.get_semester()
    if name == "cg":
        password = getpass.getpass("CG 平台密码（输入不显示）：")
        session = await module.CgSession.new()
        code = await captcha(session.captcha_image, folder, "cg-captcha.png")
        token = await session.login(context["stu_id"], password, code)
        async with module.CgClient(token) as client:
            return await client.get_course_list()
    if name == "wxpay":
        if "person" not in context:
            context["person"] = await query("xgxt", context, folder)
        dormitory = context["person"].dormitory
        if dormitory is None:
            raise RuntimeError("学工资料没有宿舍信息")
        return await module.get_electricity(dormitory)
    client_name, method = QUERIES[name]
    token = await module.acquire_by_cas_login(context["cas"])
    async with getattr(module, client_name)(token) as client:
        result = await getattr(client, method)()
    if name == "xgxt":
        context["person"] = result
    return result


async def run_modules(
    names: list[str], context: dict, report: dict, path: Path
) -> None:
    needs_cas = any(name not in INDEPENDENT for name in names)
    if needs_cas:
        start = time.monotonic()
        print("正在登录 CAS……")
        try:
            context["cas"] = await login_cas(context["stu_id"])
            result = {"module": "cas", "status": "passed"}
        except Exception as exc:
            result = {"module": "cas", **failure(exc)}
        result["seconds"] = round(time.monotonic() - start, 2)
        report["results"].append(result)
        write_report(path, report)
        print(f"CAS: {result['status']}")
    for name in names:
        if name == "cas":
            continue
        if name not in INDEPENDENT and "cas" not in context:
            report["results"].append(
                {"module": name, "status": "skipped", "reason": "CAS 登录未完成"}
            )
            write_report(path, report)
            continue
        start = time.monotonic()
        print(f"正在验证 {name}……")
        try:
            value = await query(name, context, path.parent)
            result = {"module": name, "status": "passed"}
            if isinstance(value, list):
                result["items"] = len(value)
        except Exception as exc:
            result = {"module": name, **failure(exc)}
        result["seconds"] = round(time.monotonic() - start, 2)
        report["results"].append(result)
        write_report(path, report)
        print(
            f"{name}: {result['status']}"
            + (f" ({result['error']})" if "error" in result else "")
        )


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--modules", help="英文逗号分隔的模块名；默认交互选择")
    parser.add_argument(
        "--direct", action="store_true", help="本次联调跳过系统/环境代理"
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=Path(__file__).resolve().parents[1] / ".local/live-check.json",
    )
    parser.add_argument(
        "--pause", action="store_true", help="完成后等待回车，适用于单独窗口"
    )
    args = parser.parse_args(argv)
    report = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "status": "waiting_for_input",
        "network_mode": "direct" if args.direct else "system",
        "results": [],
    }
    write_report(args.report, report)
    exit_code = 1
    try:
        print("湖南大学查询库 · 本地只读联调")
        print("可选模块：" + ", ".join(MODULES))
        print("credential 查询本科主修成绩凭证；wxpay 需要学工宿舍资料。")
        print("报告只记录状态、异常类型和耗时；不会保存账号、密码或响应正文。")
        names = select_modules(
            args.modules or input("验证模块 [cas,hdjw]：").strip() or "cas,hdjw"
        )
        stu_id = input("学号：").strip()
        if not stu_id:
            raise ValueError("学号不能为空")
        report["status"] = "running"
        report["modules"] = names
        write_report(args.report, report)
        with connection_mode(args.direct):
            asyncio.run(run_modules(names, {"stu_id": stu_id}, report, args.report))
        report["status"] = "completed"
        exit_code = int(any(item["status"] != "passed" for item in report["results"]))
    except (KeyboardInterrupt, EOFError):
        report["status"] = "cancelled"
        print("已取消。")
    except Exception as exc:
        report["status"] = "failed"
        report["error"] = failure(exc)["error"]
        print(f"联调未完成：{report['error']}")
    finally:
        report["finished_at"] = datetime.now(timezone.utc).isoformat()
        write_report(args.report, report)
        print(f"结果报告：{args.report.resolve()}")
        if args.pause:
            try:
                input("按回车关闭窗口……")
            except (KeyboardInterrupt, EOFError):
                pass
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
