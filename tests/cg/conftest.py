from pathlib import Path

import pytest

from hnu_query.cg import CgToken


@pytest.fixture
def cg_token():
    return CgToken({"Cookie": "JSESSIONID=cg-test"})


@pytest.fixture
def cg_text():
    def read(name):
        return (Path(__file__).parent / "fixtures" / name).read_text(encoding="utf-8")

    return read
