#!/usr/bin/env python3
"""
All-in-one tool for GTA San Andreas Mobile saves.

    python gta.py audit savefiles/base.b
    python gta.py edit  savefiles/base.b --output NEW.b --money 999999999 --ammo 99999

Combines what used to be five separate scripts (gtasa_editor, armas, novias,
garaje, partida100), which shared half the code and did not even use the same
language in their options. The reverse engineering behind each field is documented
in PROJECT-MEMORY.md and in the corresponding module; this is only orchestration.

TWO RULES
---------
1. `audit` never writes. `edit` requires --output and never touches the original.
2. All changes are applied in ONE pass over the same buffer, and the checksum is
   recalculated only once at the end. Chaining scripts forced intermediate files
   and re-reading and re-validating at each step.
"""

import argparse
import math
import struct
import sys
from pathlib import Path

from .editor import (
    FLOAT_STATS, INT_STATS, MAXABLE, OFF_MONEY, OFF_DISPLAY_MONEY, OFF_RANURA,
    PLAYERINFO_BLOCK, STATS_BLOCK,
    calc_checksum, stored_checksum, find_blocks, platform_warnings,
)
from . import weapons as A
from . import girlfriends as N
from . import garage as G
from . import armor as B
from . import wardrobe as R
from . import vehicles as V
from . import globals as GL      # `as GL` on purpose: `import globals` would shadow the builtin


class Partida:
    """A save loaded into memory. All writes go to the same buffer."""

    def __init__(self, path):
        self.path = Path(path)
        self.original = self.path.read_bytes()
        self.buf = bytearray(self.original)
        self.avisos = platform_warnings(self.original)
        self.checksum_ok = calc_checksum(self.original) == stored_checksum(self.original)
        self.bloques = find_blocks(self.original)
        self.cambios = []

    # --- locators -------------------------------------------------
    @property
    def scripts(self):
        return self.bloques[N.BLOQUE_SCRIPTS]

    @property
    def simplevars(self):
        return self.bloques[0] + 5

    @property
    def ranura(self):
        """Which slot in the save list this file belongs to."""
        return self.i32(self.simplevars + OFF_RANURA)

    @property
    def mision(self):
        """The label shown in the save list: the last mission completed.
        UTF-16 zero-terminated, from SimpleVars+4; at +44 the slot starts."""
        crudo = bytes(self.buf[self.simplevars + 4:self.simplevars + OFF_RANURA])
        return crudo.decode("utf-16-le", "replace").split("\x00")[0]

    def resumen(self):
        return (f"{self.mision}, ${self.i32(self.jugador + OFF_MONEY):,}, "
                f"{self.stat_f(0) / self.stat_f(1) * 100:.0f}%, slot {self.ranura}")

    @property
    def stats(self):
        return self.bloques[STATS_BLOCK] + 5

    @property
    def jugador(self):
        return self.bloques[PLAYERINFO_BLOCK]

    @property
    def tabla_armas(self):
        return A.localizar_tabla(self.buf)

    # --- primitive read/write -------------------------------------
    def i32(self, off):
        return struct.unpack_from("<i", self.buf, off)[0]

    def f32(self, off):
        return struct.unpack_from("<f", self.buf, off)[0]

    def pon_i32(self, off, v):
        struct.pack_into("<i", self.buf, off, v)

    def pon_f32(self, off, v):
        struct.pack_into("<f", self.buf, off, float(v))

    def stat_i(self, idx):
        return self.i32(self.stats + idx * 4)

    def stat_f(self, idx):
        return self.f32(self.stats + idx * 4)

    def anota(self, que, antes, ahora, hubo_cambio=None):
        """Records a change. `hubo_cambio` is for comparing actual values when
        what is passed are already-formatted strings: without it, a stat that
        already had 1000 was listed as a change because "1000.00" != "1000"."""
        if hubo_cambio if hubo_cambio is not None else antes != ahora:
            self.cambios.append((que, antes, ahora))

    # --- save -----------------------------------------------------
    def guardar(self, salida, forzar):
        destino = Path(salida)
        if destino.exists() and not forzar:
            sys.exit(f"error: {destino} already exists (use --force)")
        if not self.cambios:
            print("  nothing to change; nothing written.")
            return None

        struct.pack_into("<I", self.buf, len(self.buf) - 4, calc_checksum(self.buf))
        assert len(self.buf) == len(self.original), "the size must not change"
        destino.write_bytes(self.buf)

        # Re-read from disk and re-validate as if it were an external file.
        check = destino.read_bytes()
        assert not platform_warnings(check), platform_warnings(check)
        assert calc_checksum(check) == stored_checksum(check), "checksum written incorrectly"
        find_blocks(check)
        A.localizar_tabla(check)

        for que, antes, ahora in self.cambios:
            print(f"  {que:<34} {antes!s:>12}  ->  {ahora}")
        n = sum(1 for i in range(len(self.original)) if self.original[i] != check[i])
        print(f"\n  {len(self.cambios)} changes · {n} bytes · wrote {destino}, checksum OK")
        return destino


# ======================================================================
#  AUDIT
# ======================================================================

def auditar(path):
    p = Partida(path)
    print(f"=== {path} ===")
    # find_blocks returns the 29 starts plus a sentinel with the end of the last one
    print(f"  {len(p.original)} bytes · {len(p.bloques) - 1} blocks · "
          f"checksum {'OK' if p.checksum_ok else 'INVALID  <-- the game will reject it'}")
    for a in p.avisos:
        print(f"  warning: {a}")

    hecho, total = p.stat_f(0), p.stat_f(1)
    print(f"\n  MONEY      ${p.i32(p.jugador + OFF_MONEY):,}"
          f"   (HUD ${p.i32(p.jugador + OFF_DISPLAY_MONEY):,})")
    print(f"  PROGRESS   {hecho:g} / {total:g} = {hecho / total * 100:.2f}%")

    uso, limite = GL.gimnasio(p.buf)
    aviso = "   <-- blocked; fixed with --arreglar-gimnasio" \
        if limite != (GL.SIN_FECHA, GL.SIN_FECHA) else ""
    print(f"  GYM        last visit {GL.fecha(uso)} · "
          f"daily limit {GL.fecha(limite)}{aviso}")

    print("\n  PLAYER STATS")
    for idx in sorted(FLOAT_STATS):
        v = p.stat_f(idx)
        # The game itself writes above 1000 (1030.30 and 1075.75 have been seen),
        # so this is NOT a broken file. But the effect caps at 1000 -- muscle at
        # 1000 and 1001 are identical in the game -- so the excess does nothing.
        # A warning is shown so nobody reads it as "I have more".
        tope = "  (above 1000; the effect does not go past 1000)" \
            if idx in MAXABLE and v > 1000 else ""
        print(f"    [{idx:2d}] {FLOAT_STATS[idx]:<24} {v:9.2f}{tope}")

    print("\n  COUNTERS (integers)")
    for idx in sorted(INT_STATS):
        print(f"    [{idx:3d}] {INT_STATS[idx]:<24} {p.stat_i(idx):>12,}")

    base = p.tabla_armas
    print(f"\n  PLAYER     health {p.f32(base + A.OFF_VIDA):.0f}"
          f"   armor {p.f32(base + A.OFF_BLINDAJE):.0f}")

    print("\n  WEAPONS")
    for n in range(A.RANURAS):
        off = base + n * A.PASO
        idw = p.i32(off + A.OFF_ID)
        if not idw:
            continue
        if idw in A.SIN_MUNICION:
            print(f"    {n:<3} {A.ARMAS[idw]:<26} (no ammo)")
        else:
            carg, tot = p.i32(off + A.OFF_CARGADOR), p.i32(off + A.OFF_TOTAL)
            print(f"    {n:<3} {A.ARMAS[idw]:<26} {tot:>7} bullets   "
                  f"(magazine {carg}, HUD will show {tot - carg}-{carg})")

    print("\n  GIRLFRIENDS")
    m = p.buf[p.scripts + N.MASCARA_OFF]
    descuadre = []
    for n in range(6):
        off = N.PROGRESO_BASE + n * 4
        nombre = next(d[2] for d in N.NOVIAS.values() if d[0] == off)
        g, s = p.i32(p.scripts + off), p.stat_i(N.STAT_PROGRESO + n)
        tuya = "yes" if (m >> n) & 1 else "--"
        alerta = ""
        if (g > 0) != (s > 0) or (g > 0 and g != s):
            alerta = "  <-- the two copies disagree"
            descuadre.append(nombre)
        print(f"    {nombre:<24} {tuya}   global {g:>5}   stats {s:>5}"
              f"   {N.estado(g)}{alerta}")
    bits, cuenta = bin(m).count("1"), p.stat_i(N.STAT_CUANTAS)
    print(f"    counter int[{N.STAT_CUANTAS}]: {cuenta}   bits in mask: {bits}"
          f"{'' if cuenta == bits else '   <-- does not match, use --arreglar-contador'}")
    print(f"    breakups int[{N.STAT_RUPTURAS}]: {p.stat_i(N.STAT_RUPTURAS)}")

    print("\n  CJ'S HOUSE GARAGE")
    for k, off in G.plazas(p.buf):
        x, y, z, marca, modelo, est = G.describir(p.buf, off)
        pos = (f"({x:7.0f},{y:8.0f},{z:6.0f})"
               if all(math.isfinite(v) for v in (x, y, z)) else "      (NaN)      ")
        aviso = "  <-- ghost slot: occupies space and cannot be cleared by playing" \
            if est == "FANTASMA" else ""
        blind = f"  proof flags {B.describir_blindaje(B.leer(p.buf, off))}" \
            if est == "ocupada" else ""
        print(f"    slot {k}  {V.etiqueta(modelo):<26} "
              f"{pos}  {est}{blind}{aviso}")

    if descuadre:
        print(f"\n  ATTENTION: girlfriends with the two copies disagreeing: {', '.join(descuadre)}")


# ======================================================================
#  EDIT
# ======================================================================

def editar(args):
    p = Partida(args.save)
    if not p.checksum_ok:
        sys.exit("error: the source has an invalid checksum; not editing")
    if p.avisos:
        for a in p.avisos:
            print(f"  - {a}", file=sys.stderr)
        sys.exit("error: the source does not look like a GTA SA Mobile save")

    if args.dinero is not None:
        for off, et in ((OFF_MONEY, "money"), (OFF_DISPLAY_MONEY, "money (HUD)")):
            antes = p.i32(p.jugador + off)
            p.pon_i32(p.jugador + off, args.dinero)
            p.anota(et, f"{antes:,}", f"{args.dinero:,}", antes != args.dinero)

    if args.stats_max:
        # 21 is fat: maxing it out would be counterproductive, it goes to 0.
        for idx in [21] + MAXABLE:
            objetivo = 0.0 if idx == 21 else 1000.0
            antes = p.stat_f(idx)
            p.pon_f32(p.stats + idx * 4, objetivo)
            p.anota(f"[{idx}] {FLOAT_STATS[idx]}", f"{antes:.2f}", f"{objetivo:.0f}",
                    abs(antes - objetivo) > 0.01)

    # This is AFTER --stats-max on purpose: that sets fat to 0, and if the user
    # asks for both, the explicit value wins. They used to be in reverse order and
    # --stats-max overwrote fat, so they were declared incompatible; it was an
    # ordering error.
    # The player stats scale is value/10 = percentage on screen:
    # the player read "Fat: 55%" with float[21] = 550.50.
    #
    # Fat and muscle are DUPLICATED: they also live at the end of the wardrobe,
    # in block 2, and that is the copy that deforms the body. That is why they go
    # through ropa.sincroniza_cuerpo() and not raw, which would leave the menu
    # showing one thing and CJ showing another. See ropa.py.
    if args.grasa is not None or args.musculatura is not None:
        pares = R.sincroniza_cuerpo(
            p.buf,
            None if args.grasa is None else args.grasa * 10.0,
            None if args.musculatura is None else args.musculatura * 10.0)
        for nombre, idx, antes, ahora in pares:
            p.anota(f"[{idx}] {FLOAT_STATS[idx]} (both copies)",
                    f"{antes:.2f} ({antes/10:.0f}%)",
                    f"{ahora:.2f} ({ahora/10:.0f}%)", abs(antes - ahora) > 0.01)

    base = p.tabla_armas
    if args.vida is not None:
        antes = p.f32(base + A.OFF_VIDA)
        p.pon_f32(base + A.OFF_VIDA, args.vida)
        p.anota("health", f"{antes:.0f}", f"{args.vida:.0f}", abs(antes - args.vida) > 0.01)
    if args.blindaje is not None:
        antes = p.f32(base + A.OFF_BLINDAJE)
        p.pon_f32(base + A.OFF_BLINDAJE, args.blindaje)
        p.anota("armor", f"{antes:.0f}", f"{args.blindaje:.0f}",
                abs(antes - args.blindaje) > 0.01)

    if args.municion is not None:
        # Writes +12 (total ammo), NOT +8 (magazine): see weapons.py.
        for n in range(A.RANURAS):
            off = base + n * A.PASO
            idw = p.i32(off + A.OFF_ID)
            if not idw or idw in A.SIN_MUNICION:
                continue
            antes = p.i32(off + A.OFF_TOTAL)
            valor = max(args.municion, p.i32(off + A.OFF_CARGADOR))
            p.pon_i32(off + A.OFF_TOTAL, valor)
            p.anota(f"ammo {A.ARMAS[idw]}", antes, valor)

    # --- give a weapon you don't have ---
    #
    # VERIFIED IN-GAME (thermal goggles in slot 11 and satchel charges in 8, at the
    # same time): writing the ID at +0 and ammo at +12 is enough, the weapon appears.
    # Nothing else needs to be touched.
    # Thrown weapons don't consume ammo with this setup: the HUD shows +12 and what
    # goes down is +8, which is left at 1. It shows infinite. It has not been checked
    # whether it survives a save-and-reload cycle.
    # ONE SLOT, ONE WEAPON: giving a weapon overwrites whatever was in its slot.
    for entrada in (args.dar or []):
        nombre, _, cant = entrada.partition(":")
        clave = nombre.strip().lower()
        if clave not in A.POR_NOMBRE:
            sys.exit(f"error: I don't know the weapon '{nombre}'.\n"
                     f"valid: {', '.join(sorted(A.POR_NOMBRE))}")
        idw = A.POR_NOMBRE[clave]
        ranura = A.RANURA_DE.get(idw)
        if ranura is None:
            sys.exit(f"error: I don't know which slot {A.ARMAS[idw]} goes in")
        cantidad = int(cant) if cant.strip() else 9999
        off = base + ranura * A.PASO
        antes_id = p.i32(off + A.OFF_ID)
        if antes_id and antes_id != idw:
            print(f"  warning: slot {ranura} had {A.ARMAS[antes_id]}; "
                  f"{A.ARMAS[idw]} replaces it", file=sys.stderr)
        p.pon_i32(off + A.OFF_ID, idw)
        p.anota(f"slot {ranura}", A.ARMAS.get(antes_id, antes_id), A.ARMAS[idw],
                antes_id != idw)
        if idw in A.SIN_MUNICION:
            p.pon_i32(off + A.OFF_CARGADOR, 0)
            p.pon_i32(off + A.OFF_TOTAL, 1)
        else:
            p.pon_i32(off + A.OFF_CARGADOR, 1)
            p.pon_i32(off + A.OFF_TOTAL, cantidad)
            p.anota(f"ammo {A.ARMAS[idw]}", 0, cantidad)

    for quien in (args.recuperar or []):
        clave = quien.lower()
        if clave not in N.NOVIAS:
            sys.exit(f"error: I don't know the girlfriend '{quien}'. "
                     f"Valid: {', '.join(N.NOVIAS)}")
        off, bit, nombre, viva = N.NOVIAS[clave]
        m = p.buf[p.scripts + N.MASCARA_OFF]
        if not (m >> bit) & 1:
            p.buf[p.scripts + N.MASCARA_OFF] = m | (1 << bit)
            p.anota(f"mask (bit {bit}, {nombre})", f"0x{m:02x}",
                    f"0x{p.buf[p.scripts + N.MASCARA_OFF]:02x}")
        if p.i32(p.scripts + off) <= 0:
            antes = p.i32(p.scripts + off)
            p.pon_i32(p.scripts + off, viva)
            p.anota(f"{nombre} (global)", antes, viva)
        if p.stat_i(N.STAT_PROGRESO + bit) <= 0:
            antes = p.stat_i(N.STAT_PROGRESO + bit)
            p.pon_i32(p.stats + (N.STAT_PROGRESO + bit) * 4, viva)
            p.anota(f"{nombre} (stats)", antes, viva)

    if args.novias is not None:
        m = p.buf[p.scripts + N.MASCARA_OFF]
        for clave, (off, bit, nombre, _) in N.NOVIAS.items():
            if not (m >> bit) & 1:
                print(f"  warning: you don't have {nombre}; use --recover {clave}",
                      file=sys.stderr)
                continue
            # BOTH copies: the global and the stats one, which is what the screen shows.
            antes_g = p.i32(p.scripts + off)
            p.pon_i32(p.scripts + off, args.novias)
            p.anota(f"{nombre} (global)", antes_g, args.novias)
            antes_s = p.stat_i(N.STAT_PROGRESO + bit)
            p.pon_i32(p.stats + (N.STAT_PROGRESO + bit) * 4, args.novias)
            p.anota(f"{nombre} (stats)", antes_s, args.novias)

    if args.arreglar_contador:
        bits = bin(p.buf[p.scripts + N.MASCARA_OFF]).count("1")
        antes = p.stat_i(N.STAT_CUANTAS)
        p.pon_i32(p.stats + N.STAT_CUANTAS * 4, bits)
        p.anota("girlfriend counter", antes, bits)

    if args.arreglar_gimnasio:
        antes = GL.arreglar_gimnasio(p.buf)
        if antes is None:
            p.anota("gym limit", "no date", "no date", False)
        else:
            p.anota("gym limit", GL.fecha(antes), "cleared", True)

    if args.limpiar_garaje:
        for k, off in G.plazas(p.buf):
            if p.buf[off:off + G.PLAZA_LEN] == G.PLAZA_LIBRE:
                continue
            antes = G.describir(p.buf, off)[5]
            p.buf[off:off + G.PLAZA_LEN] = G.PLAZA_LIBRE
            p.anota(f"garage slot {k}", antes, "FREE (clean)")

    # After --clean-garage: if both are requested, cleaning leaves slots without
    # cars and then there is nothing to proof, which is correct.
    if args.blindar or args.desblindar:
        valor = B.BLINDADO if args.blindar else B.NORMAL
        for k, off in G.plazas(p.buf):
            if G.describir(p.buf, off)[5] != "ocupada":
                continue
            antes, ahora = B.aplicar(p.buf, off, valor)
            p.anota(f"proof flags slot {k}", f"0x{antes:02x}", f"0x{ahora:02x}",
                    antes != ahora)

    p.guardar(args.salida, args.forzar)


# ======================================================================
#  CLONE
# ======================================================================

def clonar(args):
    """Leaves an exact copy of `save` ready to occupy another phone slot.

    The phone decides the slot by the FILE NAME, so copying is enough for the save
    to load. But inside, at SimpleVars+44, the file carries its own slot number,
    and a raw copy leaves it lying: save 5 put in slot 3 would still say "I am 5".
    It is rewritten and the checksum is redone.
    """
    p = Partida(args.save)
    if not p.checksum_ok:
        sys.exit("error: the source has an invalid checksum; not cloning")
    if p.avisos:
        for a in p.avisos:
            print(f"  - {a}", file=sys.stderr)
        sys.exit("error: the source does not look like a GTA SA Mobile save")

    destino = Path(args.salida) if args.salida else p.path.parent / f"GTASAsf{args.a}.b"
    if destino.resolve() == p.path.resolve():
        sys.exit("error: the destination is the source itself")

    antes = p.ranura
    p.pon_i32(p.simplevars + OFF_RANURA, args.a)
    p.anota("internal slot (SimpleVars+44)", antes, args.a, True)

    print(f"=== clone {p.path.name} -> slot {args.a} ===")
    if destino.exists():
        # It's not the file the phone has now, it's the local copy that was there.
        # It's still worth mentioning the overwrite: it may be the only one left.
        try:
            print(f"  overwriting {destino.name}, which is now: "
                  f"{Partida(destino).resumen()}")
        except Exception:
            print(f"  overwriting {destino.name}")
        if not args.forzar:
            sys.exit("error: the destination already exists (use --force)")

    print(f"  the copy carries: {p.resumen()}")
    if p.guardar(destino, forzar=True):
        print(f"\n  Upload it to the phone as {destino.name}. Slot {args.a} becomes\n"
              f"  identical to {antes}: same money, same weapons, same position.\n"
              f"  In the save list both will show the same mission name.")


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="orden", required=True)

    a = sub.add_parser("audit", aliases=["auditar"], help="full report; writes nothing")
    a.add_argument("save")

    e = sub.add_parser("edit", aliases=["editar"], help="applies changes and writes a new file")
    e.add_argument("save")
    e.add_argument("--output", "--salida", dest="salida", metavar="OUTPUT", required=True)
    e.add_argument("--force", "--forzar", dest="forzar", action="store_true")
    e.add_argument("--money", "--dinero", dest="dinero", metavar="MONEY", type=int)
    e.add_argument("--fat", "--grasa", dest="grasa", type=float, metavar="PERCENT",
                   help="fat as %% shown by the game (0-100)")
    e.add_argument("--muscle", "--musculatura", dest="musculatura", type=float, metavar="PERCENT",
                   help="muscle as %% (0-100); writes both copies")
    e.add_argument("--stats-max", action="store_true",
                   help="max out player stats (and set fat to 0)")
    e.add_argument("--health", "--vida", dest="vida", metavar="HEALTH", type=float)
    e.add_argument("--armor", "--blindaje", dest="blindaje", metavar="ARMOR", type=float)
    e.add_argument("--ammo", "--municion", dest="municion", type=int, metavar="N",
                   help="total ammo for all weapons you carry")
    e.add_argument("--girlfriends", "--novias", dest="novias", type=int, metavar="PERCENT",
                   help="progress for all girlfriends you already have (0-100)")
    e.add_argument("--give", "--dar", dest="dar", action="append", metavar="WEAPON[:N]",
                    help="give a weapon you don't have, e.g. --give 'thermal goggles' or "
                        "--give satchel charges:50. Note: overwrites the weapon in that slot")
    e.add_argument("--recover", "--recuperar", dest="recuperar", action="append", metavar="NAME",
                   help="recover a lost girlfriend; can be repeated")
    e.add_argument("--fix-counter", "--arreglar-contador", dest="arreglar_contador", action="store_true")
    e.add_argument("--fix-gym", "--arreglar-gimnasio", dest="arreglar_gimnasio", action="store_true",
                   help="clears the gym daily limit date, which makes the "
                        "game answer 'you have done enough exercise for today'")
    e.add_argument("--clean-garage", "--limpiar-garaje", dest="limpiar_garaje", action="store_true")
    e.add_argument("--proof", "--blindar", dest="blindar", action="store_true",
                   help="makes saved garage cars proof flags 0x1f (all-proof)")
    e.add_argument("--unproof", "--desblindar", dest="desblindar", action="store_true",
                   help="removes their proof flags (0x00)")

    c = sub.add_parser("clone", aliases=["clonar"],
                       help="copies a save to another slot, ready to upload")
    c.add_argument("save")
    c.add_argument("--slot", "--a", dest="a", type=int, required=True, metavar="SLOT",
                   help="destination slot (1-10); the file will be named GTASAsfN.b")
    c.add_argument("--output", "--salida", dest="salida", help="default: GTASAsfN.b next to the source")
    c.add_argument("--force", "--forzar", dest="forzar", action="store_true")

    args = ap.parse_args()
    if args.orden in ("audit", "auditar"):
        auditar(args.save)
    elif args.orden in ("clone", "clonar"):
        if not 1 <= args.a <= 10:
            ap.error("--slot is a phone slot, between 1 and 10")
        clonar(args)
    else:
        if args.dinero is not None and not 0 <= args.dinero <= 2_147_483_647:
            ap.error("--money must fit in a signed int32")
        if args.grasa is not None and not 0 <= args.grasa <= 100:
            ap.error("--fat is a percentage, between 0 and 100")
        if args.musculatura is not None and not 0 <= args.musculatura <= 100:
            ap.error("--muscle is a percentage, between 0 and 100")
        if args.novias is not None and not 0 <= args.novias <= 100:
            ap.error("--girlfriends is a percentage, between 0 and 100")
        if args.municion is not None and not 0 <= args.municion <= 2_147_483_647:
            ap.error("--ammo must fit in a signed int32")
        editar(args)


if __name__ == "__main__":
    main()
