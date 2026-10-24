from pathlib import Path

import pytest

from hnu_query.yjsxt import YjsxtToken


@pytest.fixture
def yjsxt_token():
    return YjsxtToken.from_id_unchecked("(S(test-session))")


@pytest.fixture
def yjsxt_text():
    def read(name):
        return (Path(__file__).parent / "fixtures" / name).read_text(encoding="utf-8")

    return read
