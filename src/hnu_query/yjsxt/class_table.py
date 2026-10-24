from .client import YjsxtClient
from .models import Course, CourseSchedule
from .token import YjsxtToken

__all__ = ["Course", "CourseSchedule", "get_class_table"]


async def get_class_table(yjsxt_token: YjsxtToken, semester_id: str) -> list[Course]:
    async with YjsxtClient(yjsxt_token) as client:
        return await client.get_class_table(semester_id)
