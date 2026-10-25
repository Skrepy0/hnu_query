"""可信电子凭证文件查询，复用客户端请求逻辑。"""

from .client import CaClient
from .token import CaToken


async def preview_file(ca_token: CaToken, template_id: str) -> str:
    """预览凭证，返回 JSON 字符串。"""
    async with CaClient(ca_token) as client:
        return await client.preview_file(template_id)


async def file(ca_token: CaToken, file_name: str) -> bytes:
    """下载凭证文件，返回文件字节。"""
    async with CaClient(ca_token) as client:
        return await client.file(file_name)
