import base64
from dataclasses import dataclass
from typing import Optional
from lib.logger import log_error
from lib.config import ADDON_PATH
from Cryptodome.Cipher import AES

SECRET1_FILE_PATH = ADDON_PATH / "resources" / "secret1.txt"
SECRET2_FILE_PATH = ADDON_PATH / "resources" / "secret2.txt"
SECRET1 = open(SECRET1_FILE_PATH, "r").read().strip()
SECRET2 = open(SECRET2_FILE_PATH, "r").read().strip()


@dataclass
class KeyInfo:
  key: bytes
  iv: bytes


def hex_string_to_bytes(hex_str: str) -> bytes:
  return bytes.fromhex(hex_str)


def parse_key_info(secret: str) -> KeyInfo:
  key_hex, iv_hex = secret.split(":")
  return KeyInfo(
    key=hex_string_to_bytes(key_hex),
    iv=hex_string_to_bytes(iv_hex),
  )


def keys():
  return {
    "key1": parse_key_info(SECRET1),
    "key2": parse_key_info(SECRET2),
  }


def decrypt_data(encrypted_base64: str) -> Optional[str]:
  try:
    clean_base64 = (
      encrypted_base64.strip()
      .replace("\n", "")
      .replace("\r", "")
      .replace(" ", "")
      .replace("\t", "")
    )

    ciphertext = base64.b64decode(clean_base64)

    for key_info in keys().values():
      result = try_decrypt(ciphertext, key_info)
      if result is not None:
        return result

    log_error("crypto_utils", "Decryption failed with all keys.")
    return None
  except Exception as e:
    log_error("crypto_utils", f"Decryption failed: {e}")
    return None


def try_decrypt(ciphertext: bytes, key_info: KeyInfo) -> Optional[str]:
  try:
    cipher = AES.new(key_info.key, AES.MODE_CBC, key_info.iv)
    decrypted = cipher.decrypt(ciphertext)

    # PKCS5/7 unpadding
    pad_len = decrypted[-1]
    decrypted = decrypted[:-pad_len]

    text = decrypted.decode("utf-8")

    if (
      text.startswith("{")
      or text.startswith("[")
      or "http" in text.lower()
    ):
      return text
    return None
  except Exception:
    return None
