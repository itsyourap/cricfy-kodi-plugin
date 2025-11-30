import time
import json
import hashlib
from lib.config import ADDON_PATH, cache
from lib.logger import log_error, log_info
from lib.crypto_utils import decrypt_data
from lib.req import fetch_url
from lib.m3u_parser import PlaylistItem, parse_m3u

URL_FILE_PATH = ADDON_PATH / "resources" / "cricfy_url.txt"
FALLBACK_PROVIDERS_FILE_PATH = ADDON_PATH / \
  "resources" / "fallback_providers.json"

URL = open(URL_FILE_PATH, "r").read().strip()
FALLBACK_PROVIDERS = json.loads(open(FALLBACK_PROVIDERS_FILE_PATH, "r").read())

PROVIDERS_CACHE_KEY = "cricfy_providers"
CHANNEL_CACHE_TTL = 3600  # 1 hour


def _hash_key(key: str) -> str:
  """
  Simple hash function for caching keys.
  """
  return hashlib.sha256(key.encode()).hexdigest()


def get_providers():
  """
  Fetches and decrypts the list of providers from Cricfy.
  Uses caching to avoid repeated network calls.
  """
  cached_providers = cache.get(PROVIDERS_CACHE_KEY)
  if cached_providers and isinstance(cached_providers, str):
    return json.loads(cached_providers)

  log_info("providers", "[Cache Miss] Fetching providers from remote URL")

  response = fetch_url(
    URL,
    timeout=15,
  )
  if response:
    try:
      decrypted_data = decrypt_data(response)
      if not decrypted_data:
        return FALLBACK_PROVIDERS

      providers = json.loads(decrypted_data)

      if not isinstance(providers, list):
        return FALLBACK_PROVIDERS

      cache.set(PROVIDERS_CACHE_KEY, decrypted_data)
      log_info("providers", "Providers cached successfully")
      return providers
    except Exception as e:
      log_error("providers", f"Error parsing providers: {e}")
  return FALLBACK_PROVIDERS


def get_channels(provider_url: str):
  """
  Fetches channels for a specific provider.
  """
  channel_cache_key = f"channels_{_hash_key(provider_url)}"
  cached_channels = cache.get(channel_cache_key)
  if cached_channels and isinstance(cached_channels, str):
    channel_data = json.loads(cached_channels)
    fetch_time = float(channel_data.get('fetch_time'))
    channels = json.loads(channel_data.get('channels', "[]"))
    if (time.time() - fetch_time <= CHANNEL_CACHE_TTL) and isinstance(channels, list):
      return [PlaylistItem.from_dict(item) for item in channels]

  log_info(
    "providers", f"[Cache Miss] Fetching M3U URL ({provider_url}) content")

  try:
    content = fetch_url(provider_url, timeout=15)
    channels = parse_m3u(content)
    cache.set(channel_cache_key, json.dumps({
      'channels': json.dumps(channels, default=lambda o: o.to_dict()),
      'fetch_time': time.time()
    }))
    return channels
  except Exception as e:
    log_error(
      "providers", f"Error fetching M3U URL ({provider_url}) content: {e}")
    raise e
