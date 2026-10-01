"""Shared helpers and constants used across the client."""

from urllib.parse import urlparse

BASE_URL = "https://sawa9ly.app"

# The site also answers on sawa9ly.com, but .app is the primary: its storage
# and CDN URLs are hardcoded to it. Auth cookies are scoped to this host so
# the server's own cookies are not duplicated in the jar.
COOKIE_DOMAIN = urlparse(BASE_URL).hostname


def parse_cookie(cookie_string):
  """
  Parses a cookie string into a dictionary.

  Args:
      cookie_string (str): The cookie string to parse.

  Returns:
      dict: A dictionary containing cookie names and values.
  """
  cookies = {}

  for cookie in cookie_string.split(';'):
    if '=' in cookie:
      name, value = cookie.strip().split('=', 1)
      cookies[name] = value

  return cookies


# Imported after the definitions above on purpose: livewire and selector read
# BASE_URL / parse_cookie from this package, so importing them at the top of the
# file would be a circular import.
from .livewire import Livewire, LivewireError, PageNotFound  # noqa: E402
from .selector import Selector  # noqa: E402
from .telegram import Telegram, TelegramError  # noqa: E402


__all__ = [
  "BASE_URL",
  "COOKIE_DOMAIN",
  "Livewire",
  "LivewireError",
  "PageNotFound",
  "Selector",
  "Telegram",
  "TelegramError",
  "parse_cookie",
]
