import json
from pathlib import Path

import pytest

from hnu_query.pt import PtToken


@pytest.fixture
def pt_token():
    return PtToken({"Cookie": "SESSION=pt-test"})


@pytest.fixture
def pt_data():
    def read(name):
        return json.loads(
            (Path(__file__).parent / "fixtures" / name).read_text(encoding="utf-8")
        )

    return read
