from .client import XgxtClient
from .dormitory import Dormitory, parse_dormitory
from .models import Gender, Level, PersonalInfo
from .token import XgxtToken

__all__ = [
    "Dormitory",
    "Gender",
    "Level",
    "PersonalInfo",
    "get_person_info",
    "parse_dormitory",
]


async def get_person_info(xgxt_token: XgxtToken) -> PersonalInfo:
    async with XgxtClient(xgxt_token) as client:
        return await client.get_person_info()
