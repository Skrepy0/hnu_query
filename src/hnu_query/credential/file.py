import httpx

from .token import CaToken
from .exceptions import CaNetworkError, CaStatusError

BASE_URL = "https://ca.hnu.edu.cn"
_TIMEOUT = httpx.Timeout(60.0)


async def preview_file(
    ca_token: CaToken,
    template_id: str,
    *,
    client: httpx.AsyncClient | None = None,
) -> str:
    """预览指定模板的凭证页面，返回 HTML 文本。

    对应 Rust ``ca::file::preview_file``。
    """
    owns = client is None
    if owns:
        client = httpx.AsyncClient(
            base_url=BASE_URL,
            headers=ca_token.headers,
            timeout=_TIMEOUT,
            follow_redirects=True,
        )

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
        if resp.status_code >= 400:
            raise CaStatusError(resp.status_code, resp.text[:200])
        return resp.text
    except httpx.RequestError as e:
        raise CaNetworkError(str(e)) from e
    finally:
        if owns:
            await client.aclose()


async def file(
    ca_token: CaToken,
    file_name: str,
    *,
    client: httpx.AsyncClient | None = None,
) -> bytes:
    """下载凭证文件（通常是 PDF），返回字节内容。

    对应 Rust ``ca::file::file``。

    ``file_name`` 来自 :func:`preview_file_name` 的返回值。
    """
    from urllib.parse import quote

    owns = client is None
    if owns:
        client = httpx.AsyncClient(
            base_url=BASE_URL,
            headers=ca_token.headers,
            timeout=_TIMEOUT,
            follow_redirects=True,
        )

    try:
        safe_name = quote(file_name, safe="")
        resp = await client.get(f"/student/sys/common/view/{safe_name}")
        if resp.status_code >= 400:
            raise CaStatusError(resp.status_code, resp.text[:200])
        return resp.content
    except httpx.RequestError as e:
        raise CaNetworkError(str(e)) from e
    finally:
        if owns:
            await client.aclose()