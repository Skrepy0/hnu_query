from urllib.parse import quote, urljoin, urlsplit

import httpx

from .exceptions import CaLoginError, CaNetworkError, CaStatusError
from .token import CaToken

BASE_URL = "https://ca.hnu.edu.cn"
_TIMEOUT = httpx.Timeout(60.0)


class CaClient:
    """可信电子凭证平台客户端。

    用法::

        async with CaClient(token) as client:
            preview_json = await client.preview_file("template-id")
            pdf = await client.file("file-name")
    """

    def __init__(
        self,
        token: CaToken,
        *,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._token = token
        self._client = (
            client
            if client is not None
            else httpx.AsyncClient(
                base_url=BASE_URL,
                timeout=_TIMEOUT,
                follow_redirects=False,
            )
        )
        self._owns_client = client is None

    # ---------- 公开 API ----------

    async def preview_file(self, template_id: str) -> str:
        """预览指定模板的凭证，返回 JSON 字符串。

        对应 Rust ``ca::grade_rank::fetch::preview_file``。

        Args:
            template_id: 模板 ID，通常来自凭证列表接口。

        Returns:
            JSON 文本，使用 preview_file_name 解析出真实文件名。
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

        对应 Rust ``ca::grade_rank::fetch::file``。

        Args:
            file_name: 文件名，来自 ``preview_file`` 返回 JSON 的解析结果。
        """
        resp = await self._request("GET", f"/student/sys/common/view/{quote(file_name, safe='/')}")
        return resp.content

    # ---------- 内部 ----------

    async def _request(
        self, method: str, url: str, *, allowed_host: str | None = None, **kwargs
    ) -> httpx.Response:
        current = urljoin(BASE_URL, url)
        for attempt in range(11):
            try:
                target = urlsplit(current)
                port = target.port
                if (
                    target.scheme != "https"
                    or target.username is not None
                    or target.password is not None
                ):
                    raise ValueError
            except ValueError as exc:
                raise CaLoginError("凭证请求跳转地址无效") from exc
            if allowed_host is not None and (
                target.hostname != allowed_host or target.port not in (None, 443)
            ):
                raise CaLoginError("凭证登录跳转目标不属于凭证平台")
            # 注入连接同样显式设置认证头；跨域下载不携带凭证令牌。
            is_ca = target.hostname == "ca.hnu.edu.cn" and port in (None, 443)
            headers = dict(self._token.headers) if is_ca else {}
            try:
                request = self._client.build_request(method, current, headers=headers, **kwargs)
                if not is_ca:
                    for name in ("X-Access-Token", "Cookie", "Authorization"):
                        request.headers.pop(name, None)
                resp = await self._client.send(request, follow_redirects=False, auth=None)
            except httpx.RequestError as e:
                raise CaNetworkError("凭证网络请求失败") from e
            if resp.is_redirect:
                location = resp.headers.get("location")
                if not location or attempt == 10:
                    raise CaLoginError("凭证请求跳转缺失或次数超限")
                current = urljoin(current, location)
                if urlsplit(current).hostname == "cas.hnu.edu.cn":
                    raise CaLoginError("凭证会话失效，需要重新登录")
                kwargs.pop("params", None)
                continue
            if not 200 <= resp.status_code < 300:
                raise CaStatusError(resp.status_code)
            return resp
        raise CaLoginError("凭证请求跳转次数超限")

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def __aenter__(self) -> "CaClient":
        return self

    async def __aexit__(self, *exc) -> None:
        await self.aclose()
