from pathlib import Path

import pytest

from hnu_query.ai import AiToken
from hnu_query.cas import CasToken


@pytest.fixture
def ai_token():
    return AiToken({"Authorization": "Bearer test-bearer", "Cookie": "session=test"})


@pytest.fixture
def cas_token():
    return CasToken("TGC=original; JSESSIONID=authenticated", "test-student")


@pytest.fixture
def sample():
    def load(name):
        return (Path(__file__).parent / "fixtures" / name).read_text(encoding="utf-8")

    return load
