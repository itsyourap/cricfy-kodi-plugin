import re
import json


class PlaylistItem:
  def __init__(self):
    self.title = ""
    self.url = ""
    self.tvg_logo = ""
    self.group_title = ""
    self.user_agent = ""
    self.cookie = ""
    self.referer = ""
    self.license_string = ""
    self.headers = {}
    self.is_drm = False

  def to_json(self) -> str:
    """Returns the JSON string representation of this object"""
    return json.dumps(self.__dict__)

  def to_dict(self) -> dict:
    """Returns the dictionary representation of this object"""
    return self.__dict__

  @staticmethod
  def from_dict(data):
    """Helper to create an object back from a dictionary"""
    item = PlaylistItem()
    # Update item with data, ignoring keys that don't exist in the class
    item.__dict__.update(data)
    return item


def parse_m3u(content: str):
  lines = content.splitlines()
  items: list[PlaylistItem] = []
  current_item = None

  # Buffers for properties appearing before the URL line
  buf_user_agent = None
  buf_cookie = None
  buf_referer = None
  buf_license_string = None
  buf_attrs = None
  buf_title = None

  for line in lines:
    line = line.strip()
    if not line:
      continue

    if line.startswith("#EXTINF"):
      # Extract Attributes (tvg-logo, group-title)
      # Regex for key="value" or key=value
      matches = re.findall(r'([a-zA-Z0-9_-]+)=("[^"]*"|[^,]+)', line)
      attrs = {m[0]: m[1].strip('"') for m in matches}

      buf_attrs = attrs

      # Extract Title (everything after the last comma)
      title_split = line.rsplit(',', 1)
      if len(title_split) > 1:
        buf_title = title_split[1].strip()
      else:
        buf_title = "Unknown Channel"

    elif line.startswith("#EXTVLCOPT"):
      # Handle VLC Options
      if "http-user-agent=" in line:
        buf_user_agent = line.split("http-user-agent=")[1]
      if "http-referrer=" in line:
        buf_referer = line.split("http-referrer=")[1]

    elif line.startswith("#EXTHTTP"):
      # Custom HTTP headers format often found in these M3Us
      try:
        json_str = line.replace("#EXTHTTP:", "")
        data = json.loads(json_str)
        if "cookie" in data:
          buf_cookie = data["cookie"]
        if "user-agent" in data:
          buf_user_agent = data["user-agent"]
      except:
        pass

    elif line.startswith("#KODIPROP:inputstream.adaptive.license_key="):
      # License String for DRM
      buf_license_string = line.split("=", 1)[1]

    elif not line.startswith("#"):
      # Must be URL Line
      current_item = PlaylistItem()

      # Apply buffered items
      if buf_user_agent:
        current_item.user_agent = buf_user_agent
      if buf_cookie:
        current_item.cookie = buf_cookie
      if buf_referer:
        current_item.referer = buf_referer
      if buf_license_string:
        current_item.license_string = buf_license_string
        current_item.is_drm = True
      if buf_attrs:
        if "tvg-logo" in buf_attrs:
          current_item.tvg_logo = buf_attrs["tvg-logo"]
        if "group-title" in buf_attrs:
          current_item.group_title = buf_attrs["group-title"]
      if buf_title:
        current_item.title = buf_title

      # Reset buffers
      buf_user_agent = None
      buf_cookie = None
      buf_referer = None
      buf_license_string = None
      buf_attrs = None
      buf_title = None

      full_url_line = line

      # Handle pipe separated parameters (url|User-Agent=...&Referer=...)
      if "|" in full_url_line:
        url_parts = full_url_line.split("|")
        current_item.url = url_parts[0]
        params = url_parts[1].split("&")
        for p in params:
          if "=" in p:
            k, v = p.split("=", 1)
            if k.lower() == "user-agent":
              current_item.user_agent = v
            elif k.lower() == "referer":
              current_item.referer = v
            elif k.lower() == "cookie":
              current_item.cookie = v
            else:
              current_item.headers[k] = v
      else:
        current_item.url = full_url_line

      items.append(current_item)
      current_item = None  # Reset for next item

  return items
