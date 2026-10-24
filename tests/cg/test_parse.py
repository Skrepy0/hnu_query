import pytest

from hnu_query.cg import parse


def test_courses_rust_fixtures(cg_text):
    result = parse.courses_from_list(cg_text("courselist.html"))
    assert [(c.id, c.name) for c in result] == [
        (1001, "高等数学"),
        (2002, "线性代数"),
        (3003, "程序设计基础"),
    ]
    dedup = parse.courses_from_list(cg_text("courselist_dup.html"))
    assert [(c.id, c.name) for c in dedup] == [(1001, "高等数学"), (2002, "线性代数")]
    assert [
        (c.id, c.name)
        for c in parse.courses_from_main(cg_text("main_single_course.html"))
    ] == [(1001, "高等数学")]


def test_assignments_rust_fixture(cg_text):
    assert [
        (a.id, a.name) for a in parse.assignments(cg_text("assignment_list.html"))
    ] == [(5001, "作业一"), (5002, "作业二"), (5003, "作业三")]


def test_problems_rust_fixture(cg_text):
    result = parse.problems(cg_text("problem_list.html"))
    assert [p.model_dump() for p in result] == [
        {"index": 1, "id": 20001, "title": "第一题", "score": 100.0},
        {"index": 2, "id": 20002, "title": "第二题", "score": 50.0},
        {"index": 3, "id": 20003, "title": "第三题", "score": 75.5},
    ]


@pytest.mark.parametrize(
    "parser",
    [
        parse.courses_from_list,
        parse.courses_from_main,
        parse.assignments,
        parse.problems,
    ],
)
@pytest.mark.parametrize("html", ["", "<html><body>没有记录</body></html>"])
def test_empty_lists_return_none(parser, html):
    assert parser(html) is None


def test_course_invalid_rows_are_skipped_and_nested_text_joined():
    html = """<a href="courselist.jsp?courseID=1"> A<b>B</b> </a>
    <a href="courselist.jsp?courseID=1">duplicate</a>
    <a href="courselist.jsp?courseID=-1">negative</a>
    <a href="courselist.jsp?courseID=4294967296">overflow</a>
    <a href="courselist.jsp?courseID=2&extra=1">unknown suffix</a>
    <a href="courselist.jsp?courseID=3"> </a>"""
    assert [c.model_dump() for c in parse.courses_from_list(html)] == [
        {"id": 1, "name": "AB"}
    ]


def test_main_course_dedup_and_bad_id():
    html = """<span class="dropdown-item-course" value="1">one</span>
    <span class="dropdown-item-course" value="1">duplicate</span>
    <span class="dropdown-item-course">missing</span>
    <span class="dropdown-item-course" value="bad">bad</span>"""
    assert [c.name for c in parse.courses_from_main(html)] == ["one"]


def test_assignment_missing_title_or_link_skipped():
    html = """<div class="main-zy"><p class="main-title">one</p><a href="index.jsp?assignID=1">link</a></div>
    <div class="main-zy"><a href="index.jsp?assignID=2">no title</a></div>
    <div class="main-zy"><p class="main-title">no link</p></div>
    <div class="main-zy"><p class="main-title"> </p><a href="index.jsp?assignID=3">blank</a></div>"""
    assert [a.model_dump() for a in parse.assignments(html)] == [
        {"id": 1, "name": "one"}
    ]


@pytest.mark.parametrize(
    "old,new",
    [
        ("proNum=1", "proNum=bad"),
        ("problemID=20001", "problemID=-1"),
        ("100.00", "not-score"),
        ("100.00", "NaN"),
        ("第一题", " "),
        ("judgeDetailsRedirect.jsp?assignID=1001&problemID=20001", "other.jsp"),
    ],
)
def test_bad_problem_row_skipped(cg_text, old, new):
    result = parse.problems(cg_text("problem_list.html").replace(old, new, 1))
    assert [p.index for p in result] == [2, 3]


def test_problem_html_fixture(cg_text):
    body = cg_text("problem_page.html")
    assert "cgProblemContentClass" in body and "uploadFORM" in body
