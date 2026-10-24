from .client import GymClient
from .models import EyeGrade, Grade, GradeItem, GradeItemColor
from .token import GymToken

__all__ = ["EyeGrade", "Grade", "GradeItem", "GradeItemColor", "get_grade"]


async def get_grade(gym_token: GymToken, xn: int) -> Grade:
    async with GymClient(gym_token) as client:
        return await client.get_grade(xn)
