# tests/ca/test_parse.py
import pytest

from hnu_query.credential import preview_file_name
from hnu_query.credential.exceptions import CaParseError


def test_parse_from_anchor(sample_preview_html):
    """从 <a href> 中提取文件名。"""
    assert preview_file_name(sample_preview_html) == "abc123.pdf"


def test_parse_from_iframe(sample_preview_html_iframe):
    """从 <iframe src> 中提取文件名。"""
    assert preview_file_name(sample_preview_html_iframe) == "xyz789.pdf"


def test_parse_no_link(sample_preview_html_no_link):
    """没有下载链接时抛 CaParseError。"""
    with pytest.raises(CaParseError):
        preview_file_name(sample_preview_html_no_link)


def test_parse_empty_html():
    with pytest.raises(CaParseError):
        preview_file_name("")


def test_parse_fallback_regex():
    """即使标签被破坏，正则回退也能命中。"""
    html = '<div>broken <a href=/student/sys/common/view/fallback.pdf>下载</a>'
    assert preview_file_name(html) == "fallback.pdf"