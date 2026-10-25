import json
from pathlib import Path

import pytest

from hnu_query.gym import GymToken


@pytest.fixture
def gym_token():
    return GymToken({"Cookie": "PHPSESSID=gym-test"})


@pytest.fixture
def gym_data():
    def read(name):
        return json.loads((Path(__file__).parent / "fixtures" / name).read_text(encoding="utf-8"))

    return read


@pytest.fixture
def appointments():
    # Rust 未提供预约样本，按 RawAppointment 字段定义构造。
    return {
        "info": "查询成功",
        "status": 1,
        "data": [
            {
                "class_id": 42,
                "button_status": 1,
                "class_name": "体测预约",
                "class_time": "2025-12-15",
                "show_time": "2025年12月15号（周一）",
                "test_time": "10:00 - 11:30",
            },
            {
                "class_id": 43,
                "button_status": 2,
                "class_name": "视力检查",
                "class_time": "2025-12-16",
                "show_time": "2025年12月16号（周二）",
                "test_time": "14:00 - 15:00",
            },
        ],
    }
