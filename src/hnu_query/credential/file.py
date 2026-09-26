# src/hnu_query/credential/file.py
import httpx

from .exceptions import CaNetworkError, CaStatusError
from .token import CaToken

BASE_URL = "https://ca.hnu.edu.cn"
_TIMEOUT = httpx.Timeout(60.0)


async def preview_file(ca_token: CaToken, template_id: str) -> str:
    """预览指定模板的凭证页面，返回 JSON 字符串。"""
    async with httpx.AsyncClient(
            base_url=BASE_URL,
            headers=ca_token.headers,
            timeout=_TIMEOUT,
            follow_redirects=True,
    ) as client:
        try:
            resp = await client.get(
                "/student/student/caTemplate/preview_file",
                params={
                    "templateId": template_id,
                    "isbzf": "0",
                    "kcxz": "",
                    "xfjd": "",
                    "xzkc": "",
                },
            )
        except httpx.RequestError as e:
            raise CaNetworkError(str(e)) from e
        if resp.status_code >= 400:
            raise CaStatusError(resp.status_code, resp.text[:200])
        return resp.text


async def file(ca_token: CaToken, file_name: str) -> bytes:
    """下载凭证文件（通常是 PDF）。"""
    async with httpx.AsyncClient(
            base_url=BASE_URL,
            headers=ca_token.headers,
            timeout=_TIMEOUT,
            follow_redirects=True,
    ) as client:
        try:
            resp = await client.get(f"/student/sys/common/view/{file_name}")
        except httpx.RequestError as e:
            raise CaNetworkError(str(e)) from e
        if resp.status_code >= 400:
            raise CaStatusError(resp.status_code, resp.text[:200])
        return resp.content
