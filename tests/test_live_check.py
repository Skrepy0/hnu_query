import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from scripts import live_check


def test_selection_is_explicit_and_deduplicated():
    assert live_check.select_modules("cas, hdjw,cas") == ["cas", "hdjw"]
    with pytest.raises(ValueError):
        live_check.select_modules("cas,delete_token")


async def test_cas_failure_skips_dependents_and_redacts_report(tmp_path, monkeypatch):
    secret = "private-password-and-response"
    login = AsyncMock(side_effect=RuntimeError(secret))
    query = AsyncMock()
    monkeypatch.setattr(live_check, "login_cas", login)
    monkeypatch.setattr(live_check, "query", query)
    report = {"results": []}
    path = tmp_path / "report.json"
    await live_check.run_modules(
        ["cas", "hdjw", "ai"], {"stu_id": "private-student"}, report, path
    )
    assert [item["status"] for item in report["results"]] == [
        "failed",
        "skipped",
        "skipped",
    ]
    assert secret not in path.read_text(encoding="utf-8")
    assert "private-student" not in path.read_text(encoding="utf-8")
    assert login.await_count == 1
    query.assert_not_awaited()


async def test_independent_module_needs_no_cas_and_saves_no_data(tmp_path, monkeypatch):
    login = AsyncMock()
    query = AsyncMock(return_value=[{"student": "private-value"}])
    monkeypatch.setattr(live_check, "login_cas", login)
    monkeypatch.setattr(live_check, "query", query)
    report = {"results": []}
    path = tmp_path / "report.json"
    await live_check.run_modules(["cg"], {"stu_id": "student"}, report, path)
    assert report["results"][0]["items"] == 1
    assert "private-value" not in path.read_text(encoding="utf-8")
    login.assert_not_awaited()


async def test_one_module_failure_does_not_block_others(tmp_path, monkeypatch):
    monkeypatch.setattr(live_check, "login_cas", AsyncMock(return_value=object()))
    monkeypatch.setattr(
        live_check, "query", AsyncMock(side_effect=[RuntimeError("private"), []])
    )
    report = {"results": []}
    await live_check.run_modules(
        ["hdjw", "pt"], {"stu_id": "student"}, report, tmp_path / "report.json"
    )
    assert [item["status"] for item in report["results"]] == [
        "passed",
        "failed",
        "passed",
    ]


async def test_sms_retry_uses_returned_tfa_token(monkeypatch):
    import hnu_query.cas
    from hnu_query.cas import TFARequired

    cas = object()
    second = SimpleNamespace(verify=AsyncMock(return_value=("success", cas)))
    first = SimpleNamespace(
        send_sms=AsyncMock(return_value="valid"),
        verify=AsyncMock(return_value=("code_error", second)),
    )
    monkeypatch.setattr(
        hnu_query.cas, "acquire_by_login", AsyncMock(side_effect=TFARequired(first))
    )
    monkeypatch.setattr("builtins.input", lambda _: "y")
    prompts = iter(["private-password", "wrong-code", "right-code"])
    monkeypatch.setattr(live_check.getpass, "getpass", lambda _: next(prompts))
    assert await live_check.login_cas("student") is cas
    first.verify.assert_awaited_once_with("wrong-code")
    second.verify.assert_awaited_once_with("right-code")


def test_main_cancel_creates_report_without_credentials(tmp_path, monkeypatch):
    path = tmp_path / "report.json"
    monkeypatch.setattr("builtins.input", lambda _: (_ for _ in ()).throw(EOFError()))
    assert live_check.main(["--report", str(path)]) == 1
    assert json.loads(path.read_text(encoding="utf-8"))["status"] == "cancelled"


def test_failure_retains_http_code_without_body():
    from hnu_query.credential import CaStatusError

    value = live_check.failure(CaStatusError(401, "private response"))
    assert value["http_status"] == 401
    assert "private response" not in str(value)


def test_failure_preserves_cause_types_without_messages():
    try:
        try:
            raise ConnectionError("private-cookie")
        except ConnectionError as cause:
            raise RuntimeError("private-ticket") from cause
    except RuntimeError as exc:
        value = live_check.failure(exc)
    assert value["causes"] == ["builtins.ConnectionError"]
    assert "private-cookie" not in str(value) and "private-ticket" not in str(value)


def test_direct_mode_bypasses_proxy_only_during_run(tmp_path, monkeypatch):
    import httpx._utils

    monkeypatch.setenv("NO_PROXY", "previous.example")
    monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:9")
    monkeypatch.setattr("builtins.input", lambda _: "student")

    async def login(stu_id):
        assert stu_id == "student"
        assert httpx._utils.get_environment_proxies() == {}
        return object()

    monkeypatch.setattr(live_check, "login_cas", login)
    path = tmp_path / "report.json"
    assert live_check.main(["--modules", "cas", "--direct", "--report", str(path)]) == 0
    assert live_check.os.environ["NO_PROXY"] == "previous.example"
    assert json.loads(path.read_text(encoding="utf-8"))["network_mode"] == "direct"
