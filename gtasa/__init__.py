"""
Tools for GTA San Andreas Mobile save files.

The entry point is `gtasa.cli` (or `gta.py` in the root). `gtasa.savefile` is
the file layer that everything else should rely on: it locates the 29 blocks,
reads them, writes them, and closes the checksum.

    from gtasa.savefile import Save
    sf = Save.abrir("partidas/buena/GTASAsf1.b")
    print(sf.version, sf.checksum_ok(), sf[15].inicio)
"""
