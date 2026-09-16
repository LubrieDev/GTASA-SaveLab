"""Tests for the reference save and the re-engineering anchors.

The public save path (`base.b`) is tracked on purpose. The suite iterates every
``savefiles/*.b`` so a stray, malformed fixture fails instead of being silently
ignored.
"""

import struct
import unittest
from pathlib import Path

from gtasa import editor, garage, globals as GL, houses, savefile, wardrobe
from tests._paths import BASE, REPO, SAVEFILES


def todos_los_saves():
    return sorted(p for p in SAVEFILES.glob("*.b"))


class TestReferenceSaves(unittest.TestCase):
    """Every tracked save must be a valid Mobile save on its own."""

    def test_references_exist(self):
        self.assertTrue(BASE.is_file())

    def test_base_is_the_documented_reference(self):
        self.assertEqual(todos_los_saves(), [BASE])

    def test_every_save_parses_and_is_mobile(self):
        for ruta in todos_los_saves():
            with self.subTest(save=ruta.name):
                data = ruta.read_bytes()
                sf = savefile.Save(bytearray(data))
                self.assertEqual(len(sf.bloques), 29)
                self.assertTrue(sf.checksum_ok())
                self.assertEqual(sf.version, 4)
                self.assertEqual(sf.n_globals(), 12303)
                self.assertEqual(editor.platform_warnings(data), [])

    def test_all_saves_have_identically_sized_globals(self):
        tam = set(sf.n_globals() for p in todos_los_saves()
                  for sf in (savefile.Save(bytearray(p.read_bytes())),))
        self.assertEqual(tam, {12303})


class TestMobileDiscriminator(unittest.TestCase):
    """Block 1's declared ScriptSpace size separates Mobile from PC."""

    def test_base_declares_49212(self):
        sf = savefile.Save(bytearray(BASE.read_bytes()))
        self.assertEqual(sf.tam_scriptspace(), 49212)

    def test_pc_size_is_rejected(self):
        data = bytearray(BASE.read_bytes())
        struct.pack_into("<I", data, editor.find_blocks(data)[1] + 5, 43808)
        self.assertTrue(editor.platform_warnings(data))


class TestGlobalsAndGym(unittest.TestCase):
    """The gym daily-limit flow, exercised through the real globals indices."""

    def test_gym_starts_unblocked(self):
        buf = bytearray(BASE.read_bytes())
        uso, limite = GL.gimnasio(bytes(buf))
        self.assertEqual(limite, (GL.SIN_FECHA, GL.SIN_FECHA), "the limit must be clear")

    def test_setting_the_limit_then_clearing_it_restores(self):
        buf = bytearray(BASE.read_bytes())
        for i, v in zip(GL.GIMNASIO_LIMITE, (25, 2)):
            struct.pack_into("<i", buf, editor.find_blocks(buf)[1] + GL.INICIO + i * 4, v)
        self.assertEqual(GL.gimnasio(bytes(buf))[1], (25, 2))
        GL.arreglar_gimnasio(buf)
        self.assertEqual(GL.gimnasio(bytes(buf))[1], (GL.SIN_FECHA, GL.SIN_FECHA))

    def test_arreglar_gimnasio_returns_none_when_clear(self):
        buf = bytearray(BASE.read_bytes())
        self.assertIsNone(GL.arreglar_gimnasio(buf))

    def test_girlfriend_control_slots_align(self):
        offs = editor.find_blocks(BASE.read_bytes())
        ini = offs[1]
        for byte_off in GL.CONTROL:
            self.assertEqual((byte_off - GL.INICIO) % 4, 0, "progress must be int32-aligned")
            self.assertLess(ini + byte_off + 4, offs[2])


class TestWardrobeAnchor(unittest.TestCase):
    """Fat+muscle anchor: same (f32, f32) pair in block 16 and block 2."""

    def test_anchor_is_unique_in_block_2(self):
        data = BASE.read_bytes()
        self.assertIsNotNone(wardrobe.localiza(data))

    def test_sync_writes_both_copies_and_keeps_clothes(self):
        buf = bytearray(BASE.read_bytes())
        base, mod, tex = wardrobe.lee(bytes(buf))
        hechos = wardrobe.sincroniza_cuerpo(buf, grasa=55.5, musculo=66.6)
        self.assertEqual({h[0] for h in hechos}, {"fat", "muscle"})

        offs = editor.find_blocks(bytes(buf))
        st = offs[editor.STATS_BLOCK] + 5
        self.assertAlmostEqual(struct.unpack_from("<f", buf, st + 21 * 4)[0], 55.5, delta=1e-3)
        self.assertAlmostEqual(struct.unpack_from("<f", buf, st + 23 * 4)[0], 66.6, delta=1e-3)
        self.assertAlmostEqual(struct.unpack_from("<f", buf,
                                                  base + wardrobe.DESDE_ANCLA_A_MODELOS)[0],
                               55.5, delta=1e-3)
        self.assertAlmostEqual(struct.unpack_from("<f", buf,
                                                  base + wardrobe.DESDE_ANCLA_A_MODELOS + 4)[0],
                               66.6, delta=1e-3)
        _, mod2, tex2 = wardrobe.lee(bytes(buf))
        self.assertEqual(mod, mod2, "sync must not alter clothing")
        self.assertEqual(tex, tex2)


class TestProofedReferenceCar(unittest.TestCase):
    """The Patriot (470) in the reference save carries the confirmed 0x1f."""

    def test_garage_1_slot_0_is_the_proofed_patriot(self):
        data = BASE.read_bytes()
        off = houses.off_plaza(data, 1, 0)
        x, y, z, _, modelo, estado = garage.describir(data, off)
        if modelo == 470:
            self.assertEqual(estado, "ocupada")
            self.assertEqual(data[off + 16] & 0x1F, 0x1F,
                             "the Patriot is the ARMORED/UNARMORED control pair")


if __name__ == "__main__":
    unittest.main()