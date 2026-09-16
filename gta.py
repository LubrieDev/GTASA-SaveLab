#!/usr/bin/env python3
"""
Shortcut. The code lives in gtasa.cli.py -- the main tool: audit and edit saves.

    python gta.py ...      is the same as      python -m gtasa.cli ...

Exists so existing commands keep working after moving code into the
`gtasa` package. Do not add logic here.
"""
import runpy
import sys

# Keep command output stable when the tool is launched from Windows terminals.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

# Without `alter_sys`: sys.argv[0] stays as this file so argparse
# prints "usage: weapons.py ..." instead of "usage: python -m gtasa.weapons ...".
sys.exit(runpy.run_module("gtasa.cli", run_name="__main__") and 0)
