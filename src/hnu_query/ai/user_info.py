from .client import AiClient
from .token import AiToken


async def get_user_remaining_quota(token: AiToken) -> int:
    async with AiClient(token) as client:
        return await client.get_user_remaining_quota()
