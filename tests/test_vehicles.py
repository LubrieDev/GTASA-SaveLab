"""Tests for the 64-byte CStoredCar grid (block 3) of every garage slot.

Everything runs on an in-memory copy of the reference save. The armor/proof
mask is exercised over all 80 slots of the 20 garages.
"""

import math
import struct
import unittest

from gtasa import armor, garage, houses
from tests._paths import BASE

ORIGINAL = BASE.read_bytes()


def todas_las_plazas(data):
    for g in range(houses.N_GARAJES):
        for k in range(houses.N_PLAZAS):
            yield g, k, houses.off_plaza(data, g, k)


class TestGridLayout(unittest.TestCase):
    """The grid equations from houses.py must match block 3 exactly."""

    def test_first_slot_is_payload_plus_39(self):
        payload = houses.payload(ORIGINAL)
        self.assertEqual(houses.off_plaza(ORIGINAL, 0, 0), payload + houses.REJILLA)

    def test_garage_stride_is_64_and_slot_stride_is_1280(self):
        for g in range(houses.N_GARAJES):
            self.assertEqual(houses.off_plaza(ORIGINAL, g, 0),
                             houses.off_plaza(ORIGINAL, 0, 0) + houses.PASO_GARAJE * g)
        for k in range(houses.N_PLAZAS):
            self.assertEqual(houses.off_plaza(ORIGINAL, 0, k),
                             houses.off_plaza(ORIGINAL, 0, 0) + houses.PASO_PLAZA * k)

    def test_grid_plus_garage_array_fits_the_block(self):
        ini = houses.payload(ORIGINAL)
        fin = houses.payload(ORIGINAL) + houses.ARRAY + houses.N_ENTRADAS * houses.LEN_ENTRADA
        offs_last = houses.off_plaza(ORIGINAL, houses.N_GARAJES - 1, houses.N_PLAZAS - 1)
        self.assertLess(offs_last + 64, fin)
        self.assertEqual(fin, houses.payload(ORIGINAL) + 9159)

    def test_upgrade_slots_stay_inside_the_record(self):
        ultimo = houses.MEJORAS_OFF + 2 * houses.MEJORAS_N
        self.assertLessEqual(ultimo, 64, "ten int16 upgrades must fit in the record")


class TestSlotStates(unittest.TestCase):
    """describir's states and es_fantasma must agree on every slot."""

    def test_states_exhaust_and_agree_with_es_fantasma(self):
        for g, k, off in todas_las_plazas(ORIGINAL):
            with self.subTest(slot=(g, k)):
                x, y, z, marca, modelo, estado = garage.describir(ORIGINAL, off)
                self.assertIn(estado, ("ocupada", "FANTASMA", "libre", "LIBRE (limpia)"))
                self.assertEqual(garage.es_fantasma(ORIGINAL, off), estado == "FANTASMA")
                if estado == "FANTASMA":
                    self.assertNotEqual(modelo, 0)
                    self.assertFalse(all(math.isfinite(v) for v in (x, y, z)))

    def test_cj_garage_matches_reference(self):
        estados = [garage.describir(ORIGINAL, houses.off_plaza(ORIGINAL, 0, k))[5]
                   for k in range(houses.N_PLAZAS)]
        self.assertEqual(estados, ["ocupada", "ocupada", "LIBRE (limpia)", "LIBRE (limpia)"])

    def test_occupied_slots_have_finite_positions(self):
        for g, k, off in todas_las_plazas(ORIGINAL):
            if garage.describir(ORIGINAL, off)[5] == "ocupada":
                with self.subTest(slot=(g, k)):
                    x, y, z, *_ = garage.describir(ORIGINAL, off)
                    self.assertTrue(all(math.isfinite(v) for v in (x, y, z)))


class TestProofFlags(unittest.TestCase):
    """The mask preserves the unknown high bits (0x20/0x40/0x80)."""

    @classmethod
    def setUpClass(cls):
        cls.offs = [off for _, _, off in todas_las_plazas(ORIGINAL)]
        cls.antes = [ORIGINAL[off + armor.OFF_BLINDAJE] for off in cls.offs]

    def test_blindado_keeps_high_bits_and_sets_low_five(self):
        buf = bytearray(ORIGINAL)
        for off in self.offs:
            armor.aplicar(buf, off, armor.BLINDADO)
        for off, antes in zip(self.offs, self.antes):
            ahora = buf[off + armor.OFF_BLINDAJE]
            self.assertEqual(ahora & ~armor.MASCARA, antes & ~armor.MASCARA)
            self.assertEqual(ahora & armor.MASCARA, armor.BLINDADO)

    def test_normal_keeps_high_bits_and_clears_low_five(self):
        buf = bytearray(ORIGINAL)
        for off in self.offs:
            armor.aplicar(buf, off, armor.NORMAL)
        for off, antes in zip(self.offs, self.antes):
            ahora = buf[off + armor.OFF_BLINDAJE]
            self.assertEqual(ahora & ~armor.MASCARA, antes & ~armor.MASCARA)
            self.assertEqual(ahora & armor.MASCARA, 0)

    def test_blindado_then_normal_clears_only_proof_bits(self):
        buf = bytearray(ORIGINAL)
        for off in self.offs:
            armor.aplicar(buf, off, armor.BLINDADO)
            armor.aplicar(buf, off, armor.NORMAL)
        for off, antes in zip(self.offs, self.antes):
            self.assertEqual(buf[off + armor.OFF_BLINDAJE], antes & ~armor.MASCARA)

    def test_known_reference_has_a_proofed_slot(self):
        resultado = None
        for g, k, off in todas_las_plazas(ORIGINAL):
            x, y, z, _, modelo, estado = garage.describir(ORIGINAL, off)
            bajos = armor.leer(ORIGINAL, off) & armor.MASCARA
            if estado == "ocupada" and bajos:
                resultado = (g, k, modelo, bajos)
                break
        self.assertIsNotNone(resultado,
                             "the reference save must carry at least one proofed car")
        self.assertEqual(resultado[3], armor.BLINDADO,
                         "the low five bits must be the full 0x1f, never partial")

    def test_proof_does_not_touch_position_or_model(self):
        buf = bytearray(ORIGINAL)
        off = houses.off_plaza(ORIGINAL, 0, 0)
        pos = struct.unpack_from("<fff", ORIGINAL, off)
        mod = struct.unpack_from("<h", ORIGINAL, off + 18)[0]
        armor.aplicar(buf, off, armor.BLINDADO)
        self.assertEqual(struct.unpack_from("<fff", buf, off), pos)
        self.assertEqual(struct.unpack_from("<h", buf, off + 18)[0], mod)


class TestGhostDetection(unittest.TestCase):
    """A real model with a NaN position is the ghost: it blocks the slot."""

    @classmethod
    def setUpClass(cls):
        cls.off_libre = houses.off_plaza(ORIGINAL, 0, 2)  # a clean/free slot

    def _fabricate(self):
        buf = bytearray(ORIGINAL)
        off = houses.off_plaza(buf, 0, 2)
        struct.pack_into("<fff", buf, off, float("nan"), float("nan"), float("nan"))
        struct.pack_into("<h", buf, off + 18, 524)  # Cement Truck
        return buf

    def test_fabricated_ghost_is_detected(self):
        buf = self._fabricate()
        self.assertTrue(garage.es_fantasma(buf, houses.off_plaza(buf, 0, 2)))

    def test_clean_slot_is_not_a_ghost(self):
        self.assertFalse(garage.es_fantasma(ORIGINAL, self.off_libre))

    def test_fantasma_description_matches(self):
        buf = self._fabricate()
        off = houses.off_plaza(buf, 0, 2)
        self.assertEqual(garage.describir(buf, off)[5], "FANTASMA")


if __name__ == "__main__":
    unittest.main()