import os

import pytest

from tests.live.conftest import live_network


def test_live_direct_mode_restores_proxy_settings(monkeypatch):
    monkeypatch.delenv("TEST_DIRECT", raising=False)
    monkeypatch.setenv("NO_PROXY", "original.example")
    if os.name != "nt":
        monkeypatch.delenv("no_proxy", raising=False)
    setup = live_network.__wrapped__()
    next(setup)
    try:
        assert os.environ["NO_PROXY"] == "*"
        assert os.environ["no_proxy"] == "*"
    finally:
        setup.close()
    assert os.environ["NO_PROXY"] == "original.example"
    if os.name != "nt":
        assert "no_proxy" not in os.environ


def test_live_proxy_mode_preserves_environment(monkeypatch):
    monkeypatch.setenv("TEST_DIRECT", "false")
    monkeypatch.setenv("NO_PROXY", "original.example")
    setup = live_network.__wrapped__()
    next(setup)
    try:
        assert os.environ["NO_PROXY"] == "original.example"
    finally:
        setup.close()


def test_live_network_rejects_invalid_mode(monkeypatch):
    monkeypatch.setenv("TEST_DIRECT", "invalid")
    with pytest.raises(pytest.fail.Exception, match="TEST_DIRECT"):
        next(live_network.__wrapped__())
