from pathlib import Path
from xbmcaddon import Addon
from xbmcvfs import translatePath
try:
  import StorageServer  # pyright: ignore[reportMissingImports]
except:
  import lib.storageserverdummy as StorageServer

ADDON_PATH = Path(translatePath(Addon().getAddonInfo('path')))
cache = StorageServer.StorageServer("cricfy_plugin", 24)
