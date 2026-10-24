from collections.abc import Sequence

from .client import HdjwClient
from .models import EmptyClassroom
from .token import HdjwToken

__all__ = ["EmptyClassroom", "get_empty_classroom"]


async def get_empty_classroom(
    hdjw_token: HdjwToken,
    building_id: str,
    week: int,
    day: int,
    time: Sequence[int],
    xn: int,
    xq: int,
) -> list[EmptyClassroom]:
    async with HdjwClient(hdjw_token) as client:
        return await client.get_empty_classroom(building_id, week, day, time, xn, xq)
