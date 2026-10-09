"""A store's logo, kept as a base64 data URI.

The dashboard uploads a small image and the browser hands it over as a
`data:image/png;base64,...` string. That string is stored verbatim on the user and
emitted back into the storefront's markup, which is why it has to be checked here
rather than trusted: an uncapped upload would put an unbounded blob in a row that
is read on every store page, and a `data:` type that is not an image is a vector
into the page.

There is no file storage in this project, so the alternative to a data URI would
be a media directory and a serving route. This keeps the whole thing in the row.

The check is a prefix and a size, not a real image decode: this is a bound on what
the server will keep, not proof the bytes are a picture. The storefront escapes
everything it renders, so a mislabelled payload is a broken image, not script.
"""

import base64
import re

#: The image types a store logo may be. SVG is deliberately absent: it can carry
#: script, and an `<img>` is not a place to find out whether a browser runs it.
ALLOWED_TYPES = ("image/png", "image/jpeg", "image/webp", "image/gif")

#: The most a decoded logo may be. Small enough that a directory of them stays a
#: page, large enough for a real logo.
MAX_BYTES = 256 * 1024

#: `data:<type>;base64,<payload>`, with the payload kept so it can be decoded and
#: measured. The type is checked against `ALLOWED_TYPES` after the match.
DATA_URI = re.compile(r"^data:([\w.+-]+/[\w.+-]+);base64,(.+)$", re.DOTALL)


class StoreLogoError(ValueError):
  """A logo is not something that can be stored."""


class StoreLogo:
  """Validating and normalising a store logo data URI."""

  @classmethod
  def clean(cls, value):
    """The storable form of a logo, or None for "no logo".

    An empty string clears it. Anything else must be an allowed image data URI
    within the size cap, or `StoreLogoError` is raised so the API can answer 400
    rather than keep something it cannot render.
    """
    if value is None:
      return None

    if isinstance(value, str) and not value.strip():
      return None

    match = DATA_URI.match(str(value).strip())

    if not match:
      raise StoreLogoError(
        "The logo must be an uploaded image (a base64 data URI), not a URL."
      )

    media_type = match.group(1).lower()

    if media_type not in ALLOWED_TYPES:
      raise StoreLogoError(
        f"Unsupported logo type '{media_type}'. Use one of: "
        f"{', '.join(ALLOWED_TYPES)}."
      )

    try:
      raw = base64.b64decode(match.group(2), validate=True)
    except ValueError as error:
      raise StoreLogoError("The logo is not valid base64 data.") from error

    if len(raw) > MAX_BYTES:
      raise StoreLogoError(
        f"The logo is {len(raw) // 1024} KB; the limit is {MAX_BYTES // 1024} KB."
      )

    return value.strip()
