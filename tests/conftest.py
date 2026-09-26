import pytest

from hnu_query.cas import CasToken
from hnu_query.credential import CaToken

CAS_BASE = "http://cas.hnu.edu.cn"
PUBKEY_URL = f"{CAS_BASE}/cas/v2/getPubKey"
SERVICE_URL = (
    f"{CAS_BASE}/cas/login"
    "?service=http://cas.hnu.edu.cn/system/login/login.zf"
)


@pytest.fixture
def ca_token() -> CaToken:
    """一个携带伪造 Cookie 的 CaToken。"""
    return CaToken(headers={"Cookie": "JSESSIONID=test-session-id"})


@pytest.fixture
def cas_token() -> CasToken:
    """一个持伪造 Cookie 的 CasToken。"""
    return CasToken(
        cookie="TGC=tgt-fake; JSESSIONID=js-fake",
        stu_id="20210001",
    )


@pytest.fixture
def pubkey_url() -> str:
    return PUBKEY_URL


@pytest.fixture
def service_url() -> str:
    return SERVICE_URL


@pytest.fixture
def sample_preview_html() -> str:
    """模拟 preview_file 返回的 HTML，内含下载链接。"""
    return """
    <!DOCTYPE html>
    <html>
    <head><title>预览</title></head>
    <body>
        <h1>可信电子凭证预览</h1>
        <a href="/student/sys/common/view/abc123.pdf">下载</a>
    </body>
    </html>
    """


@pytest.fixture
def sample_preview_html_iframe() -> str:
    """模拟用 iframe 承载下载链接的 HTML。"""
    return """
    <html><body>
        <iframe src="/student/sys/common/view/xyz789.pdf"></iframe>
    </body></html>
    """


@pytest.fixture
def sample_preview_html_no_link() -> str:
    """模拟不含下载链接的 HTML。"""
    return "<html><body><p>暂无凭证</p></body></html>"
