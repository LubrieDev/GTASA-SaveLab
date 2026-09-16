"""Core reliability tests for the file layer: block parsing, checksum, version.

Every test works on an in-memory copy of the public reference save
``savefiles/base.b``. Nothing in this file writes inside the repository.
"""

import struct
import tempfile
import unittest
from pathlib import Path

from gtasa import savefile
from tests._paths import BASE

ORIGINAL = BASE.read_bytes()


class TestReferenceLoads(unittest.TestCase):
    """The public reference save must parse cleanly."""

    def test_reference_file_exists(self):
        self.assertTrue(BASE.is_file(), "savefiles/base.b must be tracked")

    def test_file_size_is_multiple_of_four(self):
        self.assertEqual(len(ORIGINAL) % 4, 0)

    def test_29_blocks_recognized(self):
        sf = savefile.Save(bytearray(ORIGINAL))
        self.assertEqual(len(sf.bloques), savefile.N_BLOQUES)
        self.assertEqual(len(sf.bloques), 29)

    def test_block_names_table_matches(self):
        self.assertEqual(len(savefile.NOMBRES), 29)


class TestBlockStructure(unittest.TestCase):
    """Block boundaries must be exact, sequential and non-overlapping."""

    @classmethod
    def setUpClass(cls):
        cls.sf = savefile.Save(bytearray(ORIGINAL))

    def test_every_block_starts_with_tag(self):
        for b in self.sf.bloques:
            self.assertEqual(
                self.sf.buf[b.inicio:b.inicio + 5], b"BLOCK",
                f"block {b.n} ({b.nombre}) is missing its tag")

    def test_blocks_do_not_overlap_and_are_ordered(self):
        pos = 0
        for b in self.sf.bloques:
            self.assertEqual(b.inicio, pos, f"block {b.n} starts where the "
                                             f"previous one ended")
            pos += b.tam

    def test_fixed_sizes_match_serializer_table(self):
        for n, tam in savefile.FIJOS.items():
            b = self.sf.bloques[n]
            self.assertEqual(b.tam, tam,
                             f"fixed block {n} ({b.nombre}) must measure {tam}")

    def test_fixed_and_variable_cover_all_blocks(self):
        self.assertEqual(savefile.FIJOS.keys() | savefile.VARIABLES,
                         set(range(savefile.N_BLOQUES)))
        self.assertFalse(savefile.FIJOS.keys() & savefile.VARIABLES,
                         "a block cannot be both fixed and variable")

    def test_data_ends_before_garbage(self):
        self.assertLessEqual(self.sf.fin_datos, len(self.sf.buf))
        self.assertGreater(len(self.sf.buf) - self.sf.fin_datos, 0,
                           "the reference save must carry trailing garbage "
                           "that the game never reads")

    def test_briefs_have_no_tag_of_their_own(self):
        self.assertEqual(
            self.sf.buf[self.sf.inicio_briefs:self.sf.inicio_briefs + 5] != b"BLOCK",
            True, "SaveBriefs lives after block 28 without its own tag")


class TestVersion(unittest.TestCase):
    def test_version_is_current(self):
        sf = savefile.Save(bytearray(ORIGINAL))
        self.assertEqual(sf.version, 4)

    def test_version_crc_is_crc32_of_gtasa_string(self):
        crc = struct.unpack_from("<I", ORIGINAL, 5)[0]
        self.assertIn(crc, savefile.VERSIONES)
        self.assertEqual(savefile.VERSIONES[crc], 4)


class TestGlobals(unittest.TestCase):
    """The Mobile discriminator: 49,212 SCM globals (PC has 43,808)."""

    def test_scriptspace_declares_49212_bytes(self):
        sf = savefile.Save(bytearray(ORIGINAL))
        self.assertEqual(sf.tam_scriptspace(), 49212)

    def test_globals_count_is_12303(self):
        sf = savefile.Save(bytearray(ORIGINAL))
        self.assertEqual(sf.n_globals(), 12303)

    def test_global_out_of_range_raises(self):
        sf = savefile.Save(bytearray(ORIGINAL))
        with self.assertRaises(savefile.SaveError):
            sf.global_(sf.n_globals())


class TestChecksum(unittest.TestCase):
    """The Mobile checksum: sum of every byte except the last four."""

    @classmethod
    def setUpClass(cls):
        cls.sf = savefile.Save(bytearray(ORIGINAL))

    def test_formula_matches_stored_value(self):
        self.assertEqual(self.sf.checksum_calculado(),
                         sum(ORIGINAL[:-4]) & 0xFFFFFFFF)
        self.assertEqual(self.sf.checksum_guardado(),
                         struct.unpack("<I", ORIGINAL[-4:])[0])

    def test_valid_reference_reports_ok(self):
        self.assertTrue(self.sf.checksum_ok())

    def test_edit_invalidates_until_recalculated(self):
        sf = savefile.Save(bytearray(ORIGINAL))
        antes = sf.leer(15, 4, "i")[0]            # money (data offset +4)
        sf.escribir(15, 4, "i", antes + 1)
        self.assertFalse(sf.checksum_ok(),
                         "a data change must invalidate the checksum")
        sf.cerrar_checksum()
        self.assertTrue(sf.checksum_ok(),
                        "recaclulating must restore a valid checksum")
        self.assertEqual(sf.checksum_guardado(), sf.checksum_calculado())

    def test_guardar_recalculates_checksum(self):
        with tempfile.TemporaryDirectory() as td:
            destino = Path(td) / "copy.b"
            sf = savefile.Save(bytearray(ORIGINAL))
            n = sf.guardar(destino)
            self.assertEqual(n, len(ORIGINAL))
            check = savefile.Save.abrir(destino)
            self.assertTrue(check.checksum_ok())
            self.assertFalse(check.problemas())


class TestRoundTrip(unittest.TestCase):
    """read -> write equivalent save -> read: stays structurally valid."""

    def test_guardar_preserves_block_layout(self):
        with tempfile.TemporaryDirectory() as td:
            destino = Path(td) / "copy.b"
            sf = savefile.Save(bytearray(ORIGINAL))
            sf.guardar(destino)
            nuevamente = savefile.Save.abrir(destino)
            original = [(b.inicio, b.tam, b.fijo) for b in sf.bloques]
            repetido = [(b.inicio, b.tam, b.fijo) for b in nuevamente.bloques]
            self.assertEqual(original, repetido)
            self.assertEqual(nuevamente.fin_datos, sf.fin_datos)

    def test_guardar_changes_only_the_checksum(self):
        with tempfile.TemporaryDirectory() as td:
            destino = Path(td) / "copy.b"
            savefile.Save(bytearray(ORIGINAL)).guardar(destino)
            escrito = destino.read_bytes()
            cambiados = [i for i in range(len(ORIGINAL))
                         if ORIGINAL[i] != escrito[i]]
            limite = list(range(len(ORIGINAL) - 4, len(ORIGINAL)))
            self.assertTrue(set(cambiados) <= set(limite),
                            "saving an unmodified save must only touch the "
                            "trailing checksum")
            self.assertEqual(escrito[:-4], ORIGINAL[:-4])

    def test_edit_round_trip_keeps_structure(self):
        with tempfile.TemporaryDirectory() as td:
            destino = Path(td) / "edited.b"
            sf = savefile.Save(bytearray(ORIGINAL))
            sf.escribir(15, 4, "i", 42)
            sf.guardar(destino)
            reread = savefile.Save.abrir(destino)
            self.assertEqual(reread.leer(15, 4, "i")[0], 42)
            self.assertTrue(reread.checksum_ok())
            self.assertEqual(len(reread.bloques), 29)


class TestSaveRejectsCorruption(unittest.TestCase):
    """The sequential traversal must fail loudly, not silently mis-locate."""

    def test_corrupted_fixed_block_tag_raises(self):
        sf = savefile.Save(bytearray(ORIGINAL))
        roto = bytearray(ORIGINAL)
        del roto[sf[6].inicio]                    # knock the first byte of block 6's tag
        with self.assertRaises(savefile.SaveError):
            savefile.Save(roto)

    def test_corrupted_variable_block_tag_desynchronizes(self):
        sf = savefile.Save(bytearray(ORIGINAL))
        roto = bytearray(ORIGINAL)
        del roto[sf[10].inicio + 1]               # damage block 10's tag
        with self.assertRaises(savefile.SaveError):
            savefile.Save(roto)

    def test_unknown_version_rejected_before_writing(self):
        with tempfile.TemporaryDirectory() as td:
            destino = Path(td) / "rogue.b"
            roto = bytearray(ORIGINAL)
            struct.pack_into("<I", roto, 5, 0xFFFFFFFF)
            sf = savefile.Save(roto)
            self.assertIsNone(sf.version)
            self.assertTrue(sf.problemas())
            with self.assertRaises(savefile.SaveError):
                sf.guardar(destino)
            self.assertFalse(destino.exists(),
                             "a structurally rejected save must not be written")


class TestResize(unittest.TestCase):
    """Variable-size blocks can grow/shrink without moving the file size."""

    def test_grow_variable_block_keeps_file_size_alignment(self):
        sf = savefile.Save(bytearray(ORIGINAL))
        bloque1 = sf.bytes_de(1)
        sf.reemplazar_bloque(1, bloque1 + b"\x00" * 16)
        self.assertEqual(len(sf.buf), len(ORIGINAL),
                         "the trailing garbage must absorb the growth")
        self.assertEqual(len(sf.buf) % 4, 0)
        self.assertEqual(len(sf.bloques), 29)
        self.assertTrue(sf.checksum_ok())

    def test_shrink_variable_block_keeps_file_size(self):
        sf = savefile.Save(bytearray(ORIGINAL))
        bloque1 = sf.bytes_de(1)
        self.assertGreater(len(bloque1), 24)
        sf.reemplazar_bloque(1, bloque1[:-8])
        self.assertEqual(len(sf.buf), len(ORIGINAL))
        self.assertTrue(sf.checksum_ok())

    def test_fixed_block_rejects_resize(self):
        sf = savefile.Save(bytearray(ORIGINAL))
        for n in (0, 15, 16, 28):
            with self.subTest(block=n):
                with self.assertRaises(savefile.SaveError):
                    sf.reemplazar_bloque(n, b"\x00" * 10)


if __name__ == "__main__":
    unittest.main()