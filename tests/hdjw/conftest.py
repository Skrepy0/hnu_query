from pathlib import Path

import pytest

from hnu_query.hdjw import HdjwToken


@pytest.fixture
def fixture_text():
    def read(name):
        return (Path(__file__).parent / "fixtures" / name).read_text(encoding="utf-8")

    return read


@pytest.fixture
def hdjw_token():
    return HdjwToken({"Cookie": "JSESSIONID=hdjw-test"})
