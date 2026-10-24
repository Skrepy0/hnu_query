from .client import YjsxtClient
from .models import Semester
from .token import YjsxtToken

__all__ = ["Semester", "get_semester"]


async def get_semester(yjsxt_token: YjsxtToken) -> list[Semester]:
    async with YjsxtClient(yjsxt_token) as client:
        return await client.get_semester()
