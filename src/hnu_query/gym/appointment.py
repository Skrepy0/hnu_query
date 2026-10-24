from .client import GymClient
from .models import Appointment
from .token import GymToken

__all__ = ["Appointment", "get_appointment"]


async def get_appointment(gym_token: GymToken) -> list[Appointment]:
    async with GymClient(gym_token) as client:
        return await client.get_appointment()
