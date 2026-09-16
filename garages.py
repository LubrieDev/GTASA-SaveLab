#!/usr/bin/env python3
"""
Shortcut. The code lives in gtasa/garajes.py -- general tool for the 20 garages.

    python garages.py ver PARTIDA.b
    python garages.py anadir PARTIDA.b --salida NUEVA.b --garaje 19 --plaza 0 --modelo 596
    python garages.py quitar PARTIDA.b --salida NUEVA.b --garaje 19 --plaza 0
    python garages.py limpiar PARTIDA.b --salida NUEVA.b
    python garages.py coches
"""
import runpy
import sys

sys.exit(runpy.run_module("gtasa.garages", run_name="__main__") and 0)
