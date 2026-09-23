# src/hnu_query/ca/grade_rank.py
import httpx

from .token import CaToken
from .exceptions import CaNetworkError, CaStatusError, CaParseError

BASE_URL = "https://ca.hnu.edu.cn"
_TIMEOUT = httpx.Timeout(60.0)


async def get_grade_rank(
    ca_token: CaToken,
    *,
    year: int,
    term: int,
) -> str:
    """获取本科生主修课程的可信电子凭证排名信息。

    对应 Rust ``ca::grade_rank::get_grade_rank``。

    Args:
        ca_token: CA 平台访问令牌。
        year: 学年，如 2025。
        term: 学期，1 或 2。

    Returns:
        排名页面的 HTML 文本，需进一步解析。
    """
    async with httpx.AsyncClient(
        base_url=BASE_URL,
        headers=ca_token.headers,
        timeout=_TIMEOUT,
        follow_redirects=True,
    ) as client:
        try:
            resp = await client.get(
                "/student/student/caTemplate/grade_rank",
                params={"year": year, "term": term},
            )
            if resp.status_code >= 400:
                raise CaStatusError(resp.status_code, resp.text[:200])
            return resp.text
        except httpx.RequestError as e:
            raise CaNetworkError(str(e)) from e