from lib.config import cache
from lib.logger import log_info
from lib.providers import get_providers

if __name__ == '__main__':
  # Clear all cache entries
  cache.delete('%')
  log_info("service", "All cache cleared")

  # Prefetch providers to warm up cache
  providers = get_providers()
  log_info("service", f"Fetched {len(providers)} providers")
