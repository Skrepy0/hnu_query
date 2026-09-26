import httpx

from hnu_query.cas import extract_ticket, get_ticket_url
from .exceptions import CaLoginError, CaNetworkError, CaStatusError
from .token import CaToken

CA_URL = "http://cas.hnu.edu.cn/cas/login?service=https://ca.hnu.edu.cn/student/"


async def acquire_by_cas_login(cas_token) -> CaToken:
    """通过 CAS 换取 CA 平台的 X-Access-Token。

    对应 Rust ``CaToken::acquire_by_cas_login``。
    """
    # ① 向 CAS 申请指向 CA 的 ticket_url
    ticket_url = await get_ticket_url(cas_token, CA_URL)

    # ② 从 URL 里提取 ticket
    ticket = extract_ticket(ticket_url)

    # ③④ 同一个 client 完成「GET ticket_url → validateLogin」
    #    这样 CA 下发的会话 Cookie 会自动带到 validateLogin
    async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=30.0,
    ) as client:
        # ③ 访问 ticket_url，建立 CA 会话（CA 会 Set-Cookie）
        try:
            r = await client.get(ticket_url)
        except httpx.RequestError as e:
            raise CaNetworkError(str(e)) from e
        if r.status_code >= 400:
            raise CaStatusError(r.status_code, r.text[:200])

        # ④ 用 ticket 换 X-Access-Token
        validate_url = (
            "https://ca.hnu.edu.cn/student/cas/client/validateLogin"
            f"?ticket={ticket}%23%2F"
            "&service=https:%2F%2Fca.hnu.edu.cn%2Fstudent%2F"
        )
        try:
            resp = await client.get(validate_url)
        except httpx.RequestError as e:
            raise CaNetworkError(str(e)) from e

    # 此时 client 已关闭，但 resp 内容还在
    if resp.status_code >= 400:
        raise CaStatusError(resp.status_code, resp.text[:200])

    # CA 在 ticket 无效时返回 HTML 登录页，而不是 JSON —— 提前判断
    content_type = resp.headers.get("content-type", "")
    if "json" not in content_type.lower():
        raise CaLoginError(
            f"validateLogin 返回非 JSON（可能 ticket 失效）: {resp.text[:200]}"
        )

    try:
        data = resp.json()
    except ValueError as e:
        raise CaLoginError(f"validateLogin 返回非 JSON: {resp.text[:200]}") from e

    if data.get("message") != "登录成功":
        raise CaLoginError(f"登录失败: {data.get('message')}")

    token = (data.get("result") or {}).get("token")
    if not token:
        raise CaLoginError(f"找不到 token: {resp.text[:200]}")

    return CaToken(headers={
        "X-Access-Token": token,
        "Cookie": f"X-Access-Token={token}",
    })
