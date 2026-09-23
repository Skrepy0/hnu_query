# tests/ca/test_grade_rank.py
import httpx
import pytest
import respx

from hnu_query.credential import get_grade_rank
from hnu_query.credential.exceptions import CaNetworkError, CaStatusError

BASE = "https://ca.hnu.edu.cn"


@pytest.mark.asyncio
@respx.mock
async def test_get_grade_rank_success(ca_token):
    html = "<html><body>排名数据</body></html>"
    route = respx.get(
        f"{BASE}/student/student/caTemplate/grade_rank",
        params={"year": "2025", "term": "1"},
    ).mock(return_value=httpx.Response(200, text=html))

    result = await get_grade_rank(ca_token, year=2025, term=1)

    assert result == html
    assert route.called


@pytest.mark.asyncio
@respx.mock
async def test_get_grade_rank_unauthorized(ca_token):
    respx.get(
        f"{BASE}/student/student/caTemplate/grade_rank"
    ).mock(return_value=httpx.Response(401, text="Token expired"))

    with pytest.raises(CaStatusError) as exc_info:
        await get_grade_rank(ca_token, year=2025, term=1)

    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
@respx.mock
async def test_get_grade_rank_timeout(ca_token):
    respx.get(
        f"{BASE}/student/student/caTemplate/grade_rank"
    ).mock(side_effect=httpx.ReadTimeout("read timeout"))

    with pytest.raises(CaNetworkError):
        await get_grade_rank(ca_token, year=2025, term=1)