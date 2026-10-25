from .client import AiClient
from .models import TokenInfo
from .token import AiToken


async def get_token_list(token: AiToken) -> list[TokenInfo]:
    async with AiClient(token) as client:
        return await client.get_token_list()


async def get_token_key(token: AiToken, id: int) -> str:
    async with AiClient(token) as client:
        return await client.get_token_key(id)


async def create_token(token: AiToken, name: str) -> None:
    async with AiClient(token) as client:
        await client.create_token(name)


async def delete_token(token: AiToken, id: int) -> None:
    async with AiClient(token) as client:
        await client.delete_token(id)
