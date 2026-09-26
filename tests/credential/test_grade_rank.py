import httpx
import pytest
import respx

from hnu_query.credential import get_grade_rank
from hnu_query.credential.exceptions import CaNetworkError, CaStatusError
from hnu_query.credential.grade_rank import UNDERGRADUATE_MAJOR_ALL_TEMPLATE_ID
from hnu_query.credential.models import Rank

BASE = "https://ca.hnu.edu.cn"

#: preview_file 返回的 JSON
_PREVIEW_JSON = '{"code": 200, "message": "abc123.pdf"}'

#: 伪造的 PDF 字节（内容不重要，parse_rank 会被 mock 掉）
_FAKE_PDF = b"%PDF-1.4 fake"

#: 期望的解析结果
_FAKE_RANK = Rank(
    all_gpa="4.0",
    all_gpa_rank="30/90",
    all_weighted="86",
    all_weighted_rank="34/90",
    all_arithmetic="90",
    all_arithmetic_rank="32/90",
    must_gpa="3.8",
    must_weighted="84",
    must_arithmetic="88",
    core_gpa_rank="31/90",
    core_arithmetic_rank="33/90",
    core_weighted_rank="35/90",
)


@pytest.mark.asyncio
@respx.mock
async def test_get_grade_rank_success(ca_token, monkeypatch):
    """完整链路：preview_file → preview_file_name → file → parse_rank。"""
    # ① mock preview_file
    respx.get(
        f"{BASE}/student/student/caTemplate/preview_file",
        params={
            "templateId": UNDERGRADUATE_MAJOR_ALL_TEMPLATE_ID,
            "isbzf": "0", "kcxz": "", "xfjd": "", "xzkc": "",
        },
    ).mock(return_value=httpx.Response(200, text=_PREVIEW_JSON))

    # ② mock file
    respx.get(
        f"{BASE}/student/sys/common/view/abc123.pdf"
    ).mock(return_value=httpx.Response(200, content=_FAKE_PDF))

    # ③ mock parse_rank（避免依赖真实 PDF 解析）
    monkeypatch.setattr(
        "hnu_query.credential.grade_rank.parse_rank",
        lambda pdf_bytes: _FAKE_RANK,
    )

    result = await get_grade_rank(ca_token)

    assert result == _FAKE_RANK
    assert result.all_gpa == "4.0"
    assert result.all_gpa_rank == "30/90"


@pytest.mark.asyncio
@respx.mock
async def test_get_grade_rank_preview_401(ca_token):
    """preview_file 返回 401 → CaStatusError。"""
    respx.get(
        f"{BASE}/student/student/caTemplate/preview_file"
    ).mock(return_value=httpx.Response(401, text="Token expired"))

    with pytest.raises(CaStatusError) as exc:
        await get_grade_rank(ca_token)

    assert exc.value.status_code == 401


@pytest.mark.asyncio
@respx.mock
async def test_get_grade_rank_file_400(ca_token, monkeypatch):
    """file 返回 400 → CaStatusError。"""
    respx.get(
        f"{BASE}/student/student/caTemplate/preview_file"
    ).mock(return_value=httpx.Response(200, text=_PREVIEW_JSON))

    respx.get(
        f"{BASE}/student/sys/common/view/abc123.pdf"
    ).mock(return_value=httpx.Response(400, text="Bad Request"))

    monkeypatch.setattr(
        "hnu_query.credential.grade_rank.parse_rank",
        lambda pdf_bytes: _FAKE_RANK,
    )

    with pytest.raises(CaStatusError) as exc:
        await get_grade_rank(ca_token)

    assert exc.value.status_code == 400


@pytest.mark.asyncio
@respx.mock
async def test_get_grade_rank_network_error(ca_token):
    """preview_file 网络失败 → CaNetworkError。"""
    respx.get(
        f"{BASE}/student/student/caTemplate/preview_file"
    ).mock(side_effect=httpx.ReadTimeout("read timeout"))

    with pytest.raises(CaNetworkError):
        await get_grade_rank(ca_token)


@pytest.mark.asyncio
@respx.mock
async def test_get_grade_rank_bad_code(ca_token):
    """preview_file 返回 code != 200 → CaParseError。"""
    from hnu_query.credential.exceptions import CaParseError

    respx.get(
        f"{BASE}/student/student/caTemplate/preview_file"
    ).mock(return_value=httpx.Response(200, text='{"code": 500, "message": "error"}'))

    with pytest.raises(CaParseError):
        await get_grade_rank(ca_token)
