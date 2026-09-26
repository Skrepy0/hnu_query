from dataclasses import FrozenInstanceError

import pytest

from hnu_query.cas import CasToken


def test_token_creation():
    token = CasToken(cookie="TGC=abc", stu_id="20210001")
    assert token.cookie == "TGC=abc"
    assert token.stu_id == "20210001"


def test_from_cookie_unchecked():
    token = CasToken.from_cookie_unchecked("TGC=xyz", "20210002")
    assert token.cookie == "TGC=xyz"
    assert token.stu_id == "20210002"


def test_token_is_frozen():
    token = CasToken(cookie="TGC=abc", stu_id="20210001")
    with pytest.raises((FrozenInstanceError, AttributeError)):
        token.cookie = "new"  # type: ignore[misc]
