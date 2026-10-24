from pathlib import Path

import pytest

from hnu_query.xgxt import XgxtToken
from hnu_query.xgxt.parse import extract_xgxt_entry


@pytest.fixture
def xgxt_token():
    return XgxtToken({"Cookie": "JSESSIONID=xgxt-test"})


@pytest.fixture
def xgxt_text():
    def read(name):
        return (Path(__file__).parent / "fixtures" / name).read_text(encoding="utf-8")

    return read


@pytest.fixture
def xgxt_entries(xgxt_text):
    entries = {}
    for name in ("user_info.json", "in_school_info.json", "contact_info.json"):
        entries.update(extract_xgxt_entry(xgxt_text(name)))
    return entries
