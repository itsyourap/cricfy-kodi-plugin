import base64
from lib.logger import log_error
from lib.config import ADDON_PATH

try:
  from Crypto.Cipher import AES
except ImportError:
  # Kodi environment does not have Crypto.Cipher module
  # Instead it imports automatically from its pycryptodome package
  pass

SECRET_FILE_PATH = ADDON_PATH / "resources" / "secret.txt"
SECRET = open(SECRET_FILE_PATH, "r").read().strip()


def decrypt_data(encrypted_base64: str) -> str:
  try:
    clean_base64 = (
      encrypted_base64.strip()
      .replace("\n", "")
      .replace("\r", "")
      .replace(" ", "")
      .replace("\t", "")
    )

    # 1. Extract IV — reverse first 16 chars
    iv_raw = SECRET[:16][::-1]
    iv = iv_raw.encode("utf-8")

    # 2. Extract AES key — reverse substring from 11 to len - 1
    key_raw = SECRET[11:-1][::-1]
    key = key_raw.encode("iso-8859-1")

    # 3. Decode base64
    decoded = base64.b64decode(clean_base64)

    # 4. AES decrypt (CBC mode, PKCS5 padding)
    cipher = AES.new(key, AES.MODE_CBC, iv) # pyright: ignore[reportPossiblyUnboundVariable]
    decrypted = cipher.decrypt(decoded)

    # 5. Handle padding
    pad_len = decrypted[-1]
    if pad_len <= 0 or pad_len > 16:
      # invalid padding
      return decrypted.decode("utf-8", errors="ignore").rstrip("\x00")
    plaintext = decrypted[:-pad_len]
    return plaintext.decode("utf-8", errors="ignore")

  except Exception as e:
    log_error("crypto_utils", f"Decryption failed: {e}")
    return ""
