from .client import LabClient
from .models import Course
from .token import LabToken

__all__ = ["Course", "get_course_list"]


async def get_course_list(lab_token: LabToken, semester_id: str) -> list[Course]:
    async with LabClient(lab_token) as client:
        return await client.get_course_list(semester_id)
