"""Infrastructure shared by every script in this folder.

All the master scripts do the same outside their operation:
    1. read the source save and validate it is a GTA SA Mobile save
   2. modify a buffer
    3. recalculate the checksum and write to a NEW file
    4. re-read from disk and validate again

This is that boilerplate, so each script only contains its operation.
"""

import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))

from gtasa.editor import (
    platform_warnings, calc_checksum, stored_checksum, fix_checksum, find_blocks,
)


def load(path):
    """Returns the bytes of a valid save, or exits with an error."""
    p = Path(path)
    if not p.is_file():
        sys.exit(f"error: file not found: {p}")
    data = p.read_bytes()
    warnings = platform_warnings(data)
    for w in warnings:
        print(f"  warning: {w}", file=sys.stderr)
    if warnings:
        sys.exit(f"error: {p} does not look like a GTA SA Mobile save")
    if calc_checksum(data) != stored_checksum(data):
        sys.exit(f"error: {p} has an invalid checksum; not editing")
    return data


def save(buf, output, original, force=False):
    """Writes `buf` with a fresh checksum and validates the result from disk."""
    dest = Path(output)
    if dest.exists() and not force:
        sys.exit(f"error: {dest} already exists (use FORCE = True or change OUTPUT)")
    assert len(buf) == len(original), "file size must not change"
    fix_checksum(buf)
    dest.write_bytes(buf)

    check = dest.read_bytes()
    assert not platform_warnings(check), platform_warnings(check)
    assert calc_checksum(check) == stored_checksum(check), "checksum written incorrectly"
    find_blocks(check)

    changed = sum(1 for i in range(len(original)) if original[i] != check[i])
    n_blocks = len(find_blocks(check)) - 1   # find_blocks adds the end sentinel
    print(f"\n  {changed} bytes changed")
    print(f"  wrote {dest}: {len(check)} bytes, checksum OK, "
          f"{n_blocks} blocks OK")
    return check
