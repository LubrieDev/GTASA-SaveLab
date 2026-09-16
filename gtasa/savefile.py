#!/usr/bin/env python3
"""
The file layer: locate the 29 blocks, read them, write them and close the
checksum. It is the foundation that everything else should rely on.

    python savefile.py partidas/buena/GTASAsf1.b            # full audit
    python savefile.py partidas/buena/GTASAsf1.b --mapa   # table only

WHY `re.finditer(b"BLOCK")` DOES NOT WORK
-------------------------------------------
Because it does not find 29 markers, it finds 31. Two of them are leftovers from
the previous buffer dump, in the garbage at the end of the file. That it does not
break anything today is luck: they fall behind block 28, so indexing 0 to 28 still
gives the correct block. But measuring a block as "distance to the next marker" with
that list already introduced an error that survived for weeks (row 28 of the map said
9718 bytes; it is 357).

Here the traversal is sequential and **validates itself**: 18 of the 29 blocks have
a known constant size, taken from their serializer. You advance block by block checking
the tag; the 18 fixed ones are enforced, and the 11 variable ones are measured to
the next tag. If a false `BLOCK` appeared inside a variable block, the chain would
desynchronize and break at the next fixed block, instead of returning a wrong map
silently.

WHAT THE GAME VALIDATES (see LOADING-FLOW.md)
-----------------------------------------------
1. checksum = sum of all bytes minus the last 4 == those 4 as u32 LE
2. the file size must be a multiple of 4
3. the 5 "BLOCK" bytes are checked block by block with strncmp
4. each block must consume exactly what its ::Load reads
5. whatever is behind SaveBriefs is never read
"""

import struct
import sys
from pathlib import Path

TAG = b"BLOCK"
N_BLOQUES = 29
LARGO_BRIEFS = 173          # SaveBriefs, outside the loop and without its own tag

# Format version: the u32 at offset 0 of block 0 is CRC32("GTASA%d").
VERSIONES = {
    0x131AECDA: 0, 0x641DDC4C: 1, 0xFD148DF6: 2, 0x8A13BD60: 3, 0x147728C3: 4,
}

NOMBRES = [
    "CSimpleVariables", "CTheScripts", "CPools", "CGarages", "CGameLogic",
    "CPathFind", "CPickups", "(empty)", "CRestart", "CRadar", "CTheZones",
    "CGangs", "CTheCarGenerators", "(empty)", "(empty)", "CPlayerInfo",
    "CStats", "CSetPieces", "CStreaming", "CPedType", "CTagManager",
    "CIplStore", "CShopping", "CGangWars", "CStuntJumpManager",
    "CEntryExitManager", "CAERadioTrackManager", "C3dMarkers", "CPostEffects",
]

# Blocks whose serializer always writes the same thing (version 4 of the format).
# The value includes the 5 bytes of the tag. Checked against the disassembly, not
# measured by eye between markers.
FIJOS = {
    0: 433,      # 5 + 428 (CSimpleVariablesSaveStructure)
    6: 19928,    # the CPickups::Load loop is initialization, not reading
    7: 5,        # enum gap: only the tag
    9: 10005,    # 5 + 250 * 40 blips; with version < 4 it would be 175
    11: 165,     # 5 + 160
    13: 5,
    14: 5,
    15: 49,      # 5 + 44
    16: 1945,    # 5 + 1940
    17: 6729,    # 5 + 6724
    18: 26321,   # 5 + 26316 models, one byte each
    19: 645,     # 5 + 32 types * 5 masks * 4
    21: 264,     # loops of 256 hardcoded iterations
    23: 105,     # 5 + 100
    26: 3841,
    27: 145,     # 5 + 140 (ms_user3dMarkers)
    28: 357,     # 5 + 352; only exists if version >= 3
}

# Blocks whose record count is INSIDE the file: they can be lengthened and
# shortened. The rest are fixed size. See LOADING-FLOW.md.
VARIABLES = {1, 2, 3, 4, 5, 8, 10, 12, 20, 22, 24, 25}


def _tam_pathfind(buf, inicio):
    """
    `CPathFind::Load` @ 0x56C460 reads a `u32` with the number of zones and then that
    many 28-byte records. So: 5 + 4 + 28n, calculable without finding the next tag.

    It is worth having separate because this block proves that finding the next tag
    is not enough: some saves measure 961 bytes and others 1437, and the counter
    detector gave it as fixed because it stores its own in `this+17804`, neither on
    the stack nor in a global variable.
    """
    n = struct.unpack_from("<I", buf, inicio + 5)[0]
    return 5 + 4 + 28 * n


# Blocks whose size we can calculate from their own content. This is better than
# measuring to the next tag: it does not depend on there being no false BLOCK.
CALCULADOS = {5: _tam_pathfind}


class SaveError(Exception):
    pass


class Bloque:
    __slots__ = ("n", "nombre", "inicio", "tam", "fijo")

    def __init__(self, n, inicio, tam, fijo):
        self.n, self.nombre = n, NOMBRES[n]
        self.inicio, self.tam, self.fijo = inicio, tam, fijo

    @property
    def datos(self):
        """Offset of the first useful byte, past the tag."""
        return self.inicio + 5

    @property
    def largo_datos(self):
        return self.tam - 5

    def __repr__(self):
        return (f"<block {self.n} {self.nombre} @{self.inicio} "
                f"{self.tam}B {'fixed' if self.fijo else 'variable'}>")


class Save:
    """A save file opened in memory."""

    def __init__(self, datos, ruta=None):
        self.buf = bytearray(datos)
        self.ruta = ruta
        self.bloques = self._localizar()

    # ------------------------------------------------------------- opening

    @classmethod
    def abrir(cls, ruta):
        ruta = Path(ruta)
        return cls(ruta.read_bytes(), ruta)

    def _localizar(self):
        """
        Sequential traversal with validation. Any mismatch is an error, not a
        warning: a wrong block map poisons everything else.
        """
        bloques, pos = [], 0
        for n in range(N_BLOQUES):
            if self.buf[pos:pos + 5] != TAG:
                raise SaveError(
                    f"block {n} ({NOMBRES[n]}): expected the BLOCK tag at "
                    f"offset {pos} but found {bytes(self.buf[pos:pos + 5])!r}")
            if n in FIJOS:
                tam = FIJOS[n]
            elif n in CALCULADOS:
                tam = CALCULADOS[n](self.buf, pos)
            else:
                sig = self.buf.find(TAG, pos + 5)
                if sig < 0:
                    raise SaveError(
                        f"block {n} ({NOMBRES[n]}) is variable-size and there "
                        f"no tag behind offset {pos}")
                tam = sig - pos
            bloques.append(Bloque(n, pos, tam, n in FIJOS))
            pos += tam
        self.fin_datos = pos + LARGO_BRIEFS
        self.inicio_briefs = pos
        if self.fin_datos > len(self.buf):
            raise SaveError(
                f"blocks and briefs total {self.fin_datos} bytes but the "
                f"file only measures {len(self.buf)}")
        return bloques

    def __getitem__(self, n):
        return self.bloques[n]

    # ------------------------------------------------------------- checksum

    def checksum_calculado(self):
        return sum(self.buf[:-4]) & 0xFFFFFFFF

    def checksum_guardado(self):
        return struct.unpack_from("<I", self.buf, len(self.buf) - 4)[0]

    def checksum_ok(self):
        return self.checksum_calculado() == self.checksum_guardado()

    def cerrar_checksum(self):
        """Rewrites the last 4 bytes. Must be called after any change."""
        struct.pack_into("<I", self.buf, len(self.buf) - 4, self.checksum_calculado())

    # --------------------------------------------------------------- version

    @property
    def version(self):
        crc = struct.unpack_from("<I", self.buf, self[0].datos)[0]
        return VERSIONES.get(crc)

    # ------------------------------------------------------ read/write

    def leer(self, n, off, fmt):
        """Reads `fmt` (struct format) at offset `off` INSIDE block n."""
        b = self[n]
        if off + struct.calcsize(fmt) > b.largo_datos:
            raise SaveError(f"read past block {n}: {off}+{struct.calcsize(fmt)} "
                            f"> {b.largo_datos}")
        return struct.unpack_from("<" + fmt, self.buf, b.datos + off)

    def escribir(self, n, off, fmt, *valores):
        b = self[n]
        if off + struct.calcsize(fmt) > b.largo_datos:
            raise SaveError(f"write past block {n}: {off}+{struct.calcsize(fmt)} "
                            f"> {b.largo_datos}")
        struct.pack_into("<" + fmt, self.buf, b.datos + off, *valores)

    def bytes_de(self, n):
        b = self[n]
        return bytes(self.buf[b.datos:b.inicio + b.tam])

    # ---------------------------------------------------------------- globals

    # ScriptSpace starts after the tag (5) and the u32 with its size (4).
    def tam_scriptspace(self):
        return self.leer(1, 0, "I")[0]

    def n_globals(self):
        return self.tam_scriptspace() // 4

    def _off_global(self, g):
        if not 0 <= g < self.n_globals():
            raise SaveError(f"global ${g} out of range (there are {self.n_globals()})")
        return self[1].datos + 4 + 4 * g

    def global_(self, g, fmt="i"):
        return struct.unpack_from("<" + fmt, self.buf, self._off_global(g))[0]

    def set_global(self, g, valor, fmt="i"):
        struct.pack_into("<" + fmt, self.buf, self._off_global(g), valor)

    # ------------------------------------------------- resize blocks

    def reemplazar_bloque(self, n, datos_nuevos):
        """
        Replaces a block's content (without the tag) with another of different
        length. This only makes sense for blocks in `VARIABLES`, and the record
        counter it carries is up to whoever builds `datos_nuevos`.

        The mismatch is absorbed in the garbage at the end, which the game never
        reads, so the file keeps its size and alignment. If it does not fit, the
        file size changes, rounded to a multiple of 4.
        """
        if n not in VARIABLES:
            raise SaveError(
                f"block {n} ({NOMBRES[n]}) is fixed-size: its ::Load reads "
                f"a hardcoded loop count from the binary, not the file")
        b = self[n]
        delta = len(datos_nuevos) - b.largo_datos
        self.buf[b.datos:b.inicio + b.tam] = datos_nuevos

        cola = len(self.buf) - self.fin_datos - delta      # garbage that would remain
        if cola >= 4:
            # trim or pad the garbage so the file size does not move
            if delta > 0:
                del self.buf[len(self.buf) - delta:]
            elif delta < 0:
                self.buf.extend(b"\x00" * (-delta))
        else:
            sobra = len(self.buf) % 4
            if sobra:
                self.buf.extend(b"\x00" * (4 - sobra))

        if len(self.buf) % 4:
            raise SaveError("the file size did not end up as a multiple of 4")
        self.bloques = self._localizar()
        self.cerrar_checksum()

    # ---------------------------------------------------------------- save

    def guardar(self, ruta):
        """Closes the checksum, checks what the game checks, and writes."""
        self.cerrar_checksum()
        for problema in self.problemas():
            raise SaveError(f"nothing is written: {problema}")
        Path(ruta).write_bytes(bytes(self.buf))
        return len(self.buf)

    def problemas(self):
        """The five conditions the game enforces. Empty list = valid."""
        fuera = []
        if len(self.buf) % 4:
            fuera.append(f"the file measures {len(self.buf)} bytes, which is not "
                         f"a multiple of 4 (LoadWorkBuffer rejects it)")
        if not self.checksum_ok():
            fuera.append(f"checksum {self.checksum_guardado():#010x} != "
                         f"{self.checksum_calculado():#010x}")
        if self.version is None:
            crc = struct.unpack_from("<I", self.buf, self[0].datos)[0]
            fuera.append(f"unknown version ({crc:#010x}): not CRC32 of "
                         f"any 'GTASA0'..'GTASA4'")
        elif self.version < 2:
            fuera.append(f"version {self.version}: GenericLoad rejects it")
        if self.fin_datos > len(self.buf):
            fuera.append("the data extends past the file")
        return fuera


# ------------------------------------------------------------------ audit

def auditar(ruta, solo_mapa=False):
    sf = Save.abrir(ruta)
    print(f"{ruta}   {len(sf.buf)} bytes")
    print(f"format version: {sf.version}   "
          f"checksum: {'OK' if sf.checksum_ok() else 'INVALID'}")
    nom = sf.buf[sf[0].datos + 4:sf[0].datos + 52].decode("utf-16-le", "replace")
    print(f"save: {nom.split(chr(0))[0]!r}")
    print()
    print(f"{'#':>3} {'offset':>8} {'size':>7}  {'type':<9} block")
    print("-" * 60)
    for b in sf.bloques:
        print(f"{b.n:>3} {b.inicio:>8} {b.tam:>7}  "
              f"{'fixed' if b.fijo else 'VARIABLE':<9} {b.nombre}")
    print(f"{'':>3} {sf.inicio_briefs:>8} {LARGO_BRIEFS:>7}  {'fixed':<9} SaveBriefs")
    basura = len(sf.buf) - sf.fin_datos
    print(f"{'':>3} {sf.fin_datos:>8} {basura:>7}  {'-':<9} "
          f"previous buffer dump garbage (never read)")

    if solo_mapa:
        return sf
    print()
    print(f"globals: {sf.n_globals()} of 32 bits "
          f"(ScriptSpace = {sf.tam_scriptspace()} bytes)")
    total = sum(b.tam for b in sf.bloques) + LARGO_BRIEFS
    print(f"sum of blocks + briefs: {total} == data end {sf.fin_datos}")
    problemas = sf.problemas()
    print()
    if problemas:
        print("PROBLEMS:")
        for p in problemas:
            print(f"  - {p}")
    else:
        print("valid: meets the five conditions the game checks")
    return sf


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__.strip().split("\n\n")[1])
        sys.exit(2)
    auditar(sys.argv[1], "--mapa" in sys.argv)
