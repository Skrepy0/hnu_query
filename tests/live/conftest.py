import asyncio
import os
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
import pytest_asyncio

from hnu_query.cas import CasToken, TFARequired, acquire_by_login

pytestmark = pytest.mark.live


def required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        pytest.skip(f".env 未配置 {name}")
    return value


@pytest.fixture(scope="session")
def live_network():
    """校园网联调默认直连，避免系统代理将请求送到 WebVPN。"""
    direct = os.environ.get("TEST_DIRECT", "true").strip().lower()
    if direct not in {"true", "false", "1", "0"}:
        pytest.fail("TEST_DIRECT 必须为 true、false、1 或 0")
    with pytest.MonkeyPatch.context() as patch:
        if direct in {"true", "1"}:
            patch.setenv("NO_PROXY", "*")
            patch.setenv("no_proxy", "*")
        yield


@pytest.fixture(autouse=True, scope="session")
def live_network_setup(live_network):
    """让独立账号平台和 CAS 共用本次测试的网络设置。"""


@pytest_asyncio.fixture(scope="session")
async def cas_token(live_network) -> AsyncIterator[CasToken]:
    stu_id = required_env("TEST_STU_ID")
    password = required_env("TEST_PASSWORD")
    try:
        token = await acquire_by_login(stu_id, password)
    except TFARequired as required:
        result = await required.tfa_token.send_sms()
        if result not in {"success", "valid"}:
            pytest.fail(f"CAS 短信发送失败：{result}")
        current = required.tfa_token
        for _ in range(3):
            code = await asyncio.to_thread(input, "CAS 短信验证码：")
            status, value = await current.verify(code.strip())
            if status == "success":
                token = value
                break
            if status != "code_error":
                pytest.fail(f"CAS 短信验证失败：{status}")
            current = value
        else:
            pytest.fail("CAS 短信验证码连续三次错误")
    yield token


async def captcha(image: bytes, name: str) -> str:
    folder = Path(os.environ.get("TEST_CG_CAPTCHA_DIR", ".local"))
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / name
    path.write_bytes(image)
    print(f"请打开验证码图片：{path.resolve()}")
    return (await asyncio.to_thread(input, "验证码：")).strip()
