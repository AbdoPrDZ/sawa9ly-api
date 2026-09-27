"""Minimal Livewire v3 client.

The site is a Laravel app driven by Livewire components. Every interaction
is a POST to /livewire/update carrying the component's `wire:snapshot`, so
the client needs the page HTML (for the CSRF token and the update URI) and
the component element that owns the action.

Each client belongs to a user and keeps that user's sawa9ly session, so
several users can be driven at once without sharing a cart.
"""

import json
import logging
import os
import re
from urllib.parse import urlparse

import dotenv
import requests
from pyquery import PyQuery as pq

from src.utils import BASE_URL, COOKIE_DOMAIN, parse_cookie

dotenv.load_dotenv()

logger = logging.getLogger(__name__)

DEFAULT_UPDATE_PATH = "/livewire/update"
LOGIN_PATH = "/login"

# A page that bounces guests to /login, used to tell a live session from a
# stale one.
AUTH_CHECK_PATH = "/panier"

CSRF_PATTERN = re.compile(r'name="csrf-token"\s+content="([^"]+)"')
FORM_TOKEN_PATTERN = re.compile(r'name="_token"\s+value="([^"]+)"')
UPDATE_URI_PATTERN = re.compile(r'data-update-uri="([^"]+)"')

_db_ready = False


class LivewireError(Exception):
  """Raised when a Livewire interaction cannot be completed."""


def ensure_db():
  """Create the tables once per process, before any entity is used.

  The project is not in production, so a schema change means editing the
  model, deleting `data/sawa9ly.db` and letting `create_all` rebuild it.
  There is deliberately no migration runner.
  """
  global _db_ready

  if _db_ready:
    return

  from src.db import init_db

  init_db()
  _db_ready = True


def session_user(db, username):
  """The named user, created on first use.

  There is no default. A caller must say whose session it wants, and a user
  carries its own sawa9ly credentials, so an API-key user can never silently
  borrow another account's cart. A user created here without credentials simply
  cannot sign in until given some, which `User.credentials` reports clearly.
  """
  from src.models import User

  if not username:
    raise LivewireError("A username is required; there is no default user.")

  return User.get_or_create(db, username, inherit_credentials=False)


class Livewire:
  """Livewire client bound to one user's authenticated session.

  A username is required. There is no default and no shared instance: a client
  *is* an identity, so building one always says whose session it drives. The
  server keeps one per user in `src/server.py` to avoid repeated logins; a
  short-lived CLI run does not need that.
  """

  def __init__(self, username):
    if not username:
      raise LivewireError("Livewire requires a username; there is no default user.")

    self._username = username
    self._session = _build_session(username)

  @property
  def username(self):
    return self._username

  @property
  def session(self):
    return self._session

  def login(self, email=None, password=None, remember=False):
    """Log in as this user, storing the session in the database."""
    if not email or not password:
      email, password = self._credentials()

    return login(self.session, email, password, self._username, remember)

  def _credentials(self):
    from src.db import session_scope

    with session_scope() as db:
      return session_user(db, self._username).credentials()

  def refresh_session(self):
    """Drop this user's cookies and log in again."""
    logger.info("refreshing the session for %s", self._username)
    self.session.cookies.clear()

    return self.login()

  def cookies(self):
    """This session's cookie string."""
    return cookie_string(self.session)

  # --- pages --------------------------------------------------------

  def load_html(self, url):
    response = self.session.get(url)

    # A session that expires mid-run shows up as a bounce to /login. Log in
    # again and retry, so the refresh is invisible to callers.
    if _bounced_to_login(response, url):
      logger.info(
        "page %s bounced to the login form for %s, refreshing the session",
        url, self._username,
      )
      self.refresh_session()
      response = self.session.get(url)

    response.raise_for_status()

    return response.text

  def load_page(self, url):
    return pq(self.load_html(url))

  # --- snapshots ----------------------------------------------------

  def find_component(self, doc, name):
    """Find a component by its Livewire memo name, e.g. 'panier'."""
    for element in doc("[wire\\:id]").items():
      raw = element.attr("wire:snapshot")
      if not raw:
        continue

      try:
        snapshot = json.loads(raw)
      except ValueError:
        continue

      if snapshot["memo"]["name"] == name:
        return element

    return None

  def owning_component(self, element):
    """Nearest ancestor of element that carries a wire:id.

    pyquery's parents() is ordered outermost-first, so eq(0) returns the
    outermost component. Livewire actions belong to the *nearest* one.
    """
    node = element
    while len(node):
      node = node.parent()
      if not len(node):
        break

      if node.attr("wire:id") and node.attr("wire:snapshot"):
        return node

    raise LivewireError("No wire:id ancestor found for element")

  def snapshot_of(self, component):
    """Accept either a component element or a raw snapshot string.

    A response carries the next snapshot, and chaining calls means feeding
    that string straight back in, so both forms are useful.
    """
    if isinstance(component, str):
      return component

    snapshot = component.attr("wire:snapshot")
    if not snapshot:
      raise LivewireError("Component has no wire:snapshot attribute")

    return snapshot

  def component_data(self, response):
    """Pull the updated snapshot data out of a /livewire/update response."""
    return json.loads(response["components"][0]["snapshot"])["data"]

  # --- actions ------------------------------------------------------

  def call(self, html, component, method, params=None, referer=None):
    """Invoke a Livewire action method on a component."""
    return self._dispatch(
      html, component,
      calls=[{"path": "", "method": method, "params": params or []}],
      referer=referer, label=method,
    )

  def update(self, html, component, updates, referer=None):
    """Push wire:model property updates, with no action call.

    This is what a `wire:model.live` binding sends: an `updates` map and an
    empty `calls` list.
    """
    return self._dispatch(html, component, updates=updates,
                          referer=referer, label="update")

  def _dispatch(self, html, component, updates=None, calls=None, referer=None, label=""):
    payload = {
      "_token": self._csrf(html),
      "components": [
        {
          "snapshot": self.snapshot_of(component),
          "updates": updates or {},
          "calls": calls or [],
        }
      ],
    }

    headers = {
      "accept": "application/json",
      "content-type": "application/json",
      "x-livewire": "",
      "origin": BASE_URL,
      "referer": referer or BASE_URL,
    }

    url = f"{BASE_URL}{self._update_uri(html)}"
    logger.info("livewire %s for %s", label or "request", self._username)
    response = self.session.post(url, json=payload, headers=headers, allow_redirects=False)

    if response.status_code == 419:
      # The session died between loading the page and posting, so the token
      # no longer matches. Refresh it and retry once with a token bound to
      # the new session.
      logger.warning(
        "livewire %s for %s: CSRF rejected (419), refreshing the session and retrying",
        label, self._username,
      )
      self.refresh_session()
      payload["_token"] = self._csrf(self.load_html(referer or BASE_URL))
      response = self.session.post(url, json=payload, headers=headers, allow_redirects=False)

    if not response.ok:
      logger.error(
        "livewire %s for %s: failed with HTTP %s",
        label, self._username, response.status_code,
      )
      raise LivewireError(
        f"Livewire request '{label}' failed: "
        f"{response.status_code} {response.text[:200]}"
      )

    return response.json()

  def _csrf(self, html):
    match = CSRF_PATTERN.search(html)
    if not match:
      raise LivewireError("CSRF token not found in page HTML")

    return match.group(1)

  def _update_uri(self, html):
    match = UPDATE_URI_PATTERN.search(html)
    return match.group(1) if match else DEFAULT_UPDATE_PATH


def login(session, email, password, username=None, remember=False):
  """Log in through the site's plain form, storing the session in the database.

  /login is an ordinary Laravel form (POST with _token, email, password),
  not a Livewire component. On success Laravel redirects away from /login
  and rotates the session cookie; on failure it sends the browser back to
  /login with the errors flashed.

  Raises:
      LivewireError: If the login page or CSRF token cannot be read, or the
          credentials are rejected.
  """
  html = session.get(f"{BASE_URL}{LOGIN_PATH}", headers={"accept": "text/html"}).text

  data = {
    "_token": _form_token(html),
    "email": email,
    "password": password,
  }
  if remember:
    data["remember"] = "on"

  response = session.post(
    f"{BASE_URL}{LOGIN_PATH}",
    data=data,
    headers={
      "accept": "text/html",
      "referer": f"{BASE_URL}{LOGIN_PATH}",
      "origin": BASE_URL,
    },
    allow_redirects=True,
  )

  if response.status_code == 419:
    logger.warning("login for %s: CSRF rejected (419)", username)
    raise LivewireError("Login failed: the CSRF token was rejected (419).")

  if urlparse(response.url).path.rstrip('/') == LOGIN_PATH:
    logger.warning("login for %s: the site refused the sign-in", username)
    raise LivewireError(
      "Login failed: the site rejected the credentials. Each user stores its "
      "own, so check the user with: python main.py user list"
    )

  cookies = cookie_string(session)
  save_session(username, cookies)

  logger.info("login for %s: accepted", username)

  return cookies


def load_session(username=None):
  """The stored cookie string for a user, or None."""
  from src.db import session_scope
  from src.models import SESSION_KEY

  ensure_db()
  with session_scope() as db:
    return session_user(db, username).setting(db, SESSION_KEY)


def save_session(username, cookies):
  """Persist a cookie string for a user."""
  from src.db import session_scope
  from src.models import SESSION_KEY

  ensure_db()
  with session_scope() as db:
    session_user(db, username).set_setting(db, SESSION_KEY, cookies)


def cookie_string(session):
  """Serialise a session's cookies."""
  return "; ".join(f"{cookie.name}={cookie.value}" for cookie in session.cookies)


def _form_token(html):
  for pattern in (FORM_TOKEN_PATTERN, CSRF_PATTERN):
    match = pattern.search(html)
    if match:
      return match.group(1)

  raise LivewireError("CSRF token not found in the login page")


def _scope_cookies(session, cookie_string):
  """Bind a stored cookie string to the apex domain.

  The site sets its own cookies for the apex, so domain-less ones would sit
  alongside them in the jar and Laravel could read the stale copy.
  """
  for name, value in parse_cookie(cookie_string).items():
    session.cookies.set(name, value, domain=COOKIE_DOMAIN, path="/")


def _is_authenticated(session):
  """Whether the session still reaches an authenticated page."""
  response = session.get(f"{BASE_URL}{AUTH_CHECK_PATH}", allow_redirects=True)

  return urlparse(response.url).path.rstrip('/') != LOGIN_PATH


def _bounced_to_login(response, url):
  """True when the site sent us to /login for a page that is not /login."""
  if urlparse(url).path.rstrip('/') == LOGIN_PATH:
    return False

  return urlparse(response.url).path.rstrip('/') == LOGIN_PATH


def _build_session(username=None):
  """Reuse a user's stored session, falling back to a fresh login.

  A stored session that no longer authenticates is discarded and replaced, so
  an expired one never blocks startup. Which of the two happened is logged,
  because a re-login is invisible to the caller and an expired session is the
  usual reason a command that worked yesterday does not work today.
  """
  ensure_db()

  from src.db import session_scope
  from src.models import SESSION_KEY

  with session_scope() as db:
    user = session_user(db, username)
    cookies = user.setting(db, SESSION_KEY)
    email, password = user.credentials()

  session = requests.Session()

  if cookies:
    _scope_cookies(session, cookies)

    if _is_authenticated(session):
      logger.info("session for %s: reused the stored one", username)
      return session

    logger.info(
      "session for %s: the stored one no longer authenticates, signing in again",
      username,
    )
  else:
    logger.info("session for %s: nothing stored, signing in", username)

  login(session, email, password, username)

  return session

