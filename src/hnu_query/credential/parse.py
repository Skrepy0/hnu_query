# src/hnu_query/credential/parse.py（续）
import io
import json
import re

from hnu_query.credential.exceptions import CaParseError

from .models import Rank

#: 与 Rust 完全一致的正则
_RANK_RE = re.compile(
    r"平均学分绩点排名 ([0-9/]+)"
    r".*平均学分绩点 ([0-9.]+)"
    r".*核心课程平均学分绩点排名 ([0-9/]+)"
    r".*必修课平均学分绩点 ([0-9.]+)"
    r".*课程算术平均成绩排名 ([0-9/]+)"
    r".*算术平均分 ([0-9.]+)"
    r".*核心课程算术平均成绩排名 ([0-9/]+)"
    r".*必修课算术平均分 ([0-9.]+)"
    r".*学分加权平均成绩排名 ([0-9/]+)"
    r".*加权平均分 ([0-9.]+)"
    r".*核心课程学分加权平均成绩排名 ([0-9/]+)"
    r".*必修课加权平均分 ([0-9.]+)",
    re.DOTALL,  # ← 对应 Rust 的 dot_matches_new_line(true)
)


def preview_file_name(json_str: str) -> str:
    """从 ``preview_file`` 返回的 JSON 中提取真实文件名。

    对应 Rust ``ca::parse::preview_file_name``。

    Args:
        json_str: ``preview_file`` 返回的 JSON 字符串。

    Returns:
        ``message`` 字段的值，即真实文件名。

    Raises:
        CaParseError: code 不是 200，或 message 字段缺失。
    """
    try:
        data = json.loads(json_str)
    except ValueError as e:
        raise CaParseError("preview_file 返回非 JSON") from e

    if not isinstance(data, dict):
        raise CaParseError("preview_file 响应不是对象")
    if type(data.get("code")) is not int or data["code"] != 200:
        raise CaParseError("无法解析响应代码")

    message = data.get("message")
    if not isinstance(message, str):
        raise CaParseError("无法解析文件名")

    return message


def _extract_pdf_text(pdf_bytes: bytes) -> str:
    """从 PDF 字节中提取纯文本。

    对应 Rust ``pdf_extract::extract_text_from_mem``。
    """
    import pdfplumber

    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            return "\n".join(page.extract_text() or "" for page in pdf.pages)
    except Exception as e:
        raise CaParseError(f"PDF 文本提取失败: {e}") from e


def parse_rank(pdf_bytes: bytes) -> Rank:
    """从可信电子凭证 PDF 中解析成绩排名。

    对应 Rust ``ca::parse::rank``。
    """
    text = _extract_pdf_text(pdf_bytes)
    return _parse_rank_from_text(text)


def _parse_rank_from_text(pdf_text: str) -> Rank:
    """从已提取的 PDF 文本里解析排名。

    对应 Rust ``ca::parse::rank_with_pdf_text``（单独抽出便于测试）。
    """
    m = _RANK_RE.search(pdf_text)
    if not m:
        raise CaParseError("正则匹配失败")

    # 12 个捕获组，顺序和 Rust 完全一致
    (
        all_gpa_rank,
        all_gpa,
        core_gpa_rank,
        must_gpa,
        all_arithmetic_rank,
        all_arithmetic,
        core_arithmetic_rank,
        must_arithmetic,
        all_weighted_rank,
        all_weighted,
        core_weighted_rank,
        must_weighted,
    ) = m.groups()

    return Rank(
        all_gpa=all_gpa,
        all_gpa_rank=all_gpa_rank,
        all_weighted=all_weighted,
        all_weighted_rank=all_weighted_rank,
        all_arithmetic=all_arithmetic,
        all_arithmetic_rank=all_arithmetic_rank,
        must_gpa=must_gpa,
        must_weighted=must_weighted,
        must_arithmetic=must_arithmetic,
        core_gpa_rank=core_gpa_rank,
        core_arithmetic_rank=core_arithmetic_rank,
        core_weighted_rank=core_weighted_rank,
    )
