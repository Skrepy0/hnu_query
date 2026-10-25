import pytest

from hnu_query.credential import preview_file_name
from hnu_query.credential.exceptions import CaParseError
from hnu_query.credential.parse import _parse_rank_from_text

# ---------- preview_file_name ----------


def test_preview_file_name_success():
    json_str = '{"code": 200, "message": "abc123.pdf"}'
    assert preview_file_name(json_str) == "abc123.pdf"


def test_preview_file_name_bad_code():
    json_str = '{"code": 500, "message": "abc123.pdf"}'
    with pytest.raises(CaParseError, match="响应代码"):
        preview_file_name(json_str)


def test_preview_file_name_missing_message():
    json_str = '{"code": 200}'
    with pytest.raises(CaParseError, match="文件名"):
        preview_file_name(json_str)


def test_preview_file_name_not_json():
    with pytest.raises(CaParseError, match="非 JSON"):
        preview_file_name("<html>not json</html>")


# ---------- parse_rank ----------

PDF_TEXT = """平均学分绩点排名 30/90
平均学分绩点 4.0
核心课程平均学分绩点排名 31/90
必修课平均学分绩点 3.8
课程算术平均成绩排名 32/90
算术平均分 90
核心课程算术平均成绩排名 33/90
必修课算术平均分 88
学分加权平均成绩排名 34/90
加权平均分 86
核心课程学分加权平均成绩排名 35/90
必修课加权平均分 84
"""


def test_parse_rank():
    rank = _parse_rank_from_text(PDF_TEXT)
    assert rank.all_gpa_rank == "30/90"
    assert rank.all_gpa == "4.0"
    assert rank.core_gpa_rank == "31/90"
    assert rank.must_gpa == "3.8"
    assert rank.all_arithmetic_rank == "32/90"
    assert rank.all_arithmetic == "90"
    assert rank.core_arithmetic_rank == "33/90"
    assert rank.must_arithmetic == "88"
    assert rank.all_weighted_rank == "34/90"
    assert rank.all_weighted == "86"
    assert rank.core_weighted_rank == "35/90"
    assert rank.must_weighted == "84"


def test_parse_rank_missing():
    with pytest.raises(CaParseError, match="正则匹配失败"):
        _parse_rank_from_text("完全无关的文本")
