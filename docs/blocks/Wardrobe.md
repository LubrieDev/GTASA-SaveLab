# CJ's wardrobe (clothes, hair and tattoos) — within block 2

Located behind the weapons table, within the ped record, in the structure
GTA SA calls `CPedClothesDesc`.

## Layout

```
+0     uint32  models[10]      the garment (the DFF)
+40    uint32  textures[18]     the pattern on top (the TXD)
+112   float   fat             copy of float[21] from the stats block
+116   float   muscle          copy of float[23]
```

The offset within block 2 is **not fixed**: block 2 grows with the loaded world
(seen going from 5,217 to 74,765 bytes). It is located by the fat+muscle
anchor — searching for the float pair `(250.0, 1000.0)` (or similar values)
within the block, which appears only once.

## The confirmed slots

### `models[10]` — garment meshes

| Slot | What it is |
|---|---|
| 0 | torso |
| 1 | head / hair |
| 2 | **unknown** — not clothes; survives removing everything; likely CJ's underwear |
| 3 | legs |
| 4 | shoes |
| 5 | chain |
| 6 | watch |
| 7 | face accessory (bandana, shades, eyepatch — shares a single slot) |
| 8 | cap |
| 9 | **special outfit** (racing suit, gym outfit, gangster outfit, etc.) |

### `textures[18]` — textures/patterns

| Slot | What it is |
|---|---|
| 0 | torso texture |
| 1 | hair texture |
| 2 | legs texture |
| 3 | shoes texture |
| 4–12 | **the nine tattoo slots** |
| 13 | chain texture |
| 14 | watch texture |
| 15 | face accessory texture |
| 16 | cap texture |
| 17 | special outfit texture |

## Key behaviors

### Removing something reveals more than adding it

When **removing** a garment the game empties its two slots (model and texture to
0), making the mapping unambiguous. This is the technique that closed out the
wardrobe.

### Accessories can be zeroed; core clothing cannot

Getting naked doesn't empty the slot, it **replaces** it:
- Torso, legs, shoes → texture goes to 0 but the **model changes** to another
  value (the bare body mesh, pantsless legs, bare feet).
- Accessories (chain, watch, cap) → model and texture both go to 0.

### Tattoos are texture only

None of the nine tattoo slots ever moved a model. They only affect `textures[4..12]`.

### The same design in two slots does NOT produce the same hash

Three tattoos called "gun" were applied (left forearm, back, left pectoral) and
produced three different hash values. A hash dictionary must carry **the slot in
addition to the name**.

The same design in the **same** slot DOES repeat the hash — hashes are stable
across saves.

### A garment can share a hash between model and texture

The white tank top wrote the same hash in `models[0]` and `textures[0]`.

### Glasses and bandanas share a slot

`models[7]` + `textures[15]` is **a single face accessory slot**. Taking off
sunglasses and putting on a bandana in the same session moves the same pair from
one to the other — the two actions cannot be separated.

### Special outfits are a separate layer

`models[9]` + `textures[17]` are the pair for the **special outfit**. Putting one
on:
- **doesn't erase anything.** Torso, legs, shoes, cap, shades, and tattoos stay
  exactly as they were. The outfit is painted on top; when removed, the set
  underneath reappears.
- **doesn't touch sex appeal.** `float[25]` stayed at 500 with the outfit on.

### The afro forces the cap

When getting a haircut (afro), `models[8]` and `textures[16]` go to 0 without
the player touching the cap.

### Meshes are shared within some categories

| Category | Does the model change when switching items? |
|---|---|
| watch | **no** — different watches share the same model hash |
| chain | **no** — cross and dog tags share the same model hash |
| glasses | **no** — different glasses share the same model hash |
| cap | **yes** — cap and hat have different models |
| torso, legs, shoes | **yes** |

## Hash-based identification

Each garment is a `uint32` that is the hash of a name. The hash algorithm
(Jenkins uppercase / `CKeyGen`) has not been cracked for the garment name space.
What can be done is **copy the hash from a save that already has it equipped**.

Watch out for false positives: hashes also appear in block 1 around **+15300**,
which is the shop script's working buffer — it stores *the last thing you
touched*, not what you're wearing. The real wardrobe is the one in block 2.

## Stats affected by clothing

`float[25]` (sex appeal) is NOT directly controlled by clothing. Getting naked,
putting on a tuxedo, or wearing a special outfit all leave it at 500. The
cause of small fluctuations (−5, −10) observed when adding individual accessories
remains unidentified.
