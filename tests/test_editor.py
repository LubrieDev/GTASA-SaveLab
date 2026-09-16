"""Tests for the editor layer and the `gta.py` command line.

The editor layer takes offsets relative to a BLOCK START (they include the 5-byte
tag), matching how `gtasa.editor.report`/`gtasa.cli` read the file. The CLI is
exercised end to end in separate subprocesses against temp copies -- never the
repository files.
"""

import contextlib
import io
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from gtasa import editor, savefile
from tests._paths import BASE, REPO

ORIGINAL = BASE.read_bytes()


def cli(*args, cwd=REPO):
    return subprocess.run([sys.executable, *args], cwd=cwd,
                          capture_output=True, text=True, encoding="utf-8")


class TestFindBlocks(unittest.TestCase):
    def test_returns_29_starts_plus_sentinel(self):
        offs = editor.find_blocks(ORIGINAL)
        self.assertEqual(len(offs), savefile.N_BLOQUES + 1)

    def test_sentinel_is_the_briefs_start(self):
        offs = editor.find_blocks(ORIGINAL)
        self.assertEqual(offs[-1], 184400)

    def test_size_of_block_zero_is_simplevars(self):
        offs = editor.find_blocks(ORIGINAL)
        self.assertEqual(offs[1] - offs[0], editor.MOBILE_SIMPLEVARS)

    def test_find_blocks_validates_corruption(self):
        roto = bytearray(ORIGINAL)
        del roto[editor.find_blocks(ORIGINAL)[6]]   # knock a fixed block's tag
        with self.assertRaises(ValueError):
            editor.find_blocks(roto)

    def test_cached_lookup_is_consistent(self):
        offs1 = editor.find_blocks(ORIGINAL)
        offs2 = editor.find_blocks(ORIGINAL)
        self.assertEqual(offs1, offs2)


class TestPlayerBlock(unittest.TestCase):
    """Money and DisplayMoney are int32 at block 15 + 9 / + 21 (abs offsets)."""

    @classmethod
    def setUpClass(cls):
        cls.offs = editor.find_blocks(ORIGINAL)
        cls.pi = cls.offs[editor.PLAYERINFO_BLOCK]

    def test_money_matches_reference_value(self):
        self.assertEqual(struct.unpack_from("<i", ORIGINAL, self.pi + editor.OFF_MONEY)[0],
                         999_999_999)

    def test_display_money_must_match_money(self):
        m = struct.unpack_from("<i", ORIGINAL, self.pi + editor.OFF_MONEY)[0]
        d = struct.unpack_from("<i", ORIGINAL, self.pi + editor.OFF_DISPLAY_MONEY)[0]
        self.assertEqual(d, m, "the HUD copy is what the game shows; they must agree")

    def test_stats_slot_layout(self):
        st = self.offs[editor.STATS_BLOCK] + 5
        for idx in range(82):
            off = st + idx * 4
            self.assertLess(off + 4, self.offs[editor.STATS_BLOCK + 1])


class TestPlatformDiscriminator(unittest.TestCase):
    def test_reference_is_mobile(self):
        self.assertEqual(editor.platform_warnings(ORIGINAL), [])

    def test_pc_globals_counter_is_rejected(self):
        pila = bytearray(ORIGINAL)
        offs = editor.find_blocks(ORIGINAL)
        struct.pack_into("<I", pila, offs[editor.BLOQUE_SCRIPTS] + 5, 43808)
        self.assertTrue(editor.platform_warnings(pila),
                        "43808 globals is the PC build; Mobile saves carry 49212")

    def test_ansi_name_is_rejected(self):
        pila = bytearray(ORIGINAL)
        pila[9:9 + 20] = b"A user supplied name. "
        self.assertTrue(editor.platform_warnings(pila),
                        "PC stores the player name in ANSI, Mobile in UTF-16")

    def test_truncated_save_is_rejected(self):
        self.assertTrue(editor.platform_warnings(ORIGINAL[:2000]))


class TestChecksumHelpers(unittest.TestCase):
    def test_helpers_agree_with_savefile(self):
        sf = savefile.Save(bytearray(ORIGINAL))
        self.assertEqual(editor.calc_checksum(ORIGINAL), sf.checksum_calculado())
        self.assertEqual(editor.stored_checksum(ORIGINAL), sf.checksum_guardado())

    def test_fix_checksum_restores_validity(self):
        buf = bytearray(ORIGINAL)
        struct.pack_into("<i", buf, editor.find_blocks(ORIGINAL)[15] + editor.OFF_MONEY, 1)
        self.assertFalse(savefile.Save(buf).checksum_ok())
        editor.fix_checksum(buf)
        self.assertTrue(savefile.Save(buf).checksum_ok())

    def test_report_reads_a_copy_without_writing(self):
        with tempfile.TemporaryDirectory() as td:
            copia = Path(td) / "copia.b"
            shutil.copy2(BASE, copia)
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                editor.report(copia)
            self.assertIn("999,999,999", out.getvalue())
            self.assertIn("checksum", out.getvalue())


class TestCliEndToEnd(unittest.TestCase):
    """The real `python gta.py ...` command, against temp copies."""

    def test_audit_succeeds_on_reference(self):
        r = cli("gta.py", "audit", str(BASE))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("checksum OK", r.stdout)

    def test_edit_writes_valid_save(self):
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "src.b"
            out = Path(td) / "out.b"
            shutil.copy2(BASE, src)
            r = cli("gta.py", "edit", str(src), "--output", str(out), "--money", "5000")
            self.assertEqual(r.returncode, 0, r.stderr)
            data = out.read_bytes()
            self.assertEqual(len(data), len(ORIGINAL))
            self.assertEqual(savefile.Save(bytearray(data)).problemas(), [])
            self.assertEqual(editor.platform_warnings(data), [])
            offs = editor.find_blocks(data)
            pi = offs[editor.PLAYERINFO_BLOCK]
            self.assertEqual(struct.unpack_from("<i", data, pi + editor.OFF_MONEY)[0], 5000)
            self.assertEqual(struct.unpack_from("<i", data, pi + editor.OFF_DISPLAY_MONEY)[0], 5000)

    def test_edit_changes_only_money_and_checksum_bytes(self):
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "src.b"
            out = Path(td) / "out.b"
            shutil.copy2(BASE, src)
            cli("gta.py", "edit", str(src), "--output", str(out), "--money", "5000")
            nuevo = out.read_bytes()
            offs = editor.find_blocks(ORIGINAL)
            pi = offs[editor.PLAYERINFO_BLOCK]
            esperado = set(range(pi + editor.OFF_MONEY, pi + editor.OFF_MONEY + 4))
            esperado |= set(range(pi + editor.OFF_DISPLAY_MONEY,
                                  pi + editor.OFF_DISPLAY_MONEY + 4))
            esperado |= set(range(len(ORIGINAL) - 4, len(ORIGINAL)))
            cambiados = {i for i in range(len(ORIGINAL)) if ORIGINAL[i] != nuevo[i]}
            self.assertLessEqual(cambiados, esperado,
                                 "only money, display money and the checksum may change")

    def test_edit_refuses_invalid_checksum_source(self):
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "src.b"
            out = Path(td) / "out.b"
            malo = bytearray(ORIGINAL)
            malo[-4:] = b"\x00\x00\x00\x00"
            src.write_bytes(malo)
            r = cli("gta.py", "edit", str(src), "--output", str(out), "--money", "5000")
            self.assertNotEqual(r.returncode, 0)
            self.assertFalse(out.exists(), "nothing may be written from a bad source")

    def test_edit_requires_output(self):
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "src.b"
            shutil.copy2(BASE, src)
            r = cli("gta.py", "edit", str(src), "--money", "5000")
            self.assertNotEqual(r.returncode, 0)

    def test_audit_output_lists_slots(self):
        r = cli("gta.py", "audit", str(BASE))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("GIRLFRIENDS", r.stdout)
        self.assertIn("CJ'S HOUSE GARAGE", r.stdout)


if __name__ == "__main__":
    unittest.main()