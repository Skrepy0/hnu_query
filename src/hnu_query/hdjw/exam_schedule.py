from .client import HdjwClient
from .models import ExamSchedule
from .token import HdjwToken

__all__ = ["ExamSchedule", "get_exam_schedule"]


async def get_exam_schedule(hdjw_token: HdjwToken, xn: int, xq: int) -> list[ExamSchedule]:
    async with HdjwClient(hdjw_token) as client:
        return await client.get_exam_schedule(xn, xq)
