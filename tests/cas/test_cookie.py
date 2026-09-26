# tests/cas/test_cookie.py
from hnu_query.utils.cookie import cookie_parser


def test_cookie_parser_simple():
    headers = ["TGC=tgt-value; Path=/cas/; HttpOnly"]
    assert cookie_parser(headers) == ["TGC=tgt-value"]


def test_cookie_parser_multiple():
    headers = [
        "TGC=tgt-value; Path=/cas/",
        "JSESSIONID=js-value; Path=/; HttpOnly",
    ]
    assert cookie_parser(headers) == ["TGC=tgt-value", "JSESSIONID=js-value"]


def test_cookie_parser_empty_list():
    assert cookie_parser([]) == []


def test_cookie_parser_no_attributes():
    headers = ["simple=value"]
    assert cookie_parser(headers) == ["simple=value"]


def test_cookie_parser_empty_value():
    headers = ["name=; Path=/"]
    assert cookie_parser(headers) == ["name="]


def test_cookie_parser_skips_blank():
    headers = ["", "  ", "name=value"]
    assert cookie_parser(headers) == ["name=value"]
