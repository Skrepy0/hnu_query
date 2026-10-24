import json
from pathlib import Path

import pytest

from hnu_query.netflow import NetflowToken


@pytest.fixture
def netflow_token():
    return NetflowToken({"Cookie": "ASP.NET_SessionId=test; .ASPXAUTH=auth"})


@pytest.fixture
def netflow_data():
    def read(name):
        return json.loads(
            (Path(__file__).parent / "fixtures" / name).read_text(encoding="utf-8")
        )

    return read
