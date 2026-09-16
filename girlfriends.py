#!/usr/bin/env python3
"""
Shortcut. The code lives in gtasa.girlfriends.py -- girlfriends.

    python girlfriends.py ...      is the same as      python -m gtasa.girlfriends ...

Exists so existing commands keep working after moving code into the
`gtasa` package. Do not add logic here.
"""
import runpy
import sys

# Without `alter_sys`: sys.argv[0] stays as this file so argparse
# prints "usage: weapons.py ..." instead of "usage: python -m gtasa.weapons ...".
sys.exit(runpy.run_module("gtasa.girlfriends", run_name="__main__") and 0)
