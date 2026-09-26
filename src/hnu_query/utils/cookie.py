def cookie_parser(set_cookie_headers: list[str]) -> list[str]:
    """从一组 Set-Cookie 头中提取 ``name=value`` 列表。

    对应 Rust ``utils::request::cookie_parser``。

    只保留第一个分号之前的部分，丢弃 Path、HttpOnly 等属性。
    """
    cookies: list[str] = []
    for header in set_cookie_headers:
        name_value = header.split(";", 1)[0].strip()
        if name_value:
            cookies.append(name_value)
    return cookies
