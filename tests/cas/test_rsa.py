from hnu_query.utils.rsa import rsa_encrypt

#: 小公钥便于手算：模数 0xbf=191，指数 0x03=3
_SMALL_MODULUS = "00bf"
_SMALL_EXPONENT = "03"


def test_rsa_encrypt_single_byte():
    """字节 \\x05 对应整数 5，5^3 mod 191 = 125 = 0x7d。"""
    result = rsa_encrypt("\x05", _SMALL_EXPONENT, _SMALL_MODULUS)
    assert result is not None
    assert result.endswith("7d")
    assert len(result) == 128


def test_rsa_encrypt_ascii_digit():
    """ASCII '5' = 0x35 = 53，53^3 mod 191 = 88 = 0x58。"""
    result = rsa_encrypt("5", _SMALL_EXPONENT, _SMALL_MODULUS)
    assert result is not None
    assert result.endswith("58")
    assert len(result) == 128


def test_rsa_encrypt_padding():
    """结果必须是 128 位十六进制。"""
    result = rsa_encrypt("password", "10001", "00bf")
    assert result is not None
    assert len(result) == 128
    assert all(c in "0123456789abcdef" for c in result)


def test_rsa_encrypt_deterministic():
    """同样输入结果必须一致。"""
    r1 = rsa_encrypt("hello", _SMALL_EXPONENT, _SMALL_MODULUS)
    r2 = rsa_encrypt("hello", _SMALL_EXPONENT, _SMALL_MODULUS)
    assert r1 == r2


def test_rsa_encrypt_empty_password():
    """空密码对应整数 0，加密后仍是 0。"""
    result = rsa_encrypt("", _SMALL_EXPONENT, _SMALL_MODULUS)
    assert result == "0" * 128


def test_rsa_encrypt_invalid_modulus():
    assert rsa_encrypt("password", "zz", "qq") is None


def test_rsa_encrypt_invalid_exponent():
    assert rsa_encrypt("password", "not-hex", _SMALL_MODULUS) is None


def test_rsa_encrypt_chinese_password():
    """含中文的密码按 UTF-8 编码后计算。"""
    result = rsa_encrypt("密码", _SMALL_EXPONENT, _SMALL_MODULUS)
    assert result is not None
    assert len(result) == 128
