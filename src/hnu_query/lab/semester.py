from .client import LabClient
from .models import Semester
from .token import LabToken

__all__ = ["Semester", "get_semester"]


async def get_semester(lab_token: LabToken) -> list[Semester]:
    async with LabClient(lab_token) as client:
        return await client.get_semester()
