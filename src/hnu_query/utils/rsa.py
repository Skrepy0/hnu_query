def rsa_encrypt(password: str, exponent: str, modulus: str) -> str | None:
    """模拟 JS 的 RSA 加密（用于正方 CAS 登录）。

    对应 Rust ``utils::rsa_encrypt``。

    Args:
        password: 明文密码。
        exponent: 公钥指数（十六进制字符串，如 ``"10001"``）。
        modulus: 公钥模数（十六进制字符串）。

    Returns:
        加密后的十六进制字符串，左补零到 128 位；失败返回 None。
    """
    try:
        password_int = int.from_bytes(password.encode("utf-8"), "big")
        e_int = int(exponent, 16)
        m_int = int(modulus, 16)
        if e_int < 0 or m_int <= 0:
            return None
        result_int = pow(password_int, e_int, m_int)
        return format(result_int, "x").zfill(128)
    except (ValueError, TypeError):
        return None
