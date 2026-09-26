import httpx
import pytest
import respx

from hnu_query.credential import CaNetworkError, preview_file, file, CaStatusError

BASE = "https://ca.hnu.edu.cn"


@pytest.mark.asyncio
@respx.mock
async def test_preview_file_success(ca_token, sample_preview_html):
    route = respx.get(
        f"{BASE}/student/student/caTemplate/preview_file",
        params={
            "templateId": "tpl-001",
            "isbzf": "0",
            "kcxz": "",
            "xfjd": "",
            "xzkc": "",
        },
    ).mock(return_value=httpx.Response(200, text=sample_preview_html))

    from hnu_query.credential import preview_file
    result = await preview_file(ca_token, "tpl-001")

    assert result == sample_preview_html
    assert route.called
    # 校验认证头确实带上了
    request = route.calls.last.request
    assert request.headers["Cookie"] == "JSESSIONID=test-session-id"


@pytest.mark.asyncio
@respx.mock
async def test_preview_file_status_error(ca_token):
    respx.get(
        f"{BASE}/student/student/caTemplate/preview_file"
    ).mock(return_value=httpx.Response(401, text="Unauthorized"))

    with pytest.raises(CaStatusError) as exc_info:
        await preview_file(ca_token, "tpl-001")

    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
@respx.mock
async def test_preview_file_network_error(ca_token):
    respx.get(
        f"{BASE}/student/student/caTemplate/preview_file"
    ).mock(side_effect=httpx.ConnectError("connection refused"))

    with pytest.raises(CaNetworkError):
        await preview_file(ca_token, "tpl-001")


@pytest.mark.asyncio
@respx.mock
async def test_file_success(ca_token):
    pdf_bytes = b"%PDF-1.4 fake pdf content"
    route = respx.get(
        f"{BASE}/student/sys/common/view/abc123.pdf"
    ).mock(return_value=httpx.Response(200, content=pdf_bytes))

    result = await file(ca_token, "abc123.pdf")

    assert result == pdf_bytes
    assert route.called


@pytest.mark.asyncio
@respx.mock
async def test_file_url_encodes_name(ca_token):
    """文件名中的特殊字符应被 URL 编码。"""
    route = respx.get(
        f"{BASE}/student/sys/common/view/a%20b.pdf"
    ).mock(return_value=httpx.Response(200, content=b"pdf"))

    result = await file(ca_token, "a b.pdf")

    assert result == b"pdf"
    assert route.called


@pytest.mark.asyncio
@respx.mock
async def test_file_status_error(ca_token):
    respx.get(
        f"{BASE}/student/sys/common/view/missing.pdf"
    ).mock(return_value=httpx.Response(404, text="Not Found"))

    with pytest.raises(CaStatusError) as exc_info:
        await file(ca_token, "missing.pdf")

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
@respx.mock
async def test_file_follows_redirect(ca_token):
    """下载接口可能 302 到 CDN，应自动跟随。"""
    respx.get(
        f"{BASE}/student/sys/common/view/abc123.pdf"
    ).mock(return_value=httpx.Response(302, headers={"Location": "https://cdn.example.com/f.pdf"}))
    respx.get("https://cdn.example.com/f.pdf").mock(
        return_value=httpx.Response(200, content=b"from cdn")
    )

    result = await file(ca_token, "abc123.pdf")
    assert result == b"from cdn"
