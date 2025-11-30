import ast
import re
import sys
from urllib.parse import urlencode, parse_qsl
import xbmcgui
import xbmcplugin
from lib.providers import get_providers, get_channels
from lib.req import license_headers
from lib.logger import log_error

# Base URL for the addon
BASE_URL = sys.argv[0]
ADDON_HANDLE = int(sys.argv[1])


def build_url(query):
  return f'{BASE_URL}?{urlencode(query)}'


def list_providers():
  """
  Lists the providers from Cricfy
  """
  provider_list = get_providers()

  for prov in provider_list:
    title = prov.get('title', 'Unknown')
    image = prov.get(
      'image', 'https://www.iconexperience.com/_img/v_collection_png/256x256/shadow/unknown.png')
    cat_link = prov.get('catLink', '')

    if not cat_link or not cat_link.startswith('http'):
      continue

    # Create a folder item for this provider
    li = xbmcgui.ListItem(label=title)
    li.setArt({'icon': image, 'thumb': image})

    url = build_url({'mode': 'list_channels', 'url': cat_link, 'title': title})
    xbmcplugin.addDirectoryItem(
      handle=ADDON_HANDLE, url=url, listitem=li, isFolder=True)

  xbmcplugin.endOfDirectory(ADDON_HANDLE)


def list_channels(provider_url):
  """
  Fetches the M3U from the specific provider and lists channels.
  """
  if not provider_url or not provider_url.startswith('http'):
    xbmcgui.Dialog().notification(
        'Error', 'Invalid provider URL', xbmcgui.NOTIFICATION_ERROR)
    xbmcplugin.endOfDirectory(ADDON_HANDLE)
    return

  # Fetch M3U content
  try:
    channels = get_channels(provider_url=provider_url)
    if not channels:
      xbmcgui.Dialog().notification(
          'Error', 'No channels found', xbmcgui.NOTIFICATION_ERROR)
      xbmcplugin.endOfDirectory(ADDON_HANDLE)
      return
  except Exception as e:
    log_error("main", f"Error fetching channels: {e}")
    xbmcgui.Dialog().notification(
        'Error', 'Failed to fetch playlist content', xbmcgui.NOTIFICATION_ERROR)
    xbmcplugin.endOfDirectory(ADDON_HANDLE)
    return

  for ch in channels:
    li = xbmcgui.ListItem(label=ch.title)
    li.setArt({'thumb': ch.tvg_logo, 'icon': ch.tvg_logo})
    li.setInfo('video', {'title': ch.title, 'genre': ch.group_title})
    li.setProperty('IsPlayable', 'true')

    # Construct URL for playback mode
    # We encode the channel data into the URL so we don't have to re-parse on playback
    # TODO: Use a cache to eliminate stale URLs (if item was added to favorites, etc)
    params = {
      'mode': 'play',
      'url': ch.url,
      'ua': ch.user_agent,
      'cookie': ch.cookie,
      'referer': ch.referer,
      'lic': ch.license_string,
      'headers': ch.headers
    }

    url = build_url(params)
    xbmcplugin.addDirectoryItem(
      handle=ADDON_HANDLE, url=url, listitem=li, isFolder=False)
  xbmcplugin.endOfDirectory(ADDON_HANDLE)


def play_video(url, user_agent, cookie, referer, license_string, headers):
  """
  Resolves the URL and sets up Inputstream Adaptive for DRM or HLS.
  """
  li = xbmcgui.ListItem(path=url)

  # Construct standard headers string for Kodi
  stream_headers = []
  if headers:
    parsed_headers = ast.literal_eval(headers)
    for k, v in parsed_headers.items():
      stream_headers.append(f'{k}={v}')

  if user_agent:
    stream_headers.append(f'User-Agent={user_agent}')
  if referer:
    stream_headers.append(f'Referer={referer}')
  if cookie:
    stream_headers.append(f'Cookie={cookie}')

  # Check if DASH (mpd) or HLS (m3u/m3u8) or DRM license is present
  if '.mpd' in url or '.m3u8' in url or '.m3u' in url or license_string:
    li.setProperty('inputstream', 'inputstream.adaptive')

    if (stream_headers):
      encoded_headers = '&'.join(stream_headers)
      li.setProperty('inputstream.adaptive.manifest_headers', encoded_headers)
      li.setProperty('inputstream.adaptive.stream_headers', encoded_headers)
      url += '|' + encoded_headers
      li.setPath(url)

    if license_string:
      # Check if Clearkey license exists
      # Match format hex:hex (one or more hex digits each side)
      hex_pair_re = re.compile(r'^[0-9a-fA-F]+:[0-9a-fA-F]+$')

      if license_string and hex_pair_re.match(license_string):
        drm_config = f"org.w3.clearkey|{license_string}"
        li.setProperty('inputstream.adaptive.drm_legacy', drm_config)

      # If it's a URL (Clearkey License Server)
      elif license_string and license_string.startswith('http'):
        drm_config = f"org.w3.clearkey|{license_string}|{urlencode(license_headers)}"
        li.setProperty('inputstream.adaptive.drm_legacy', drm_config)
  xbmcplugin.setResolvedUrl(ADDON_HANDLE, True, li)


def router(param_string):
  params = dict(parse_qsl(param_string))
  mode = params.get('mode')

  if mode is None:
    list_providers()
  elif mode == 'list_channels':
    list_channels(params.get('url'))
  elif mode == 'play':
    play_video(
      params.get('url'),
      params.get('ua'),
      params.get('cookie'),
      params.get('referer'),
      params.get('lic'),
      params.get('headers')
    )
  else:
    xbmcgui.Dialog().notification(
      'Error', 'Not implemented', xbmcgui.NOTIFICATION_ERROR)


if __name__ == '__main__':
  router(sys.argv[2][1:])
