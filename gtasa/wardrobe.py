#!/usr/bin/env python3
"""
CJ's wardrobe: clothing, hair and tattoos.

Lives in block 2 (Pools), inside the player record, and is the structure that
GTA SA calls CPedClothesDesc:

    uint32  models[10]     the garment itself (the DFF)
    uint32  textures[18]   the pattern on top (the TXD); tattoos are texture only
    float   fat            copy of float[21] from the stats block
    float   muscle         copy of float[23]

**Writing here works in-game.** Five slots were changed at once on the star save
(shirt, jeans, afro, tattoo and removing the cap: 38 bytes) and CJ appeared dressed
exactly like that. No need to re-dress him or touch anything else.

Names are stored HASHED, not as text: one uint32 per garment. The hash function
has not been cracked (Jenkins-uppercase, Jenkins-as-is and CRC32 were tried against
2559 candidate names, zero hits), so you cannot write "the white shirt" here: you
must COPY the hash from a save that already has it. Each time the player tries
something on and saves, one more hash is learned.

**The offset is NOT fixed.** Block 2 grows with the loaded world (it has been seen
going from 5217 to 74765 bytes). The structure is located by the fat+muscle anchor,
which is read from the stats block: it is the same trick that weapons.py uses with
the weapons table.

    python wardrobe.py ver SAVE.b
    python wardrobe.py copiar ORIGEN.b DESTINO.b --parte torso --salida NUEVO.b
    python wardrobe.py quitar SAVE.b --parte cap --salida NUEVO.b
"""

import argparse
import struct
import sys

from .editor import find_blocks, fix_checksum

BLOQUE_POOLS = 2
BLOQUE_STATS = 16
N_MODELOS = 10
N_TEXTURAS = 18
# fat and muscle, which serve as anchor, live right after the two tables
DESDE_ANCLA_A_MODELOS = N_MODELOS * 4 + N_TEXTURAS * 4      # 112
STAT_GRASA = 21
STAT_MUSCULO = 23

# Confidence, with the same criteria as gtasa_editor.py:
#   [A] confirmed in-game -- the player made the change and the slot moved
#   [S] assumed -- fits the known GTA SA order, not checked
#
# The five [A] textures and four [A] models come from the August 6 expedition:
# six saves in a row, one thing changed between each two.
MODELOS = {
    0: ("torso",            "A"),   # white tank top
    1: ("pelo",             "A"),   # afro -- same name as textures[1] on purpose:
                                    # a garment is its TWO slots, and `--part hair`
                                    # must move the model and the texture at once
    # The only thing that is NOT store clothing: a save was held with EVERYTHING
    # removed and it did not move, and none of the game's nine categories touches it
    # either. The player's hypothesis is that it is CJ's underwear, which cannot be
    # removed.
    2: ("cuerpo_no_es_ropa", "B"),
    3: ("piernas",          "A"),   # blue jeans
    4: ("zapatos",          "A"),   # gray boots
    # Confirmed BY REMOVING, not by putting on: changing watches or chains did not
    # move any model because meshes are SHARED between store models. When removing
    # them, the game has to empty both slots, and that is where they are seen.
    5: ("cadena",           "A"),
    6: ("reloj",            "A"),
    7: ("accesorio_cara",   "A"),   # sunglasses and bandanas SHARE this slot
    8: ("gorra",            "A"),   # was set to 0 when taken off
    9: ("especial",         "A"),   # racing suit: goes ON TOP of everything else,
                                    # without clearing torso, legs or shoes
}
# The nine tattoo slots are 4..12, confirmed all at once on August 6: the player
# got eight tattoos in eight different places and each one landed where it should.
# The ninth (chest_right) is the only one NOT tattooed, and the only one that did
# not move: it remains by elimination, which is why it has [B] and not [A].
TEXTURAS = {
    0:  ("torso",              "A"),
    1:  ("pelo",               "A"),
    2:  ("piernas",            "A"),
    3:  ("zapatos",            "A"),   # gray boots
    4:  ("brazo_izq_arriba",   "A"),   # "tomb" tattoo
    5:  ("brazo_izq_abajo",    "A"),   # "gun" tattoo
    6:  ("brazo_der_arriba",   "A"),   # "Africa" tattoo, twice and the same hash
    7:  ("brazo_der_abajo",    "A"),   # "cross" tattoo
    8:  ("espalda",            "A"),   # "gun" tattoo
    9:  ("pecho_izq",          "A"),   # "gun" tattoo
    10: ("pecho_der",          "A"),   # "los santos" tattoo
    11: ("vientre",            "A"),   # "grove" tattoo
    12: ("lumbares",           "A"),   # "angel" tattoo
    13: ("cadena",             "A"),   # chain with dog tags
    14: ("reloj",              "A"),   # yellow watch
    15: ("accesorio_cara",     "A"),
    16: ("gorra",              "A"),
    17: ("especial",           "A"),   # same as above
}

# Hashes with field truth behind them. The player said exactly what they put on and
# the corresponding slot changed to this value. Everything else is "what they had on".
CONOCIDOS = {
    # clothing
    0xbb1ca4cc: "white tank top (Binco) -- model and texture, same hash",
    0x6a946537: "blue jeans (Binco) -- model",
    0x289acf8b: "blue jeans (Binco) -- texture",
    0xe7ea8d1e: "afro + mustache (Reece's) -- model",
    0x1f727cf5: "afro + mustache (Reece's) -- texture",
    0xe386ffc6: "black bandana (Binco, accessories) -- model",
    0xe13a33d3: "black bandana (Binco, accessories) -- texture",
    # what they had on and removed: in case they want it back someday
    0x9178aaf8: "black backwards cap (Victim) -- model",
    0x0b05fb28: "black backwards cap (Victim) -- texture",
    0xf6201912: "sunglasses -- model",
    0x2410fb33: "sunglasses -- texture",
    # accessories, August 6 batch
    0x14ef3a8e: "gray boots (ZIP, footwear) -- model",
    0x54b378b5: "gray boots (ZIP, footwear) -- texture",
    0x6cfb9521: "chain with dog tags (Binco) -- texture",
    0xdaf38efa: "yellow watch (Binco) -- texture",
    0x68448cb1: "red tinted glasses (Sub Urban) -- model",
    0xb19c0296: "red tinted glasses (Sub Urban) -- texture",
    0x540cca8d: "racing suit (special) -- model",
    0x6c53513a: "racing suit (special) -- texture",
    # what they had as default, identified by removing it
    0x58a07769: "Gnocchi silver watch (Victim, $3000) -- model, SHARED with the yellow one",
    0x1fd66177: "Gnocchi silver watch (Victim, $3000) -- texture",
    0xe97bc418: "cross chain (Didier Sachs, $5000) -- model, SHARED with the dog tags",
    0x18c24b92: "cross chain (Didier Sachs, $5000) -- texture",
    # no clothing: removing it does NOT leave the slot at 0, puts a "default" model
    0x2ff481ca: "bare torso (no shirt) -- model; its texture is 0",
    0x347251c1: "no pants -- model; its texture is 0",
    0xf79d4684: "barefoot -- model; its texture is 0",
    # tuxedo and patch batch
    0xc125783f: "patch (Binco, accessories, $5) -- model and texture, same hash",
    0x1ce95af0: "'los santos' tattoo (the first one, $80), right pectoral",
    0xd3f63df6: "tuxedo jacket (Didier Sachs, $7000) -- model",
    0x234fea60: "tuxedo jacket (Didier Sachs, $7000) -- texture",
    0x437acf0d: "tuxedo pants (Didier Sachs, $3000) -- model",
    0xc15babaa: "tuxedo pants (Didier Sachs, $3000) -- texture",
    0x08ddba02: "black shoes (Didier Sachs, $2500) -- model",
    0x762f281d: "black shoes (Didier Sachs, $2500) -- texture",
    0xed9cec60: "Crowex gold watch (Didier Sachs, $8000) -- texture; shared model",
    0x1970d283: "black glasses (Didier Sachs, $600) -- texture; shared model with the red ones",
    0xd4952fd2: "dark hat (Didier Sachs, $300) -- model",
    0x02643cfe: "dark hat (Didier Sachs, $300) -- texture",
    # tattoos: texture only, never model
    0x841a1073: "'tomb' tattoo, left arm",
    0x3a3376b3: "'gun' tattoo, left forearm",
    0x7e57d86f: "'Africa' tattoo, right arm",
    0x4783e837: "'cross' tattoo, right forearm",
    0xc859ae6e: "'gun' tattoo, back",
    0x70e5c90b: "'gun' tattoo, left pectoral",
    0x14b8bbd3: "'grove' tattoo (the third with the same name), abdomen",
    0x11bdd707: "'angel' tattoo, lower back",
}

PARTES = sorted({n for n, _ in MODELOS.values()} | {n for n, _ in TEXTURAS.values()})


def stat(data, idx):
    return struct.unpack_from("<f", data, find_blocks(data)[BLOQUE_STATS] + 5 + idx * 4)[0]


def localiza(data):
    """Offset of the first byte of the models table. By anchor, never fixed."""
    offs = find_blocks(data)
    ini, fin = offs[BLOQUE_POOLS] + 9, offs[BLOQUE_POOLS + 1]
    grasa, musculo = stat(data, STAT_GRASA), stat(data, STAT_MUSCULO)
    ancla = struct.pack("<ff", grasa, musculo)

    donde = [i for i in range(ini, fin - 8)
             if data[i:i + 8] == ancla]
    if not donde:
        raise ValueError(
            f"the fat={grasa:.1f} muscle={musculo:.1f} anchor does not appear in "
            f"block 2; without it the wardrobe location is unknown")
    if len(donde) > 1:
        raise ValueError(
            f"the fat={grasa:.1f} muscle={musculo:.1f} anchor appears "
            f"{len(donde)} times in block 2; ambiguous, not touching anything")
    return donde[0] - DESDE_ANCLA_A_MODELOS


def lee(data):
    b = localiza(data)
    mod = list(struct.unpack_from(f"<{N_MODELOS}I", data, b))
    tex = list(struct.unpack_from(f"<{N_TEXTURAS}I", data, b + N_MODELOS * 4))
    return b, mod, tex


def sincroniza_cuerpo(buf, grasa=None, musculo=None):
    """Writes fat and muscle in BOTH copies and returns what was done.

    They are duplicated: `float[21]` and `float[23]` from the stats block, and
    again at the end of the wardrobe in block 2. The block 2 copy is the one that
    deforms CJ's body; the stats copy is the one that paints the menu. Touching
    only one leaves the character showing one thing and displaying another -- the
    same breakdown that already happened with girlfriends, which had their state
    duplicated in globals and stats.

    Also, the (fat, muscle) pair is the ANCHOR with which the wardrobe is located.
    Throwing it off leaves `ropa.py` unable to find it.
    """
    b = localiza(bytes(buf))          # with the old values, before touching anything
    st = find_blocks(bytes(buf))[BLOQUE_STATS] + 5
    hechos = []
    for idx, valor, nombre in ((STAT_GRASA, grasa, "fat"),
                               (STAT_MUSCULO, musculo, "muscle")):
        if valor is None:
            continue
        antes = struct.unpack_from("<f", buf, st + idx * 4)[0]
        struct.pack_into("<f", buf, st + idx * 4, valor)
        off_pools = b + DESDE_ANCLA_A_MODELOS + (0 if idx == STAT_GRASA else 4)
        struct.pack_into("<f", buf, off_pools, valor)
        hechos.append((nombre, idx, antes, valor))
    return hechos


def ranuras(parte):
    """Returns [(which_table, index)] for the slots we call `parte`."""
    out = [("modelos", i) for i, (n, _) in MODELOS.items() if n == parte]
    out += [("texturas", i) for i, (n, _) in TEXTURAS.items() if n == parte]
    return out


def ver(path):
    data = open(path, "rb").read()
    b, mod, tex = lee(data)
    offs = find_blocks(data)
    print(f"=== {path} ===")
    print(f"  wardrobe in block 2 (Pools) +{b - offs[BLOQUE_POOLS] - 9}  "
          f"(absolute offset {b}; located by anchor, not fixed)\n")
    for titulo, tabla, mapa in (("MODELOS", mod, MODELOS), ("TEXTURAS", tex, TEXTURAS)):
        print(f"  {titulo}")
        for i, v in enumerate(tabla):
            nombre, conf = mapa[i]
            que = "empty" if v == 0 else f"0x{v:08x}"
            nota = CONOCIDOS.get(v, "")
            print(f"    [{i:2}] {nombre:<18} [{conf}]  {que:>10}"
                  + (f"   {nota}" if nota else ""))
        print()
    print(f"  fat {stat(data, STAT_GRASA):.1f}   "
          f"muscle {stat(data, STAT_MUSCULO):.1f}   (the anchor)")


def escribe(path, salida, cambios):
    """`cambios` is [(table, index, new_value, text)]."""
    data = open(path, "rb").read()
    buf = bytearray(data)
    b = localiza(data)
    for tabla, i, valor, texto in cambios:
        off = b + (i * 4 if tabla == "modelos" else N_MODELOS * 4 + i * 4)
        antes = struct.unpack_from("<I", buf, off)[0]
        struct.pack_into("<I", buf, off, valor)
        print(f"  {tabla[:-1]}[{i}] {texto}: 0x{antes:08x} -> 0x{valor:08x}")
    fix_checksum(buf)
    with open(salida, "wb") as f:
        f.write(buf)
    print(f"\n  wrote {salida} ({len(buf)} bytes, checksum recalculated)")


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    v = sub.add_parser("ver", aliases=["view"], help="shows the entire wardrobe")
    v.add_argument("save")

    c = sub.add_parser("copiar", aliases=["copy"], help="brings a garment from another save")
    c.add_argument("origen", help="the save that is wearing what you want")
    c.add_argument("destino", help="the save to dress")
    c.add_argument("--parte", required=True, choices=PARTES)
    c.add_argument("--salida", required=True)

    q = sub.add_parser("quitar", aliases=["remove"], help="empties a part (like taking off the cap)")
    q.add_argument("save")
    q.add_argument("--parte", required=True, choices=PARTES)
    q.add_argument("--salida", required=True)

    a = p.parse_args()
    try:
        if a.cmd in ("ver", "view"):
            ver(a.save)
            return 0

        objetivo = ranuras(a.parte)
        if not objetivo:
            print(f"'{a.parte}' is not a known slot")
            return 2

        if a.cmd in ("quitar", "remove"):
            escribe(a.save, a.salida,
                    [(t, i, 0, f"{a.parte} to empty") for t, i in objetivo])
        else:
            org = open(a.origen, "rb").read()
            _, mo, to = lee(org)
            cambios = []
            for t, i in objetivo:
                valor = mo[i] if t == "modelos" else to[i]
                cambios.append((t, i, valor, f"{a.parte} from {a.origen}"))
            escribe(a.destino, a.salida, cambios)
        return 0
    except (ValueError, OSError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
