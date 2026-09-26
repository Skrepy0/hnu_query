from hnu_query.credential import CaToken


def test_empty_token():
    token = CaToken()
    assert token.is_empty() is True
    assert token.headers == {}


def test_token_with_headers():
    token = CaToken(headers={"Cookie": "a=b"})
    assert token.is_empty() is False
    assert token.headers == {"Cookie": "a=b"}


def test_token_is_frozen():
    """CaToken 应不可变，防止意外修改。"""
    import pytest
    token = CaToken(headers={"Cookie": "a=b"})
    with pytest.raises(Exception):  # FrozenInstanceError
        token.headers = {}  # type: ignore[misc]
