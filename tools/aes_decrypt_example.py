"""
AES-128-CBC 解密範例
展示如何使用 cryptography 處理解密與 padding 異常
"""
from typing import Optional, Tuple
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.backends import default_backend
import os


def aes128_cbc_encrypt(plaintext: bytes, key: bytes, iv: bytes) -> bytes:
    """加密：先 PKCS7 padding，再 AES-CBC"""
    padder = padding.PKCS7(128).padder()
    padded = padder.update(plaintext) + padder.finalize()
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    return encryptor.update(padded) + encryptor.finalize()


def aes128_cbc_decrypt(ciphertext: bytes, key: bytes, iv: bytes) -> bytes:
    """解密：AES-CBC 解密後去除 PKCS7 padding"""
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    decryptor = cipher.decryptor()
    padded = decryptor.update(ciphertext) + decryptor.finalize()
    unpadder = padding.PKCS7(128).unpadder()
    return unpadder.update(padded) + unpadder.finalize()


def aes128_cbc_decrypt_safe(ciphertext: bytes, key: bytes, iv: bytes) -> Tuple[bool, Optional[bytes]]:
    """
    安全解密：捕捉 padding 異常
    回傳 (成功與否, 明文或 None)
    """
    try:
        plaintext = aes128_cbc_decrypt(ciphertext, key, iv)
        return True, plaintext
    except ValueError as e:
        return False, None


def handle_padding_exceptions():
    """
    Padding 異常常見原因與處理方式
    """
    key = os.urandom(16)
    iv = os.urandom(16)

    encrypted = aes128_cbc_encrypt(b"Hello, World!", key, iv)
    success, plain = aes128_cbc_decrypt_safe(encrypted, key, iv)
    print(f"正常解密: {success}, 結果: {plain}")

    wrong_key = os.urandom(16)
    success, plain = aes128_cbc_decrypt_safe(encrypted, wrong_key, iv)
    print(f"錯誤金鑰: {success}, 結果: {plain}")

    tampered = encrypted[:-1] + bytes([encrypted[-1] ^ 0x01])
    try:
        aes128_cbc_decrypt(tampered, key, iv)
    except ValueError as e:
        print(f"Padding 異常 (密文被篡改): {type(e).__name__}: {e}")


if __name__ == "__main__":
    key = b"0" * 16
    iv = b"0" * 16
    plaintext = b"Secret message"
    encrypted = aes128_cbc_encrypt(plaintext, key, iv)
    decrypted = aes128_cbc_decrypt(encrypted, key, iv)
    print(f"原文: {plaintext}")
    print(f"解密: {decrypted}")
    print(f"驗證: {plaintext == decrypted}")
    print()
    handle_padding_exceptions()
