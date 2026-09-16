#!/usr/bin/env python3
"""
Shortcut. The code lives in gtasa.garage.py -- garage slots.

    python garage.py ...      is the same as      python -m gtasa.garage ...

Exists so existing commands keep working after moving code into the
`gtasa` package. Do not add logic here.
"""
import runpy
import sys

# Without `alter_sys`: sys.argv[0] stays as this file so argparse
# prints "usage: weapons.py ..." instead of "usage: python -m gtasa.weapons ...".
sys.exit(runpy.run_module("gtasa.garage", run_name="__main__") and 0)
