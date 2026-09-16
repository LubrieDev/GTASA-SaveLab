#!/usr/bin/env python3
"""
Inspect and repair girlfriend state in a GTA SA Mobile save.

    python girlfriends.py <save> --inspeccionar
    python girlfriends.py <save> --recuperar denise --salida GTASAsf6.b

THREE THINGS, NOT ONE
---------------------
A girlfriend's state is spread across THREE places, and all three are needed:

  1. The MASK: global 1629, one byte, one bit per girlfriend. Without her bit,
     the game does not draw the heart on the map regardless of progress.
  2. The PROGRESS: global 1441 + 4*n.
  3. The STATS COPY: block 16, int[214 + n]. This is what PAINTS THE SCREEN.
     Without it the girlfriend exists but does not appear in the statistics list.

Discovering the third cost days. It was believed the list "only showed those
already dated"; in reality it reads the stats block, and in the 100% save the
two copies did not match (globals said 45, stats said 0).

ALL SIX, VERIFIED IN-GAME
--------------------------
    bit 0  global 1441  Denise Robinson
    bit 1  global 1445  Michelle Cannes
    bit 2  global 1449  Helena Wankstein
    bit 3  global 1453  Barbara Schternvart
    bit 4  global 1457  Katie Zhan
    bit 5  global 1461  Millie Perkins

Slot 7 (global 1465) is NOT a girlfriend: in the PC 100% save, with all six
obtained, it remains at -100 with the bit off.

Progress: -999 dead or blocked, -100 never obtained, 0 unknown, >0 percentage.

ERRORS THAT COST SEVERAL ATTEMPTS
----------------------------------
1. It was assumed Denise was 1461 because it was the only slot that fit.
   It was written there and nothing happened.
2. With the correct slot, progress was set without the mask. Nothing happened either.
3. With mask and progress, the girlfriend did not appear in the list: the stats
   copy was missing.
4. int[146] was recalculated as "mask bits". It is a game counter: after we wrote
   it and the game incremented it again, the count reached 7 (impossible).
5. int[151] was read as "girlfriends killed". It is "girls you have broken up with".

Moral: "the only one that fits" confirms nothing, and fixing one field is not
enough when state is spread out. Only seeing the complete transition in-game
counts.
"""

import argparse
import struct
import sys
from pathlib import Path

from .editor import calc_checksum, stored_checksum, find_blocks, platform_warnings

BLOQUE_SCRIPTS = 1
MASCARA_OFF = 1629          # one byte: bit n = "you have girlfriend n"
PROGRESO_BASE = 1441        # globals 1441 + 4*n

# THE STATE IS DUPLICATED. In addition to globals, block 16 (stats) stores its own
# copy, and it is the one that PAINTS THE statistics screen. It was discovered because
# in the 100% save the two copies did not match:
#
#     globals   1441..1461:  [-100,  6, 10, 45, 45, -999]
#     stats  int[214..219]:  [   0,  6, 10,  0,  0,    0]
#
# The game only listed Michelle and Helena. It was not that it showed "only those
# dated": it reads the stats block. Writing only the globals leaves the two copies
# in disagreement.
BLOQUE_STATS = 16
STAT_PROGRESO = 214         # int[214 + n], progress as displayed. 0 = not shown

# "Current number of girlfriends" on the statistics screen.
#
# MUST NOT BE RECALCULATED. It was believed to be the number of mask bits because
# it matched in 7 samples, and --recuperar rewrote it with that count. That is false:
# it is its own counter that the game increments on its own when obtaining a
# girlfriend. After we wrote it AND the game incremented it again on the next date,
# the count shot up to 7 -- impossible, there are only six girlfriends. That 7 was
# caused by us.
#
# Now it is only touched with --arreglar-contador, and the real bit count is set.
STAT_CUANTAS = 146

# "Girls you have broken up with". It is NOT "how many you have killed": that was
# inferred from seeing it equal 1 in the three saves where a girlfriend had been
# killed, and the player was told the 100% save owner had killed four. The stats
# screen transcription disproved it: they are breakups.
STAT_RUPTURAS = 151

MUERTA = -999
NUNCA = -100

# name -> (progress offset, bit in mask, label, "alive" progress)
#
# There are SIX girlfriends, bits 0 to 5. Slot 6 (global 1465) is NOT a girlfriend:
# in the PC 100% save, with all six obtained and the mask at 0x3f, slot 6 remains
# at -100 with the bit off.
#
# The order matches the canonical game order: Denise, Michelle, Helena, Barbara,
# Katie, Millie. All six are verified IN-GAME, not inferred: the slot was written
# and it was confirmed the girlfriend appeared where she lives.
NOVIAS = {
    "denise":   (1441, 0, "Denise Robinson", 74),
    "michelle": (1445, 1, "Michelle Cannes", 25),
    "helena":   (1449, 2, "Helena Wankstein", 10),
    "barbara":  (1453, 3, "Barbara Schternvart", 15),
    "katie":    (1457, 4, "Katie Zhan", 15),
    "millie":   (1461, 5, "Millie Perkins", 15),
}
SIN_CONFIRMAR = set()
NO_ES_NOVIA = 1465
RANURAS = 7


def base(data):
    return find_blocks(data)[BLOQUE_SCRIPTS]


def base_stats(data):
    return find_blocks(data)[BLOQUE_STATS] + 5


def stat(data, idx):
    return struct.unpack_from("<i", data, base_stats(data) + idx * 4)[0]


def poner_stat(buf, idx, valor):
    struct.pack_into("<i", buf, base_stats(buf) + idx * 4, valor)


def progreso(data, off):
    return struct.unpack_from("<i", data, base(data) + off)[0]


def mascara(data):
    return data[base(data) + MASCARA_OFF]


def estado(v):
    # NOTE: -999 does NOT mean "dead". It was observed that Millie was already at
    # -999 in the player's save BEFORE doing Key to Her Heart, without ever having
    # met her. It is a "not available" sentinel that works equally for story-blocked
    # or killed. Calling it MUERTA was a hasty reading: it was inferred from seeing
    # Katie go from 15 to -999 after killing her, which is only one of two cases.
    return {MUERTA: "blocked or dead",
            NUNCA: "never obtained",
            0: "unknown"}.get(v, "alive")


def por_offset(off):
    return next((d for d in NOVIAS.values() if d[0] == off), None)


def inspeccionar(path):
    data = Path(path).read_bytes()
    for w in platform_warnings(data):
        print(f"  warning: {w}", file=sys.stderr)
    m = mascara(data)
    print(f"=== {path} ===")
    print(f"  checksum: {'OK' if calc_checksum(data) == stored_checksum(data) else 'INVALID'}")
    print(f"  mask (global {MASCARA_OFF}): 0x{m:02x} = {m:05b}")
    print()
    print("  global  girlfriend                you have it  global  stats  status")
    descuadre = []
    for n in range(RANURAS):
        off = PROGRESO_BASE + n * 4
        conf = por_offset(off)
        if off == NO_ES_NOVIA:
            print(f"  {off:<7} {'(not a girlfriend)':<24}     ?      "
                  f"{progreso(data, off):>6}      -")
            continue
        clave = next(k for k, d in NOVIAS.items() if d[0] == off)
        nombre = conf[2] + (" *" if clave in SIN_CONFIRMAR else "")
        tiene = "yes" if (m >> conf[1]) & 1 else "--"
        v = progreso(data, off)
        s = stat(data, STAT_PROGRESO + n)
        aviso = ""
        if (v > 0) != (s > 0) or (v > 0 and v != s):
            aviso = "  <-- the two copies do not match"
            descuadre.append(nombre)
        print(f"  {off:<7} {nombre:<24}    {tiene:<7} {v:>6} {s:>6}  {estado(v)}{aviso}")

    bits = bin(m).count("1")
    c, rup = stat(data, STAT_CUANTAS), stat(data, STAT_RUPTURAS)
    print(f"\n  how many you have (stats int[{STAT_CUANTAS}]): {c}   "
          f"bits in mask: {bits}{'' if c == bits else '   <-- does not add up'}")
    print(f"  breakups (stats int[{STAT_RUPTURAS}]): {rup}")
    if any(k in SIN_CONFIRMAR for k in NOVIAS):
        print("\n  * by elimination, no observed transition")
    if descuadre:
        print(f"  the global and the stats block disagree on: {', '.join(descuadre)}")


def recuperar(path, quien, valor, salida, forzar):
    if quien not in NOVIAS:
        sys.exit(f"error: unknown '{quien}'. Confirmed: {', '.join(NOVIAS)}")
    destino = Path(salida)
    if destino.exists() and not forzar:
        sys.exit(f"error: {destino} already exists (use --forzar)")

    data = Path(path).read_bytes()
    fallos = platform_warnings(data)
    if calc_checksum(data) != stored_checksum(data):
        fallos.append("invalid checksum")
    if fallos:
        for f in fallos:
            print(f"  - {f}", file=sys.stderr)
        sys.exit(1)

    off, bit, nombre, viva = NOVIAS[quien]
    if valor is None:
        valor = viva

    buf = bytearray(data)
    b = base(data)
    hechos = []

    antes_m = buf[b + MASCARA_OFF]
    if not (antes_m >> bit) & 1:
        buf[b + MASCARA_OFF] = antes_m | (1 << bit)
        hechos.append(f"  mask: 0x{antes_m:02x} ({antes_m:05b})  ->  "
                      f"0x{buf[b + MASCARA_OFF]:02x} ({buf[b + MASCARA_OFF]:05b})   "
                      f"[bit {bit} = {nombre}]")

    antes_p = struct.unpack_from("<i", buf, b + off)[0]
    if antes_p in (MUERTA, NUNCA) or antes_p <= 0:
        struct.pack_into("<i", buf, b + off, valor)
        hechos.append(f"  progress: global {off}   {antes_p} ({estado(antes_p)})  ->  {valor}")

    # The stats block copy, which is the one that paints the screen. Without this
    # the two copies remain in disagreement and the girlfriend does not appear
    # in the list.
    antes_s = stat(buf, STAT_PROGRESO + bit)
    if antes_s != valor:
        poner_stat(buf, STAT_PROGRESO + bit, valor)
        hechos.append(f"  progress: stats int[{STAT_PROGRESO + bit}]   {antes_s}  ->  {valor}")

    # int[146] is NOT touched: the game manages it. See the STAT_CUANTAS comment.
    bits = bin(buf[b + MASCARA_OFF]).count("1")
    if stat(buf, STAT_CUANTAS) != bits:
        hechos.append(f"  warning: int[{STAT_CUANTAS}] says {stat(buf, STAT_CUANTAS)} "
                      f"but the mask has {bits} bits. Use --arreglar-contador")

    if not hechos:
        print(f"  {nombre} is already fine (mask and progress correct). Nothing changed.")
        return

    struct.pack_into("<I", buf, len(buf) - 4, calc_checksum(buf))
    assert len(buf) == len(data)

    destino.write_bytes(buf)
    check = destino.read_bytes()
    assert not platform_warnings(check)
    assert calc_checksum(check) == stored_checksum(check)
    find_blocks(check)

    for h in hechos:
        print(h)
    cambiados = sum(1 for i in range(len(data)) if data[i] != check[i])
    print(f"\n  {cambiados} bytes changed")
    print(f"  wrote {destino}: {len(check)} bytes, checksum OK, 29 blocks OK")


def arreglar_contador(path, salida, forzar):
    """Sets int[146] to the real number of girlfriends from the mask.

    Needed because a previous version of --recuperar rewrote it on every
    execution, and additionally the game increments it on its own: after
    restoring girlfriends by hand and then going on dates, the count was
    added twice and ended at 7, which is impossible -- there are only six
    girlfriends.
    """
    destino = Path(salida)
    if destino.exists() and not forzar:
        sys.exit(f"error: {destino} already exists (use --forzar)")

    data = Path(path).read_bytes()
    if calc_checksum(data) != stored_checksum(data):
        sys.exit("error: source has invalid checksum")

    buf = bytearray(data)
    bits = bin(buf[base(data) + MASCARA_OFF]).count("1")
    antes = stat(buf, STAT_CUANTAS)
    if antes == bits:
        print(f"  int[{STAT_CUANTAS}] already equals {bits}. Nothing changed.")
        return
    poner_stat(buf, STAT_CUANTAS, bits)

    struct.pack_into("<I", buf, len(buf) - 4, calc_checksum(buf))
    destino.write_bytes(buf)
    check = destino.read_bytes()
    assert calc_checksum(check) == stored_checksum(check) and not platform_warnings(check)
    find_blocks(check)

    print(f"  girlfriend count: int[{STAT_CUANTAS}]   {antes}  ->  {bits}")
    cambiados = sum(1 for i in range(len(data)) if data[i] != check[i])
    print(f"\n  {cambiados} bytes changed · wrote {destino}, checksum OK")


def progreso_de(path, quien, valor, salida, forzar):
    """Sets the progress of a girlfriend you ALREADY HAVE, in both copies.

    --recuperar does not work for this: it only writes if the slot is at a
    sentinel (-999 / -100 / 0), because its job is to rescue lost girlfriends,
    not to rescore those that are fine. Here it always writes.

    Both copies are touched -- the global and stats int[214+n] -- because the
    screen reads the stats copy. Writing only one leaves them in disagreement,
    which was the days-long deadlock.
    int[146] is NOT touched: the game manages it.
    """
    objetivo = "todas" if quien == "todas" else quien.lower()
    if objetivo != "todas" and objetivo not in NOVIAS:
        sys.exit(f"error: unknown '{quien}'. Valid: {', '.join(NOVIAS)}, todas")
    if not 0 <= valor <= 100:
        sys.exit("error: progress is a percentage, between 0 and 100")

    destino = Path(salida)
    if destino.exists() and not forzar:
        sys.exit(f"error: {destino} already exists (use --forzar)")

    data = Path(path).read_bytes()
    if calc_checksum(data) != stored_checksum(data):
        sys.exit("error: source has invalid checksum")

    buf = bytearray(data)
    b = base(data)
    m = buf[b + MASCARA_OFF]
    hechos, avisos = [], []
    for clave, (off, bit, nombre, _) in NOVIAS.items():
        if objetivo not in ("todas", clave):
            continue
        if not (m >> bit) & 1:
            avisos.append(f"  {nombre}: you do not have her (bit {bit} off). "
                          f"Use --recuperar {clave} first.")
            continue
        antes_g = struct.unpack_from("<i", buf, b + off)[0]
        antes_s = stat(buf, STAT_PROGRESO + bit)
        if antes_g == valor and antes_s == valor:
            continue
        struct.pack_into("<i", buf, b + off, valor)
        poner_stat(buf, STAT_PROGRESO + bit, valor)
        hechos.append((nombre, antes_g, antes_s, valor))

    for a in avisos:
        print(a, file=sys.stderr)
    if not hechos:
        print("  nothing to change.")
        return

    struct.pack_into("<I", buf, len(buf) - 4, calc_checksum(buf))
    destino.write_bytes(buf)
    check = destino.read_bytes()
    assert calc_checksum(check) == stored_checksum(check) and not platform_warnings(check)
    find_blocks(check)

    for nombre, ag, as_, v in hechos:
        print(f"  {nombre:<22} global {ag:>4} -> {v:<4}   stats {as_:>4} -> {v}")
    cambiados = sum(1 for i in range(len(data)) if data[i] != check[i])
    print(f"\n  {len(hechos)} girlfriend(s) · {cambiados} bytes changed · wrote {destino}")


def probar_ranura(path, n, valor, salida, forzar):
    """FINE DIAGNOSTIC save: turns on ONE slot and leaves the rest as-is.

    --mapear turns on all seven at once, and that has been proven not to work
    for identification: upon loading, permanent date icons appeared on the map
    (cafes, restaurants, bars), which normally only appear during a date. With
    four bits and two progress values moved at once, there is no way to know
    which caused it.

    Additionally there are SEVEN slots for SIX girlfriends (Denise, Michelle,
    Helena, Katie, Barbara, Millie): one extra, and the most likely explanation
    is that it is not a girlfriend but date state. One slot per save is the only
    way to find out.

    What to note when loading each one:
      - where the heart appears (Prickle Pine = Millie, El Quebrados = Barbara)
      - whether date icons appear on the map or not
      - which name appears in the statistics list AFTER going on a date
    """
    if not 0 <= n < RANURAS:
        sys.exit(f"error: slot must be between 0 and {RANURAS - 1}")
    destino = Path(salida)
    if destino.exists() and not forzar:
        sys.exit(f"error: {destino} already exists (use --forzar)")

    data = Path(path).read_bytes()
    if platform_warnings(data) or calc_checksum(data) != stored_checksum(data):
        sys.exit("error: source is not a valid mobile save")

    buf = bytearray(data)
    b = base(data)
    off = PROGRESO_BASE + n * 4
    conf = por_offset(off)
    nombre = conf[2] if conf else "(unconfirmed)"
    hechos = []

    antes_m = buf[b + MASCARA_OFF]
    if not (antes_m >> n) & 1:
        buf[b + MASCARA_OFF] = antes_m | (1 << n)
        hechos.append(f"  mask: 0x{antes_m:02x} ({antes_m:07b})  ->  "
                      f"0x{buf[b + MASCARA_OFF]:02x} ({buf[b + MASCARA_OFF]:07b})")

    antes_p = struct.unpack_from("<i", buf, b + off)[0]
    if antes_p <= 0:
        struct.pack_into("<i", buf, b + off, valor)
        hechos.append(f"  progress {off}: {antes_p} ({estado(antes_p)})  ->  {valor}")

    if not hechos:
        print(f"  slot {n} ({nombre}) was already on. Nothing changed.")
        return

    struct.pack_into("<I", buf, len(buf) - 4, calc_checksum(buf))
    destino.write_bytes(buf)
    check = destino.read_bytes()
    assert calc_checksum(check) == stored_checksum(check) and not platform_warnings(check)
    find_blocks(check)

    print(f"  slot {n}  ->  global {off}  ({nombre})")
    for h in hechos:
        print(h)
    cambiados = sum(1 for i in range(len(data)) if data[i] != check[i])
    print(f"\n  {cambiados} bytes changed · wrote {destino}, checksum OK")


def mapear(path, salida, forzar):
    """COARSE DIAGNOSTIC save: turns on all seven bits at once.

    DOES NOT WORK FOR IDENTIFICATION, and has been proven in-game: the statistics
    list only shows girlfriends already DATED, not those available, so turning on
    bits does not make any new names appear. It also moves four bits and two
    progress values at once, so any observed effect (the date icons that appeared
    on the map) remains unattributed.

    Use --probar-ranura N instead. This is kept only as a reference.
    """
    destino = Path(salida)
    if destino.exists() and not forzar:
        sys.exit(f"error: {destino} already exists (use --forzar)")

    data = Path(path).read_bytes()
    if platform_warnings(data) or calc_checksum(data) != stored_checksum(data):
        sys.exit("error: source is not a valid mobile save")

    buf = bytearray(data)
    b = base(data)
    antes_m = buf[b + MASCARA_OFF]
    buf[b + MASCARA_OFF] = antes_m | 0b1111111
    print(f"  mask: 0x{antes_m:02x} ({antes_m:07b})  ->  0x{buf[b + MASCARA_OFF]:02x} "
          f"({buf[b + MASCARA_OFF]:07b})")

    for n in range(RANURAS):
        off = PROGRESO_BASE + n * 4
        v = struct.unpack_from("<i", buf, b + off)[0]
        if v <= 0:
            struct.pack_into("<i", buf, b + off, 50)
            conf = por_offset(off)
            print(f"  progress {off} ({conf[2] if conf else 'unconfirmed'}): "
                  f"{v} ({estado(v)})  ->  50")

    struct.pack_into("<I", buf, len(buf) - 4, calc_checksum(buf))
    destino.write_bytes(buf)
    check = destino.read_bytes()
    assert calc_checksum(check) == stored_checksum(check) and not platform_warnings(check)
    find_blocks(check)
    print(f"\n  wrote {destino}: {len(check)} bytes, checksum OK")
    print("  DIAGNOSTIC: load, check the girlfriend list and note which names appear")
    print("  in slots 1453, 1461 and 1465. Do not use it as a definitive save.")


def deshacer_mapeo(path, referencia, salida, forzar):
    """Reverts a --mapear save using another as reference.

    Keeps progress earned by playing (a date raises the percentage) and only
    reverts what the diagnostic put: the mask, and the slots that had sentinels
    in the reference (-999 dead / -100 never obtained).
    """
    destino = Path(salida)
    if destino.exists() and not forzar:
        sys.exit(f"error: {destino} already exists (use --forzar)")

    data = Path(path).read_bytes()
    ref = Path(referencia).read_bytes()
    for x, n in ((data, path), (ref, referencia)):
        if platform_warnings(x) or calc_checksum(x) != stored_checksum(x):
            sys.exit(f"error: {n} is not a valid mobile save")

    buf = bytearray(data)
    b, rb = base(data), base(ref)
    hechos = []

    m_ahora, m_ref = buf[b + MASCARA_OFF], ref[rb + MASCARA_OFF]
    if m_ahora != m_ref:
        buf[b + MASCARA_OFF] = m_ref
        hechos.append(f"  mask: 0x{m_ahora:02x} ({m_ahora:07b})  ->  "
                      f"0x{m_ref:02x} ({m_ref:07b})")

    for n in range(RANURAS):
        off = PROGRESO_BASE + n * 4
        v_ahora = struct.unpack_from("<i", buf, b + off)[0]
        v_ref = struct.unpack_from("<i", ref, rb + off)[0]
        # Only revert what the reference had as sentinel. Progress earned by
        # playing is NOT reverted.
        if v_ref in (MUERTA, NUNCA) and v_ahora != v_ref:
            struct.pack_into("<i", buf, b + off, v_ref)
            conf = por_offset(off)
            hechos.append(f"  progress {off} ({conf[2] if conf else 'unconfirmed'}): "
                          f"{v_ahora}  ->  {v_ref} ({estado(v_ref)})")
        elif v_ahora != v_ref:
            conf = por_offset(off)
            hechos.append(f"  progress {off} ({conf[2] if conf else 'unconfirmed'}): "
                          f"{v_ref} -> {v_ahora}, KEPT (earned by playing)")

    if not any("->" in h and "KEPT" not in h for h in hechos):
        print("  nothing to revert.")
        return

    struct.pack_into("<I", buf, len(buf) - 4, calc_checksum(buf))
    destino.write_bytes(buf)
    check = destino.read_bytes()
    assert calc_checksum(check) == stored_checksum(check) and not platform_warnings(check)
    find_blocks(check)

    for h in hechos:
        print(h)
    cambiados = sum(1 for i in range(len(data)) if data[i] != check[i])
    print(f"\n  {cambiados} bytes changed")
    print(f"  wrote {destino}: {len(check)} bytes, checksum OK, 29 blocks OK")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("save")
    ap.add_argument("--inspeccionar", action="store_true")
    ap.add_argument("--recuperar", metavar="NOMBRE")
    ap.add_argument("--deshacer-mapeo", metavar="REFERENCIA", dest="deshacer",
                    help="revert a --mapear save using another save as reference")
    ap.add_argument("--progreso", nargs=2, metavar=("NOMBRE", "PERCENTAGE"),
                    help="set the progress of a girlfriend you already have (or 'todas')")
    ap.add_argument("--arreglar-contador", action="store_true",
                    help="set int[146] to the real girlfriend count from the mask")
    ap.add_argument("--probar-ranura", metavar="N", dest="ranura", type=int,
                    help="fine diagnostic: turn ON ONLY slot N (0-6) and leave the"
                         " rest unchanged. This is how to identify which girlfriend is which")
    ap.add_argument("--mapear", action="store_true",
                    help="[deprecated] turn on all seven bits at once. Does not identify"
                         " anything and mixes effects; use --probar-ranura")
    ap.add_argument("--valor", type=int, default=None,
                    help="progress to write (default: the confirmed value for that girlfriend)")
    ap.add_argument("--salida")
    ap.add_argument("--forzar", action="store_true")
    args = ap.parse_args()

    if args.progreso:
        if not args.salida:
            ap.error("--progreso requires --salida")
        try:
            v = int(args.progreso[1])
        except ValueError:
            ap.error("the percentage must be an integer")
        progreso_de(args.save, args.progreso[0], v, args.salida, args.forzar)
    elif args.arreglar_contador:
        if not args.salida:
            ap.error("--arreglar-contador requires --salida")
        arreglar_contador(args.save, args.salida, args.forzar)
    elif args.deshacer:
        if not args.salida:
            ap.error("--deshacer-mapeo requires --salida")
        deshacer_mapeo(args.save, args.deshacer, args.salida, args.forzar)
    elif args.ranura is not None:
        if not args.salida:
            ap.error("--probar-ranura requires --salida")
        probar_ranura(args.save, args.ranura, args.valor or 45, args.salida, args.forzar)
    elif args.mapear:
        if not args.salida:
            ap.error("--mapear requires --salida")
        mapear(args.save, args.salida, args.forzar)
    elif args.recuperar:
        if not args.salida:
            ap.error("--recuperar requires --salida")
        recuperar(args.save, args.recuperar.lower(), args.valor, args.salida, args.forzar)
    else:
        inspeccionar(args.save)


if __name__ == "__main__":
    main()
