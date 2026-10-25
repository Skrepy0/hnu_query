from .client import HdjwClient
from .models import Grade, GradeDetailItem
from .token import HdjwToken

__all__ = ["Grade", "GradeDetailItem", "get_grade", "get_grade_detail"]


async def get_grade(hdjw_token: HdjwToken, xn: int, xq: int) -> list[Grade]:
    async with HdjwClient(hdjw_token) as client:
        return await client.get_grade(xn, xq)


async def get_grade_detail(hdjw_token: HdjwToken, jx0404id: str) -> list[GradeDetailItem]:
    async with HdjwClient(hdjw_token) as client:
        return await client.get_grade_detail(jx0404id)
