#!/usr/bin/env python3
"""
Editor for GTA San Andreas Mobile saves (.b).

Format deduced empirically from the 8 saves in this folder:

  * The file is a sequence of blocks (29 and 31 have been seen).
    NEITHER THE SIZE NOR THE NUMBER OF BLOCKS ARE FIXED: block 2 (Pools)
    grows with world entities, and a 260000-byte save has been seen that is
    perfectly valid. Each block starts with the ASCII signature "BLOCK"
    (5 bytes) and ends where the next one begins. Offsets are NOT fixed:
    block 1 (Scripts) changes size between saves, so the "BLOCK" markers
    must be located in each file.

  * Block 15 = PlayerInfo (49 bytes: "BLOCK" + dword size 0x28 + 40 data)
        +9   int32  Money
        +21  int32  DisplayMoney  (what the HUD shows; must match)

  * Block 16 = Stats (1940-byte payload after the signature)
        float[0..81]    -> offsets 0..327
        int  [82..304]  -> offsets 328..1219   (223 integers)
        tail of counters -> 1220..1939

  * Checksum: uint32 little-endian in the LAST 4 BYTES of the file,
    equal to the sum of all previous bytes (mod 2^32).
    Verified OK in the 8 original saves.
"""

import argparse
import re
import shutil
import struct
import sys

BLOCK_SIG = b"BLOCK"
PLAYERINFO_BLOCK = 15
STATS_BLOCK = 16
OFF_MONEY = 9
OFF_DISPLAY_MONEY = 21

# --- Identified float stats (index -> label) ----------------------
# Those marked [T] are confirmed against partidas/stats/STATSsf1.md: the player
# transcribed the statistics screen, and the screen value appears ONLY ONCE in the
# entire file. It is the same method as the minigun with 487 bullets.
#
# float[26] IS NOT RESPECT. This file said so and it was false: in the save from
# STATSsf1.md it is 19437.88, which is exactly the meters swum shown in the
# transcription, whereas that save's respect is 100%. The error came from assuming
# 21..26 were the player's six bars in sequence, counting instead of verifying.
# Consequence: --stats-max was writing 1000 on top of swim distance.
# WHERE THE REAL RESPECT IS: unidentified. It is 1000 in all saves seen, and there
# are dozens of floats at 1000, so it cannot be distinguished without a save where
# respect is NOT maxed out.
# CONFIDENCE LEVELS from the harvest (see PROJECT-MEMORY.md, "the mass harvest"):
#   [A] the screen value appears ONLY ONCE in the 260000 bytes. Unassailable.
#   [B] appears several times, but only ONE falls in a valid slot of block 16.
#       It is supported by an already-verified structure, not by "the one that fits".
#       Less solid.
#   No mark: identified earlier by differential.
FLOAT_STATS = {
    0:  "PROGRESS_MADE",
    1:  "TOTAL_PROGRESS",     # constant 187 in the 8 saves -> do not touch
    3:  "DIST_A_PIE",              # [A]
    4:  "DIST_EN_COCHE",           # [A]
    5:  "DIST_EN_MOTO",            # [A]
    6:  "DIST_EN_BARCO",           # [A]
    7:  "DIST_EN_CARRO_GOLF",      # [A]
    8:  "DIST_EN_HELICOPTERO",     # [A]
    9:  "DIST_EN_AVION",           # [A]
    10: "CABALLITO_MAS_LARGO",     # [A]
    11: "RUEDA_DELANTERA_MAS_LARGA",   # [A]
    12: "DOS_RUEDAS_MAS_LARGO",    # [B]
    13: "GASTO_EN_ARMAS",          # [A]
    14: "GASTO_EN_MODA",           # [A]
    15: "GASTO_EN_PROPIEDADES",    # [A]
    16: "GASTO_EN_REPARACIONES",   # [A]
    20: "GASTO_EN_COMIDA",         # [A]
    21: "FAT",                     # [A] 550.50 = "Fat: 55%"
    22: "STAMINA",                 # [S] probe: 110 -> screen "Stamina 11%"
    23: "MUSCLE",                  # [S] probe: 130 -> screen "Muscle 13%"
    24: "MAX_HEALTH",              # [S] does not appear on the stats screen, but DOES on the
                                   # health bar: with 170 the player was almost out of health.
                                   # In SA max health is its own stat (goes up by running,
                                   # paramedic missions, and drops from dying a lot): it does
                                   # NOT depend on stamina or muscle, so even though the probe
                                   # lowered all three, only this one can empty the bar.
    # [A] 415.00 = "Sex appeal: 41%".
    # Does not come from clothing: stripping naked and putting on a full suit left it
    # pinned at 500. What lowers it is still unknown. It is paired with float[80],
    # which is always double in saves we have not hand-edited.
    25: "SEX_APPEAL",
    26: "DIST_A_NADO",             # [A]+[S] IS NOT RESPECT, see above. It was the CONTROL
                                   # for the probe: 190 -> screen "swim distance 190.00 m".
    27: "DIST_EN_BICI",            # [A]
    28: "DIST_MAQUINA_CORRER",     # [A]
    29: "DIST_BICI_ESTATICA",      # [A]
    30: "GASTO_EN_TATUAJES",       # [B] resolved by cross-referencing two transcriptions
    31: "GASTO_EN_PELUQUERIA",     # [A]
    33: "GASTO_EN_PROSTITUTAS",    # [A]
    35: "APOSTADO_GASTADO",        # [A]
    36: "GANADO_COMO_CHULO",       # [A]
    37: "APOSTADO_GANADO",         # [B]
    38: "MAYOR_GANANCIA_APUESTA",  # [A]
    39: "MAYOR_PERDIDA_APUESTA",   # [A]
    54: "GASTO_EN_STRIPTEASE",     # [A]
    55: "GASTO_EN_TUNEO",          # [A]
    62: "GASTO_TOTAL_COMPRAS",     # [A]
    64: "DRIVING_SKILL",
    # 65, 66 and 67 are NOT flying, motorcycles and bicycle. Proven in two ways:
    #
    #  1. The probe wrote 23%, 29% and 31%; the screen kept showing 100% on all three.
    #     And when saving they came back intact (230, 290, 310): the game does NOT
    #     reconcile them, it simply does not read them for that screen.
    #  2. Without any probe: in partidas/stats/GTASAsf1.b, float[67] is 0 and float[66] is
    #     880, and the transcription of THAT save says "bicycles 100%" and
    #     "motorcycles 100%". A field at 0 cannot paint a 100%.
    #
    # float[65] and [66] DO grow by playing (200->700->1000 and 120->880 in the player's
    # saves), so they are stats for something; they are just not what they claimed.
    # float[67] is 0 in the player's 20 original saves: the 8 that have 1000 are all
    # descended from our edits. We wrote them ourselves.
    #
    # Where the screen's 100% comes from: not determined. In block 16 there is no
    # unidentified float left that is >=1000, which is the minimum to paint a 100%,
    # so those percentages come from somewhere else -- script globals like the
    # driving school, or calculated on the fly.
    65: "DESCONOCIDO_65",          # crece jugando, pero no es el vuelo
    66: "DESCONOCIDO_66",          # crece jugando, pero no son las motos
    67: "DESCONOCIDO_67",          # 0 en todas las partidas reales
    68: "RESPETO",                 # [S] NO ES LUNG_CAPACITY. Ver abajo.
    # [S] se le escribio 830 y la Suerte siguio en 1000, asi que no es la suerte.
    # Va PEGADO al sex appeal: f[80] = 2 x f[25] en las 12 partidas de la familia
    # actual, niveles y saltos. Se descuadra en las que editamos a mano.
    80: "DESCONOCIDO_LIGADO_A_SEX_APPEAL",
}

# [S] = confirmed by PROBE: a unique value was written and the screen showed it.
# That is the strongest level of proof here, because the game paints it.
#
# float[68] IS RESPECT, NOT LUNG_CAPACITY. 730 was set with muscle maxed out and the
# respect bar on the screen went down; no other stat moved. Before that the
# differential already gave it away: it grew +75.75 and +65.75 in two different
# sessions WITHOUT THE PLAYER SWIMMING A SINGLE METER (float[26] did not move once),
# and both times it coincided with killing gang members (+39 and +37).
#
# The percentage the screen shows is NOT value/10:
#
#     float[68]   muscle   screen
#      1075.75      1000     100%
#      1075.75       130      95%
#       730.00      1000      89%
#
# 730 should give 73% and gives 89%: there are about +160 from something else.
# And muscle also matters. So the DISPLAYED respect is calculated from several
# things; float[68] is the stored one, which is what goes up from killing rivals.
#
# WHERE LUNG_CAPACITY IS: unidentified. No data has revealed it because the
# player has not swum in any of the measured sessions.

# Integers. int[] starts at index 82.
INT_STATS = {
    82:  "ABATIDOS_POR_OTROS",     # [A]
    83:  "ABATIDOS_POR_TI",        # [A]
    84:  "VEHICULOS_DESTRUIDOS",   # [A]
    85:  "BARCOS_DESTRUIDOS",      # [B]
    86:  "AVIONES_DESTRUIDOS",     # [B]
    88:  "BALAS_DISPARADAS",       # [A]
    89:  "KG_DE_EXPLOSIVOS",       # [B]
    90:  "BALAS_EN_EL_BLANCO",     # [A]
    91:  "RUEDAS_REVENTADAS",      # [A]
    92:  "DISPAROS_EN_LA_CABEZA",  # [A]
    93:  "ESTRELLAS_OBTENIDAS",    # [A]
    94:  "ESTRELLAS_ELUDIDAS",     # [A]
    96:  "DIAS_TRANSCURRIDOS",     # [A]
    97:  "VISITAS_AL_HOSPITAL",    # [A]
    98:  "VISITAS_PISOS_FRANCOS",  # [B]
    100: "VEHICULOS_REPINTADOS",   # [B]
    102: "ALTURA_MAX_SALTO",       # [B]
    103: "VUELTAS_MAX_SALTO",      # [B]
    104: "ROTACION_MAX_SALTO",     # [A]
    106: "SALTOS_UNICOS_VISTOS",   # [B] the collision broke when cross-referencing (20 -> 21)
    107: "SALTOS_UNICOS_HECHOS",   # [B]
    108: "INTENTOS_DE_MISION",     # [B]
    114: "VIGILANTE_ABATIDOS",     # [B]
    115: "INCENDIOS_APAGADOS",     # [B]
    116: "PAQUETES_ENTREGADOS",    # [B]
    118: "PUNTUACION_ULTIMO_BAILE",    # [B]
    123: "MISIONES_CAMION",        # [B]
    125: "RECLUTAS_ABATIDOS",      # [B]
    128: "FOTOGRAFIAS_TOMADAS",    # [B]
    133: "CHICAS_CHULEADAS",       # [B]
    139: "MUERTES_LEGITIMAS",      # [A]
    144: "SOBORNOS_POLICIALES",    # [B]
    146: "CUANTAS_NOVIAS",         # game's own counter, do not recalculate.
                                   # Also appeared in the harvest when cross-referencing (7 -> 6):
                                   # independent confirmation from the differential.
    149: "VECES_PILLADO_CACHO",    # [B] resolved by cross-referencing
    150: "CITAS_CON_EXITO",        # [B] resolved by cross-referencing
    151: "CHICAS_CON_LAS_QUE_CORTASTE",
    160: "VISITAS_AL_GIMNASIO",    # [B]
    162: "COMIDAS_INGERIDAS",      # [B]
    164: "TIEMPO_CANTERA_SEG",     # [A]
    178: "INCENDIOS_INICIADOS",    # [A]
    196: "TERRITORIOS_CONQUISTADOS",   # [B]
    197: "TERRITORIOS_PERDIDOS",   # [B]
    200: "MIEMBROS_RECLUTADOS",    # [B]
    201: "BANDAS_ENEMIGAS_ABATIDOS",   # [A]
    202: "BANDAS_ALIADAS_ABATIDOS",    # [B]
    214: "PROGRESO_NOVIA_0",       # int[214+n], la copia que pinta la pantalla
}

# Race times go in pairs (best position, best time in seconds) from 221 to 263.
# Identified at level [B]; the pattern of pairs separated by 2 is consistent
# across all 20 races, which supports them.
INT_STATS.update({
    221: "T_LOWRIDER_RACE",  225: "T_BACKROAD_WANDERER", 227: "T_CITY_CIRCUIT",
    229: "T_VINEWOOD",       231: "T_FREEWAY",           233: "T_INTO_THE_COUNTRY",
    235: "T_BADLANDS_A",     237: "T_BADLANDS_B",        239: "T_DIRTBIKE_DANGER",
    243: "T_GO_GO_KART",     245: "T_SF_FASTLANE",       249: "T_COUNTRY_ENDURANCE",
    251: "T_SF_TO_LV",       253: "T_DAM_RIDER",         255: "T_DESERT_TRICKS",
    257: "T_LV_RINGROAD",    258: "T_WORLD_WAR_ACES",    260: "T_MILITARY_SERVICE",
    261: "T_CHOPPER_CHECKPOINT", 263: "T_HELI_HELL",
    174: "T_8_TRACK_VUELTA", 182: "T_DIRT_TRACK",        184: "T_NRG_500",
    181: "T_DIRT_TRACK_VUELTA",
})

# UNRESOLVED COLLISIONS. Two different anchors with the SAME value fall in the same
# slot, so at most one is correct and it is not known which. They are not recorded:
#   int[106]  "unique jumps found" / "last 5-star pursuit"  (20)
#   int[109]  "highest bank balance" / "missions passed"    (145)
#   int[152]  "prostitutes visited" / "longest time on 2 wheels"  (9)
#   int[223]  "heaviest weight on bench" / "best time Little Loop" (49)
# int[146] had the same collision with "longest time on front wheel" (7), but by
# then it was already known from the differential that it is the girlfriend counter:
# the collision is resolved in favor of the confirmed one. It serves as a warning
# of how fragile level [B] is when the value is small.
# The 11 weapon skills follow in 69..79
WEAPON_SKILLS = {
    69: "SKILL_PISTOL",
    70: "SKILL_PISTOL_SILENCED",
    71: "SKILL_DESERT_EAGLE",
    72: "SKILL_SHOTGUN",
    73: "SKILL_SAWNOFF",
    74: "SKILL_COMBAT_SHOTGUN",
    75: "SKILL_MICRO_SMG",
    76: "SKILL_SMG",
    77: "SKILL_AK47",
    78: "SKILL_M4",
    79: "SKILL_RIFLE",
}
FLOAT_STATS.update(WEAPON_SKILLS)

# Stats that are maxed out. They are 0..1000 player bars.
#
# 26 WAS HERE AND SHOULD NOT HAVE BEEN: it is swim distance, not respect (see above).
# Every --stats-max was writing 1000 meters on top of it. Respect stays un-maxed
# until it is known where it lives: better not to touch it than to touch the
# neighboring field.
#
# Not all of them cap at 1000 either: the game itself wrote 1030.30 in DRIVING_SKILL
# and 1075.75 in LUNG_CAPACITY after a session. Setting them to 1000 could LOWER them.
# 65, 66 and 67 WERE HERE AND SHOULD NOT HAVE BEEN, same as 26. They are not flying,
# motorcycles or bicycle (see above), and 67 is 0 in the player's 20 original saves:
# every --stats-max was writing 1000 to a field the game leaves at zero.
MAXABLE = [22, 23, 24, 25, 64, 68] + list(WEAPON_SKILLS)


# THE SIZE IS NOT FIXED. It was long believed that a mobile save measured exactly
# 195000 bytes, because the first 20 analyzed measured that. A later save from the
# same game measured 260000: block 2 (Pools), which stores loaded world entities,
# went from 5217 to 74765 bytes. The file was correct -- valid checksum, 49212
# globals, SimpleVars 433 -- and tools rejected it.
#
# The number of blocks IS fixed: there are ALWAYS 29. GenericSave iterates exactly
# 29 times (`cmp w27, #0x1d` @ 0x5617E0+0x274) and GenericLoad validates all 29
# tags one by one with strncmp. A sweep of "BLOCK" returning 31 does not mean there
# are 31 blocks: the extra two are remnants of the previous buffer dump, in the
# trailing garbage. Verified over the 70 saves in the repository: 140 false markers,
# all 140 at the tail, none inside the data.
#
# What DOES distinguish mobile from PC, and is the only thing to rely on:
BLOQUE_SCRIPTS = 1
MOBILE_SIMPLEVARS = 433     # PC: 317
MOBILE_GLOBALS = 49212      # PC: 43808  <- el discriminante fuerte
BLOQUES_MINIMOS = 29        # hay que llegar al 16 (Stats) con margen

# The file knows which slot it lives in: int32 at SimpleVars+44. Verified against
# the 23 saves in ORIGINALES, from 10 different slots, and it matches the file name
# number in all 23. Copying a save to another slot without touching this leaves a
# slot number inside that lies.
OFF_RANURA = 44


def find_blocks(data):
    """
    The starting offsets of the 29 blocks, plus a sentinel with the end of block 28
    (where SaveBriefs starts) so that `offs[n + 1]` also works for the last one.

    Previously this was bare `re.finditer(b"BLOCK")`. It returned 31 entries in the
    195000-byte saves, and the last two were garbage: that is why measuring a block
    as `offs[n+1] - offs[n]` gave 9718 bytes for block 28, when it is 357.
    Now the traversal is sequential and validated against the sizes imposed by each
    serializer. See savefile.py and LOADING-FLOW.md.
    """
    from . import savefile
    # Some places call this inside a loop over the file bytes, so the traversal
    # is memoized: iterating 195000 bytes for each byte of the file would be absurd.
    clave = None
    if isinstance(data, (bytes, str)):
        clave = hash(data)
        if clave in _CACHE_BLOQUES:
            return _CACHE_BLOQUES[clave]
    try:
        sf = savefile.Save(data)
    except savefile.SaveError as e:
        raise ValueError(str(e)) from None
    offs = [b.inicio for b in sf.bloques] + [sf.inicio_briefs]
    if clave is not None:
        if len(_CACHE_BLOQUES) > 8:
            _CACHE_BLOQUES.clear()
        _CACHE_BLOQUES[clave] = offs
    return offs


_CACHE_BLOQUES = {}


def platform_warnings(data):
    """Reasons why `data` does not look like a GTA SA Mobile save."""
    problems = []
    offs = [m.start() for m in re.finditer(BLOCK_SIG, data)]
    if len(offs) < BLOQUES_MINIMOS:
        problems.append(f"solo {len(offs)} bloques (minimo {BLOQUES_MINIMOS})")

    if len(offs) >= 2:
        sv = offs[1] - offs[0]
        if sv != MOBILE_SIMPLEVARS:
            problems.append(f"SimpleVars de {sv} bytes (movil: {MOBILE_SIMPLEVARS})")

        glob = struct.unpack_from("<I", data, offs[BLOQUE_SCRIPTS] + 5)[0]
        if glob != MOBILE_GLOBALS:
            problems.append(f"globals del script = {glob} (movil: {MOBILE_GLOBALS})")

        # Mobile stores the name in UTF-16; PC stores it in ANSI.
        name = data[offs[0] + 9: offs[0] + 29]
        if name[1:2] != b"\x00" and name[:1].isalnum():
            problems.append("nombre de partida en ANSI, no UTF-16 (tipico de PC)")

    return problems


def calc_checksum(data):
    return sum(data[:-4]) & 0xFFFFFFFF


def stored_checksum(data):
    return struct.unpack("<I", data[-4:])[0]


def fix_checksum(buf):
    """Rewrites the last 4 bytes with the correct sum."""
    struct.pack_into("<I", buf, len(buf) - 4, calc_checksum(buf))


def report(path):
    with open(path, "rb") as stream:
        data = stream.read()

    warns = platform_warnings(data)
    if warns:
        print(f"=== {path} ===")
        print("  NOT A GTA SA MOBILE SAVE  <-- do not copy to the phone")
        for w in warns:
            print(f"    - {w}")
        print("  A PC save passes checksum too: the sum does not distinguish platform.")
        # Only abort if blocks cannot even be located. A warning of another type is
        # shown, but the report continues: it is useful information.
        if len([m.start() for m in re.finditer(BLOCK_SIG, data)]) < BLOQUES_MINIMOS:
            return
        print()

    offs = find_blocks(data)
    pi, st = offs[PLAYERINFO_BLOCK], offs[STATS_BLOCK] + 5

    ok = calc_checksum(data) == stored_checksum(data)
    print(f"=== {path} ===")
    print(f"  size          : {len(data)} bytes")
    print(f"  checksum      : {'OK' if ok else 'INVALID  <-- the game will reject it'}"
          f"  (stored {stored_checksum(data):#010x} / calculated {calc_checksum(data):#010x})")
    print(f"  bloque 15 @ {offs[PLAYERINFO_BLOCK]}   bloque 16 @ {offs[STATS_BLOCK]}")

    money = struct.unpack_from("<i", data, pi + OFF_MONEY)[0]
    disp = struct.unpack_from("<i", data, pi + OFF_DISPLAY_MONEY)[0]
    print(f"  money         : ${money:,}   (HUD ${disp:,})")

    made = struct.unpack_from("<f", data, st + 0)[0]
    total = struct.unpack_from("<f", data, st + 4)[0]
    print(f"  progress      : {made:g} / {total:g} = {made / total * 100:.2f}%")
    print("  stats:")
    for idx in sorted(FLOAT_STATS):
        val = struct.unpack_from("<f", data, st + idx * 4)[0]
        print(f"    [{idx:2d}] {FLOAT_STATS[idx]:<22} {val:10.2f}")


def apply(path, money, fat, progress100, dry_run):
    data = open(path, "rb").read()
    orig_len = len(data)

    if calc_checksum(data) != stored_checksum(data):
        print(f"WARNING: {path} already has an invalid checksum before editing.", file=sys.stderr)

    offs = find_blocks(data)
    buf = bytearray(data)
    pi, st = offs[PLAYERINFO_BLOCK], offs[STATS_BLOCK] + 5

    changes = []

    def set_i32(off, val, label):
        old = struct.unpack_from("<i", buf, off)[0]
        struct.pack_into("<i", buf, off, val)
        changes.append((label, old, val))

    def set_f32(idx, val, label):
        off = st + idx * 4
        old = struct.unpack_from("<f", buf, off)[0]
        struct.pack_into("<f", buf, off, val)
        changes.append((f"[{idx:2d}] {label}", old, val))

    set_i32(pi + OFF_MONEY, money, "Money")
    set_i32(pi + OFF_DISPLAY_MONEY, money, "DisplayMoney")

    if progress100:
        total = struct.unpack_from("<f", buf, st + 4)[0]
        set_f32(0, total, "PROGRESS_MADE")

    set_f32(21, float(fat), "FAT")
    for idx in MAXABLE:
        set_f32(idx, 1000.0, FLOAT_STATS[idx])

    # The checksum ALWAYS at the end, when nothing else is being touched.
    fix_checksum(buf)

    assert len(buf) == orig_len, "file size must remain at 195000"

    for label, old, new in changes:
        o = f"{old:,}" if isinstance(old, int) else f"{old:.2f}"
        n = f"{new:,}" if isinstance(new, int) else f"{new:.2f}"
        print(f"  {label:<30} {o:>16}  ->  {n}")

    if dry_run:
        print("\n(dry-run: nothing was written)")
        return

    backup = path + ".bak"
    shutil.copy2(path, backup)
    print(f"\n  backup -> {backup}")
    with open(path, "wb") as fh:
        fh.write(buf)

    # Re-read from disk and validate
    check = open(path, "rb").read()
    assert len(check) == orig_len
    assert calc_checksum(check) == stored_checksum(check), "checksum written incorrectly"
    find_blocks(check)
    print(f"  wrote {path}: {len(check)} bytes, checksum OK, "
          f"{len(find_blocks(check)) - 1} blocks OK")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file")
    ap.add_argument("--report", action="store_true", help="show only, do not modify")
    ap.add_argument("--money", type=int, default=999_999_999)
    ap.add_argument("--fat", type=float, default=0.0)
    ap.add_argument("--no-progress", action="store_true",
                    help="do not touch PROGRESS_MADE")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if args.report:
        report(args.file)
        return

    if not (0 <= args.money <= 2_147_483_647):
        ap.error("--money must fit in a signed int32")

    print(f"=== editing {args.file} ===")
    apply(args.file, args.money, args.fat, not args.no_progress, args.dry_run)


if __name__ == "__main__":
    main()
