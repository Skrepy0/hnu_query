# src/hnu_query/ca/parse.py
import re
from selectolax.parser import HTMLParser

from .exceptions import CaParseError

_VIEW_RE = re.compile(r"/student/sys/common/view/([^\"'?]+)")


def preview_file_name(html: str) -> str:
    """从预览页 HTML 中提取真实文件名。

    对应 Rust ``ca::parse::preview_file_name``。
    """
    tree = HTMLParser(html)
    for node in tree.css("a[href], iframe[src], embed[src]"):
        href = node.attributes.get("href") or node.attributes.get("src") or ""
        m = _VIEW_RE.search(href)
        if m:
            return m.group(1)

    m = _VIEW_RE.search(html)
    if m:
        return m.group(1)

    raise CaParseError("预览页中未找到文件下载链接")