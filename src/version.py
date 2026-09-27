"""The project version, in one place.

`setup.py` and `src/server.py` both need it, and two copies is one too many —
whichever forgets to be bumped is the one someone reads. A module rather than a
plain `VERSION` text file, so importing it needs no file read and no parsing at
runtime, and so `setup.py` can exec it without importing `src` (which would
need the dependencies installed first).

Bump this and add a `CHANGELOG.md` entry in the same commit.
"""

VERSION = "1.2.0"

#: The spelling packaging tools expect.
__version__ = VERSION
