import json
from pathlib import Path

import pytest

from hnu_query.lab import LabToken


@pytest.fixture
def lab_token():
    return LabToken({"Cookie": "ASP.NET_SessionId=lab-test"}, "202402050201")


@pytest.fixture
def lab_data():
    def read(name):
        return json.loads((Path(__file__).parent / "fixtures" / name).read_text(encoding="utf-8"))

    return read
