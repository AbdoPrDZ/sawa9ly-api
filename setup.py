"""Packaging for the sawa9ly client.

Run from a checkout with `python main.py <command>`. Installing is optional and
gives you a `sawa9ly` console script; see the note in the README about where an
installed copy looks for `data/` and `dashboard/dist`.

The version is read with a regex rather than by importing `src`, because
importing the package would need the dependencies installed already — which is
precisely the state `setup.py` has to work in.
"""

import re
from pathlib import Path

from setuptools import find_packages, setup

ROOT = Path(__file__).resolve().parent

VERSION_FILE = ROOT / "src" / "version.py"
REQUIREMENTS_FILE = ROOT / "requirements.txt"
README_FILE = ROOT / "README.md"


class Package:
  """The metadata `setup()` needs, read from the files that already hold it.

  Namespaced rather than free functions, because these belong to no one entity.
  Nothing here may import `src` or `cli`: those need the runtime dependencies,
  and a build that cannot run before `pip install` is not a build.
  """

  @staticmethod
  def version():
    """The `VERSION = "..."` assignment in `src/version.py`."""
    match = re.search(
      r'^VERSION\s*=\s*["\'](.+?)["\']',
      VERSION_FILE.read_text(encoding="utf-8"),
      re.MULTILINE,
    )

    if not match:
      raise RuntimeError(f"No VERSION assignment found in {VERSION_FILE}")

    return match.group(1)

  @staticmethod
  def requirements():
    """Runtime dependencies, from the one file that already lists them."""
    lines = REQUIREMENTS_FILE.read_text(encoding="utf-8").splitlines()

    return [
      line.strip() for line in lines
      if line.strip() and not line.strip().startswith("#")
    ]

  @staticmethod
  def readme():
    return README_FILE.read_text(encoding="utf-8")


setup(
  name="sawa9ly-api",
  version=Package.version(),
  description="Python client and HTTP API for the sawa9ly.app dropshipping site",
  long_description=Package.readme(),
  long_description_content_type="text/markdown",
  license="MIT",
  license_files=["LICENSE"],
  # PEP 604 `X | None` annotations are evaluated at runtime by pydantic and
  # FastAPI, so 3.10 is the real floor. Tested on 3.14.
  python_requires=">=3.10",
  packages=find_packages(include=["src", "src.*", "cli", "cli.*", "sawa9ly"]),
  # `src/seeds` holds data, not code, so `find_packages` does not see it — it has
  # no `__init__.py` and never should. Without this the delivery seed is absent
  # from a wheel, and the install step the README gives cannot be run.
  package_data={"src": ["seeds/*.sql"]},
  include_package_data=True,
  install_requires=Package.requirements(),
  entry_points={
    "console_scripts": [
      # `cli.app:App.main` rather than a shim in `sawa9ly`: the parser already
      # lives there, so the script needs no wrapper of its own.
      "sawa9ly = cli.app:App.main",
    ],
  },
  classifiers=[
    "Development Status :: 4 - Beta",
    "Environment :: Console",
    "Framework :: FastAPI",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Topic :: Office/Business",
  ],
)
