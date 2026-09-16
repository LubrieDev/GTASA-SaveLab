#!/usr/bin/env python3
"""
The names of the 212 vehicle models, from 400 to 611.

    from vehicles import etiqueta
    etiqueta(470)   ->  'model 470 (Patriot)'
    etiqueta(0)     ->  '(free)'
    etiqueta(999)   ->  'model 999'

WHERE THIS COMES FROM AND WHY IT IS RELIABLE
--------------------------------------------
It is the San Andreas ID table, which is public and does not change between versions.
Nothing has been measured here, so the only thing that supports it is the contrast
with the cars the project had already identified on its own, and all six match:

    412 Voodoo     the one with bit 6 of proof flags  (blindaje.py, PROJECT-MEMORY.md)
    415 Cheetah    the one from the foreign 100% save
    463 Freeway    the one from the player's old saves
    470 Patriot    the one from the ARMORED / UNARMORED pair, confirmed in-game
    522 NRG-500    field truth at Grove Street  (garage.py)
    571 Kart       field truth at Grove Street  (garage.py)

If a name ever does not match what is seen on the phone, this file is the first
thing to doubt: it is the only one in the project that does not come from a save.
"""

NOMBRES = {
    400: "Landstalker", 401: "Bravura", 402: "Buffalo", 403: "Linerunner",
    404: "Perennial", 405: "Sentinel", 406: "Dumper", 407: "Fire Truck",
    408: "Trashmaster", 409: "Stretch", 410: "Manana", 411: "Infernus",
    412: "Voodoo", 413: "Pony", 414: "Mule", 415: "Cheetah",
    416: "Ambulance", 417: "Leviathan", 418: "Moonbeam", 419: "Esperanto",
    420: "Taxi", 421: "Washington", 422: "Bobcat", 423: "Mr. Whoopee",
    424: "BF Injection", 425: "Hunter", 426: "Premier", 427: "Enforcer",
    428: "Securicar", 429: "Banshee", 430: "Predator", 431: "Bus",
    432: "Rhino", 433: "Barracks", 434: "Hotknife", 435: "Trailer 1",
    436: "Previon", 437: "Coach", 438: "Cabbie", 439: "Stallion",
    440: "Rumpo", 441: "RC Bandit", 442: "Romero", 443: "Packer",
    444: "Monster", 445: "Admiral", 446: "Squalo", 447: "Seasparrow",
    448: "Pizzaboy", 449: "Tram", 450: "Trailer 2", 451: "Turismo",
    452: "Speeder", 453: "Reefer", 454: "Tropic", 455: "Flatbed",
    456: "Yankee", 457: "Caddy", 458: "Solair", 459: "Berkley's RC Van",
    460: "Skimmer", 461: "PCJ-600", 462: "Faggio", 463: "Freeway",
    464: "RC Baron", 465: "RC Raider", 466: "Glendale", 467: "Oceanic",
    468: "Sanchez", 469: "Sparrow", 470: "Patriot", 471: "Quadbike",
    472: "Coastguard", 473: "Dinghy", 474: "Hermes", 475: "Sabre",
    476: "Rustler", 477: "ZR-350", 478: "Walton", 479: "Regina",
    480: "Comet", 481: "BMX", 482: "Burrito", 483: "Camper",
    484: "Marquis", 485: "Baggage", 486: "Dozer", 487: "Maverick",
    488: "News Chopper", 489: "Rancher", 490: "FBI Rancher", 491: "Virgo",
    492: "Greenwood", 493: "Jetmax", 494: "Hotring Racer", 495: "Sandking",
    496: "Blista Compact", 497: "Police Maverick", 498: "Boxville", 499: "Benson",
    500: "Mesa", 501: "RC Goblin", 502: "Hotring Racer 2", 503: "Hotring Racer 3",
    504: "Bloodring Banger", 505: "Rancher Lure", 506: "Super GT", 507: "Elegant",
    508: "Journey", 509: "Bike", 510: "Mountain Bike", 511: "Beagle",
    512: "Cropduster", 513: "Stuntplane", 514: "Tanker", 515: "Roadtrain",
    516: "Nebula", 517: "Majestic", 518: "Buccaneer", 519: "Shamal",
    520: "Hydra", 521: "FCR-900", 522: "NRG-500", 523: "HPV1000",
    524: "Cement Truck", 525: "Towtruck", 526: "Fortune", 527: "Cadrona",
    528: "FBI Truck", 529: "Willard", 530: "Forklift", 531: "Tractor",
    532: "Combine Harvester", 533: "Feltzer", 534: "Remington", 535: "Slamvan",
    536: "Blade", 537: "Freight", 538: "Streak", 539: "Vortex",
    540: "Vincent", 541: "Bullet", 542: "Clover", 543: "Sadler",
    544: "Fire Truck Ladder", 545: "Hustler", 546: "Intruder", 547: "Primo",
    548: "Cargobob", 549: "Tampa", 550: "Sunrise", 551: "Merit",
    552: "Utility Van", 553: "Nevada", 554: "Yosemite", 555: "Windsor",
    556: "Monster 2", 557: "Monster 3", 558: "Uranus", 559: "Jester",
    560: "Sultan", 561: "Stratum", 562: "Elegy", 563: "Raindance",
    564: "RC Tiger", 565: "Flash", 566: "Tahoma", 567: "Savanna",
    568: "Bandito", 569: "Freight Train Flatbed", 570: "Streak Train Trailer",
    571: "Kart", 572: "Mower", 573: "Dune", 574: "Sweeper",
    575: "Broadway", 576: "Tornado", 577: "AT-400", 578: "DFT-30",
    579: "Huntley", 580: "Stafford", 581: "BF-400", 582: "Newsvan",
    583: "Tug", 584: "Trailer (Tanker Commando)", 585: "Emperor", 586: "Wayfarer",
    587: "Euros", 588: "Hotdog", 589: "Club", 590: "Box Freight",
    591: "Trailer 3", 592: "Andromada", 593: "Dodo", 594: "RC Cam",
    595: "Launch", 596: "Police LS", 597: "Police SF", 598: "Police LV",
    599: "Police Ranger", 600: "Picador", 601: "S.W.A.T.", 602: "Alpha",
    603: "Phoenix", 604: "Glendale Damaged", 605: "Sadler Damaged",
    606: "Baggage Trailer (covered)", 607: "Baggage Trailer (uncovered)",
    608: "Trailer (Stairs)", 609: "Boxville Mission", 610: "Farm Trailer",
    611: "Street Clean Trailer",
}

# The MOD SHOP upgrades, IDs 1000..1193. They go in the slot record, ten int16
# slots at +20..+40, and `SIN_MEJORA` (0xffff) means "empty slot".
#
# Same caveat as above: the table does not come from any save. But here there is a
# good contrast, and it was done: among the 649 cars WITH upgrades in the file,
# **none carries two upgrades from the same category** and **none uses an ID outside
# 1000..1193**. If the table were shifted or invented, that property would not hold
# in 649 cars; the game puts one part per slot and the data respects it.
SIN_MEJORA = 0xFFFF

MEJORAS = {}
for _tramo, _que in (
    ("1000,1001,1002,1003,1014,1015,1016,1023,1049,1050,1058,1060,1138,1139,1146,"
     "1147,1158,1162,1163,1164", "spoiler"),
    ("1004,1005,1011,1012", "hoods"),
    ("1006,1032,1033,1035,1038,1053,1054,1055,1061,1067,1068,1088,1091,1103,1128,"
     "1130,1131", "roof"),
    ("1007,1017,1026,1027,1030,1031,1036,1039,1040,1041,1042,1047,1048,1051,1052,"
     "1056,1057,1062,1063,1069,1070,1071,1072,1090,1093,1094,1095,1099,1101,1102,"
     "1106,1107,1108,1118,1119,1120,1121,1122,1124,1133,1134,1137", "side skirt"),
    ("1008,1009,1010", "nitro"),
    ("1013,1024", "headlights"),
    ("1018,1019,1020,1021,1022,1028,1029,1034,1037,1043,1044,1045,1046,1059,1064,"
     "1065,1066,1089,1092,1104,1105,1113,1114,1126,1127,1129,1132,1135,1136", "exhaust"),
    ("1025,1073,1074,1075,1076,1077,1078,1079,1080,1081,1082,1083,1084,1085,1096,"
     "1097,1098", "wheels"),
    ("1086", "stereo"),
    ("1087", "hydraulics"),
    ("1100,1123,1125", "bullbars"),
    ("1109,1110", "rear bullbars"),
    ("1111,1112", "front sign"),
    ("1115,1116", "front bullbars"),
    ("1117,1152,1153,1155,1157,1160,1165,1166,1169,1170,1171,1172,1173,1174,1176,"
     "1179,1181,1182,1185,1188,1189,1190,1191", "front bumper"),
    ("1140,1141,1148,1149,1150,1151,1154,1156,1159,1161,1167,1168,1175,1177,1178,"
     "1180,1183,1184,1186,1187,1192,1193", "rear bumper"),
    ("1142,1143,1144,1145", "hood ornament"),
):
    for _id in _tramo.split(","):
        MEJORAS[int(_id)] = _que
assert len(MEJORAS) == 194, len(MEJORAS)

# WHICH UPGRADES EACH CAR ACCEPTS, MEASURED -- AND WHY THIS EXISTS
# ----------------------------------------------------------------
# Eight body kit pieces from a Remington were put on the hangar Rhino and **the game
# crashed when loading the save** (August 7, tested on the phone). It was not that
# they looked ugly: it did not start.
#
# The explanation was in the file's own data: the Rhino appears parked **81 times
# and not once with upgrades**. The game never applies them because the mod shop
# does not offer any. Of 68 parked models, only 17 have ever had upgrades.
#
# So this table is a MEASURED whitelist: for each model, the upgrades the game has
# actually placed on it in any of the 101 saves in the file. It is not the game's
# complete list -- it only covers what this player encountered -- but everything
# here is a combination that existed and that the game loaded.
MEJORAS_VISTAS = {
    402: {1010, 1025},
    411: {1010, 1087, 1098},
    412: {1010, 1086, 1087},
    415: {1001, 1007, 1010, 1018},
    451: {1010},
    477: {1006, 1007, 1010, 1018, 1087, 1098},
    492: {1005, 1006, 1010, 1016, 1086, 1087, 1098},
    496: {1001, 1006, 1007, 1010, 1011, 1019, 1086, 1087, 1098, 1143},
    526: {1010, 1086, 1087, 1097},
    534: {1010, 1076, 1078, 1084, 1086, 1087, 1106, 1122, 1123, 1125, 1127, 1178, 1185},
    535: {1010, 1077, 1086, 1087, 1109, 1114, 1116, 1117, 1118},
    541: {1010, 1087, 1097},
    559: {1010, 1066, 1068, 1070, 1079, 1086, 1161, 1162, 1173},
    560: {1010, 1026, 1028, 1032, 1079, 1083, 1086, 1087, 1138, 1139, 1141, 1169},
    562: {1010, 1036, 1037, 1038, 1039, 1079, 1086, 1087, 1146, 1147, 1148, 1149, 1172},
    567: {1010, 1079, 1086, 1087, 1132, 1133, 1186, 1189},
    603: {1006, 1007, 1010, 1018, 1024, 1086, 1145},
}

LIBRE = 0


def admite(modelo, idm):
    """Whether that model has been seen with that upgrade applied by the game."""
    return idm in MEJORAS_VISTAS.get(modelo, ())


def mejora(idm):
    """'1127 (exhaust)'. Returns None if the ID is not a known upgrade."""
    que = MEJORAS.get(idm)
    return f"{idm} ({que})" if que else None


def nombre(modelo):
    """The model name, or None if not in the table."""
    return NOMBRES.get(modelo)


def etiqueta(modelo):
    """How a model is printed: 'model 470 (Patriot)'.

    0 is not a vehicle, it is the empty slot mark the game writes.
    A model outside the table is shown raw instead of inventing a name.
    """
    if modelo == LIBRE:
        return "(free)"
    n = NOMBRES.get(modelo)
    return f"model {modelo} ({n})" if n else f"model {modelo}"


if __name__ == "__main__":
    import sys
    for arg in sys.argv[1:] or ["0", "470", "522", "571", "999"]:
        print(f"  {arg:>5}  {etiqueta(int(arg))}")
