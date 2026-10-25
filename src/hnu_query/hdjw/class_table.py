from .client import HdjwClient
from .models import Course, CourseSchedule, ExtraCourse
from .token import HdjwToken

__all__ = [
    "Course",
    "CourseSchedule",
    "ExtraCourse",
    "get_class_table",
    "get_class_table_extra",
]


async def get_class_table(hdjw_token: HdjwToken, xn: int, xq: int) -> list[Course]:
    async with HdjwClient(hdjw_token) as client:
        return await client.get_class_table(xn, xq)


async def get_class_table_extra(hdjw_token: HdjwToken, xn: int, xq: int) -> list[ExtraCourse]:
    async with HdjwClient(hdjw_token) as client:
        return await client.get_class_table_extra(xn, xq)
