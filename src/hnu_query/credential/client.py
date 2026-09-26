import httpx

from .exceptions import CaNetworkError, CaStatusError
from .token import CaToken

BASE_URL = "https://ca.hnu.edu.cn"
_TIMEOUT = httpx.Timeout(60.0)


class CaClient:
    """可信电子凭证平台客户端。

    用法::

        async with CaClient(token) as client:
            html = await client.preview_file("template-id")
            pdf = await client.file("file-name")
    """

    def __init__(
            self,
            token: CaToken,
            *,
            client: httpx.AsyncClient | None = None,
    ) -> None:
        self._token = token
        self._client = client or httpx.AsyncClient(
            base_url=BASE_URL,
            headers=token.headers,
            timeout=_TIMEOUT,
            follow_redirects=True,
        )
        self._owns_client = client is None

    # ---------- 公开 API ----------

    async def preview_file(self, template_id: str) -> str:
        """预览指定模板的凭证页面，返回 HTML 文本。

        对应 Rust ``ca::file::preview_file``。

        Args:
            template_id: 模板 ID，通常来自凭证列表接口。

        Returns:
            预览页面的 HTML 文本，需再解析出真实文件名。
        """
        params = {
            "templateId": template_id,
            "isbzf": "0",
            "kcxz": "",
            "xfjd": "",
            "xzkc": "",
        }
        resp = await self._request("GET", "/student/student/caTemplate/preview_file", params=params)
        return resp.text

    async def file(self, file_name: str) -> bytes:
        """下载凭证文件（通常是 PDF），返回字节内容。

        对应 Rust ``ca::file::file``。

        Args:
            file_name: 文件名，来自 ``preview_file`` 返回页面的解析结果。
        """
        resp = await self._request("GET", f"/student/sys/common/view/{file_name}")
        return resp.content

    # ---------- 内部 ----------

    async def _request(self, method: str, url: str, **kwargs) -> httpx.Response:
        try:
            resp = await self._client.request(method, url, **kwargs)
        except httpx.RequestError as e:
            raise CaNetworkError(str(e)) from e

        if resp.status_code >= 400:
            raise CaStatusError(resp.status_code, resp.text[:200])

        return resp

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def __aenter__(self) -> "CaClient":
        return self

    async def __aexit__(self, *exc) -> None:
        await self.aclose()
