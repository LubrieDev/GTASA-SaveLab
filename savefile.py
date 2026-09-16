#!/usr/bin/env python3
"""
Shortcut. The code lives in gtasa.savefile.py -- file layer: blocks and checksum.

    python savefile.py ...      is the same as      python -m gtasa.savefile ...

Exists so existing commands keep working after moving code into the
`gtasa` package. Do not add logic here.
"""
import runpy
import sys

# Without `alter_sys`: sys.argv[0] stays as this file so argparse
# prints "usage: weapons.py ..." instead of "usage: python -m gtasa.weapons ...".
sys.exit(runpy.run_module("gtasa.savefile", run_name="__main__") and 0)
