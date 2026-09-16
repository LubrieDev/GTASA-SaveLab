"""Shared paths for the test suite.

The tests never write to the repository: they read ``savefiles/base.b`` in
memory (as a ``bytearray`` copy) and only create temp files via :mod:`tempfile`.
"""

from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SAVEFILES = REPO / "savefiles"
BASE = SAVEFILES / "base.b"