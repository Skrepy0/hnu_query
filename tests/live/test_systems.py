import os
from datetime import datetime

import pytest

from hnu_query.cas import CasToken

from .conftest import captcha, required_env

pytestmark = pytest.mark.live


def env_int(name: str) -> int:
    value = required_env(name)
    try:
        return int(value)
    except ValueError:
        pytest.fail(f"{name} 必须是整数，当前值无法解析")


async def test_cas_login(cas_token: CasToken):
    assert cas_token.stu_id == required_env("TEST_STU_ID")


async def test_hdjw(cas_token: CasToken):
    from hnu_query.hdjw import HdjwClient, acquire_by_cas_login

    token = await acquire_by_cas_login(cas_token)
    async with HdjwClient(token) as client:
        grades = await client.get_grade(env_int("TEST_XN"), env_int("TEST_XQ"))
        assert isinstance(grades, list)


async def test_credential(cas_token: CasToken):
    from hnu_query.credential import acquire_by_cas_login, get_grade_rank

    token = await acquire_by_cas_login(cas_token)
    assert await get_grade_rank(token) is not None


async def test_gym(cas_token: CasToken):
    from hnu_query.gym import GymClient, acquire_by_cas_login

    token = await acquire_by_cas_login(cas_token)
    async with GymClient(token) as client:
        assert await client.get_grade(env_int("TEST_XN")) is not None


async def test_netflow(cas_token: CasToken):
    from hnu_query.netflow import NetflowClient, acquire_by_cas_login

    token = await acquire_by_cas_login(cas_token)
    async with NetflowClient(token) as client:
        assert await client.get_this_month_info() is not None


async def test_pt(cas_token: CasToken):
    from hnu_query.pt import PtClient, acquire_by_cas_login

    token = await acquire_by_cas_login(cas_token)
    async with PtClient(token) as client:
        assert await client.get_card_info() is not None


async def test_iportal(cas_token: CasToken):
    from hnu_query.iportal import IPortalClient, acquire_by_cas_login

    token = await acquire_by_cas_login(cas_token)
    async with IPortalClient(token) as client:
        assert await client.get_account_info() is not None
        assert await client.get_term_info(datetime.now().replace(microsecond=0)) is not None


async def test_xgxt(cas_token: CasToken):
    from hnu_query.xgxt import XgxtClient, acquire_by_cas_login

    token = await acquire_by_cas_login(cas_token)
    async with XgxtClient(token) as client:
        assert await client.get_person_info() is not None


async def test_wxpay():
    from hnu_query.wxpay import get_electricity
    from hnu_query.xgxt import Dormitory

    dormitory = Dormitory.from_parsed_value(
        required_env("TEST_DORMITORY_PARK"),
        required_env("TEST_DORMITORY_BUILD"),
        required_env("TEST_DORMITORY_ROOM"),
    )
    assert await get_electricity(dormitory)


async def test_lab():
    from hnu_query.lab import LabClient, acquire_by_login

    token = await acquire_by_login(
        required_env("TEST_STU_ID"),
        required_env("TEST_LAB_PASSWORD"),
        lambda image: captcha(image, "lab-captcha.jpg"),
        env_int("TEST_LAB_MAX_TRIED"),
    )
    async with LabClient(token) as client:
        assert isinstance(await client.get_semester(), list)


async def test_cg():
    from hnu_query.cg import CgClient, CgSession

    stu_id = required_env("TEST_STU_ID")
    password = required_env("TEST_CG_PASSWORD")
    session = await CgSession.new()
    code = await captcha(session.captcha_image, "cg-captcha.png")
    token = await session.login(stu_id, password, code)
    async with CgClient(token) as client:
        courses = await client.get_course_list()
        assert courses is None or isinstance(courses, list)


def test_env_file_is_loaded():
    assert os.environ.get("TEST_STU_ID", "").strip(), (
        "请使用 `uv run --env-file .env poe test-live` 运行真实请求测试"
    )
