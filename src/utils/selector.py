"""Base class for pages described by a selector guide."""

from pyquery import PyQuery as pq


class Selector:
  """A page, its selector guide and its Livewire client.

  Subclasses define `guide` (a nested dict of selectors addressed with
  dotted paths) and `url`. The document is loaded lazily and cached;
  call `refresh()` before reading again after a mutation.

  A `client` is required. It carries an identity, and a page reached without
  one would have to guess whose session it is reading — which is how a command
  ends up operating on the wrong account's cart.
  """

  guide: dict = {}
  url: str = ""

  def __init__(self, client):
    if not isinstance(getattr(self, 'guide', None), dict):
      raise NotImplementedError("Subclasses must define a 'guide' dictionary.")

    if not isinstance(getattr(self, 'url', None), str) or not self.url:
      raise NotImplementedError("Subclasses must define a 'url' string.")

    if client is None:
      raise NotImplementedError("A page needs a Livewire client for a named user.")

    self._client = client

  @property
  def client(self):
    return self._client

  @property
  def html(self):
    if not hasattr(self, '_html'):
      self.refresh()

    return self._html

  @property
  def doc(self):
    if not hasattr(self, '_doc'):
      self._doc = pq(self.html)

    return self._doc

  def refresh(self):
    """Reload the page, discarding the cached document."""
    self._html = self.client.load_html(self.url)
    self._doc = pq(self._html)

    return self

  def get_selector(self, path):
    current = self.guide

    for key in path.split('.'):
      if key not in current:
        raise KeyError(f"Selector path '{path}' not found in guide.")

      current = current[key]

    return current

  def select(self, path):
    return self.doc(self.get_selector(path))
