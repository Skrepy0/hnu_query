import json
from pathlib import Path

import pytest

from hnu_query.iportal import IPortalToken


@pytest.fixture
def iportal_token():
    return IPortalToken({"Cookie": "session=iportal-test"})


@pytest.fixture
def iportal_text():
    def read(name):
        return (Path(__file__).parent / "fixtures" / name).read_text(encoding="utf-8")

    return read


@pytest.fixture
def iportal_data(iportal_text):
    return lambda name: json.loads(iportal_text(name))
