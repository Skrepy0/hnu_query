from .client import LabClient
from .models import LabSchedule
from .token import LabToken

__all__ = ["LabSchedule", "get_lab_schedule"]


async def get_lab_schedule(lab_token: LabToken) -> list[LabSchedule]:
    async with LabClient(lab_token) as client:
        return await client.get_lab_schedule()
