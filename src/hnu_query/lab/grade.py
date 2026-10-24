from .client import LabClient
from .models import LabGrade, LabGradeDetailItem, VirtualLabGrade
from .token import LabToken

__all__ = [
    "LabGrade",
    "LabGradeDetailItem",
    "VirtualLabGrade",
    "get_lab_grade",
    "get_virtual_lab_grade",
]


async def get_lab_grade(
    lab_token: LabToken, course_id: str, semester_id: str
) -> list[LabGrade]:
    async with LabClient(lab_token) as client:
        return await client.get_lab_grade(course_id, semester_id)


async def get_virtual_lab_grade(lab_token: LabToken) -> list[VirtualLabGrade]:
    async with LabClient(lab_token) as client:
        return await client.get_virtual_lab_grade()
