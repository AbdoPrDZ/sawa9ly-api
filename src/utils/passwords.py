"""Password hashing for dashboard accounts.

Only this module knows how a stored password is encoded. Keeping it separate
from token handling means a change to either does not drag the other along, and
it is the only place that touches scrypt parameters.

scrypt comes from the standard library, so the project gains no dependency for
hashing. `hashlib.pbkdf2_hmac` would also work but is far cheaper to attack
offline, which is the threat a leaked database row represents.
"""

import base64
import hashlib
import hmac
import secrets

# N=2**14 costs roughly 50-100ms per verification, which is the point: it makes
# an offline guessing attack against a leaked hash expensive. Raising N costs
# every login, so it is deliberately not turned up further.
N = 2 ** 14
R = 8
P = 1
DKLEN = 32
SALT_BYTES = 16

SCHEME = "scrypt"


class Passwords:
  """Hashes and verifies dashboard passwords."""

  @staticmethod
  def hash(plaintext):
    """Return an encoded `scrypt$n=..,r=..,p=..$salt$hash` string to store."""
    if not plaintext:
      raise ValueError("A password is required")

    salt = secrets.token_bytes(SALT_BYTES)
    digest = hashlib.scrypt(
      plaintext.encode("utf-8"),
      salt=salt,
      n=N,
      r=R,
      p=P,
      dklen=DKLEN,
    )

    return "$".join([
      SCHEME,
      f"n={N},r={R},p={P}",
      base64.b64encode(salt).decode("ascii"),
      base64.b64encode(digest).decode("ascii"),
    ])

  @staticmethod
  def verify(plaintext, encoded):
    """Whether the plaintext matches the stored hash. Never raises.

    A malformed or truncated hash returns False rather than raising, so a
    corrupted row denies access instead of producing a 500.
    """
    if not plaintext or not encoded:
      return False

    try:
      scheme, params, salt_b64, digest_b64 = encoded.split("$")

      if scheme != SCHEME:
        return False

      settings = dict(
        part.split("=", 1) for part in params.split(",") if "=" in part
      )
      salt = base64.b64decode(salt_b64)
      expected = base64.b64decode(digest_b64)
      candidate = hashlib.scrypt(
        plaintext.encode("utf-8"),
        salt=salt,
        n=int(settings["n"]),
        r=int(settings["r"]),
        p=int(settings["p"]),
        dklen=len(expected),
      )
    except (ValueError, KeyError, TypeError):
      return False

    # Constant time, so a wrong password cannot be discovered byte by byte.
    return hmac.compare_digest(candidate, expected)
