"""使用 HTML 选择器提取 CG 通用元数据；无有效记录时返回 None。"""

import math
import re

from selectolax.parser import HTMLParser

from .models import CgAssignment, CgCourse, CgProblem


def _u32(value: str | None) -> int | None:
    if value is None or re.fullmatch(r"\+?[0-9]+", value) is None:
        return None
    try:
        number = int(value)
    except ValueError:
        return None
    return number if number < 2**32 else None


def _after(value: str | None, marker: str) -> str | None:
    return value.split(marker, 1)[1] if value is not None and marker in value else None


def _courses(elements, id_value) -> list[CgCourse] | None:
    result = []
    seen = set()
    for node in elements:
        id = _u32(id_value(node))
        name = node.text().strip()
        if id is not None and name and id not in seen:
            result.append(CgCourse(id=id, name=name))
            seen.add(id)
    return result or None


def courses_from_list(html: str) -> list[CgCourse] | None:
    return _courses(
        HTMLParser(html).css('a[href*="courselist.jsp?courseID="]'),
        lambda node: _after(node.attributes["href"], "courselist.jsp?courseID="),
    )


def courses_from_main(html: str) -> list[CgCourse] | None:
    return _courses(
        HTMLParser(html).css("span.dropdown-item-course"),
        lambda node: node.attributes.get("value"),
    )


def assignments(html: str) -> list[CgAssignment] | None:
    result = []
    for block in HTMLParser(html).css("div.main-zy"):
        title, link = (
            block.css_first("p.main-title"),
            block.css_first('a[href*="assignID="]'),
        )
        if title is None or link is None:
            continue
        name = title.text().strip()
        id = _u32(_after(link.attributes["href"], "assignID="))
        if name and id is not None:
            result.append(CgAssignment(id=id, name=name))
    return result or None


def problems(html: str) -> list[CgProblem] | None:
    result = []
    for row in HTMLParser(html).css("table.table-striped tr"):
        links = row.css("a[href]")
        problem = next(
            (node for node in links if "programList.jsp" in (node.attributes["href"] or "")),
            None,
        )
        judge = next(
            (
                node
                for node in links
                if "judgeDetailsRedirect.jsp" in (node.attributes["href"] or "")
            ),
            None,
        )
        cells = row.css("td")
        if problem is None or judge is None or len(cells) < 2:
            continue
        index_text = _after(problem.attributes["href"], "proNum=")
        id_text = _after(judge.attributes["href"], "problemID=")
        index = _u32(index_text.split("&", 1)[0]) if index_text is not None else None
        id = _u32(id_text.split("&", 1)[0]) if id_text is not None else None
        title = problem.text().strip()
        try:
            score_text = cells[1].text().strip()
            if "_" in score_text:
                continue
            score = float(score_text)
        except ValueError:
            continue
        if index is not None and id is not None and title and math.isfinite(score):
            result.append(CgProblem(index=index, id=id, title=title, score=score))
    return result or None
