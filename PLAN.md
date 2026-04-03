# Implementation Plan — GAG + Rennpause + Box Integration

## Overview

Integrate three new data fields from galopp-statistik.de into app.py:
- `Box` — confirmed starting box (hardcoded in races.md, replaces manual UI entry)
- `GAG` — official handicap performance rating (relative within field)
- `Rennpause` — days since last race (fitness/freshness signal)

New composite weights: Form 25% · GAG 20% · Jockey 12% · Season 10% · Distance 10% · Rennpause 8% · Career 5% · Expert 5% · Box 5%

---

## Functions to Add

| Function | Purpose |
|---|---|
| `score_gag(gag, field_gag_values)` | Relative GAG normalization within race field |
| `score_rennpause(rennpause)` | Tiered fitness signal from days since last race |

## Functions to Modify

| Function | Change |
|---|---|
| `load_races()` | Parse `Box:`, `GAG:`, `Rennpause:` lines; add to horse dict |
| `composite()` | New signature: add `field_gag`; replace formula with 9-factor weights; box from `horse["box"]` |
| `race_probs()` | Remove `box_numbers` param; compute `field_gag`; new call signature |
| `make_explanation()` | Add `field_gag` optional param; insert GAG-highest and Rennpause signals |
| Sidebar weights table | Replace with 9-factor table + new footnotes |
| Per-race loop (main) | Remove box expander; update `race_probs()` call; add debütant note |
| Score details expander | Show 9 factors in 3×3 grid |
| Horse card | Add GAG / Rennpause info line below form badges |
| Wettschein collection | Pass `field_gag` to `make_explanation()` both call sites |

---

## Implementation Order

1. ✅ **SECTION 1** — `load_races()`: parse Box, GAG, Rennpause
2. ✅ **SECTION 2** — Add `score_gag()`
3. ✅ **SECTION 3** — Add `score_rennpause()`
4. ✅ **SECTION 4** — `composite()`: new signature (add `field_gag`, box from `horse["box"]`)
5. ✅ **SECTION 5** — `race_probs()`: new signature, compute `field_gag` internally; update call site; remove box expander
6. ✅ **SECTION 6** — Sidebar: update weights table + footnotes
7. ✅ **SECTION 7** — Horse cards: add GAG/Rennpause line in card + score details 3×3
8. ✅ **SECTION 8** — Debütant race note
9. ✅ **SECTION 9** — `make_explanation()`: add GAG/Rennpause signals

---

## Risks and Notes

**Signature ripple**: `composite()` drops `box` param and adds `field_gag`. Only one call site: inside `race_probs()`. Safe.

**`race_probs()` signature change**: drops `box_numbers` dict. One call site in `main()`. Must update simultaneously with removing box expander.

**`make_explanation()` call sites**: two in main() (has_odds and no_odds wettschein paths). Both must receive `field_gag`. Computed once per race before the card loop.

**`score_box()` unchanged**: logic stays identical. Now reads `horse.get("box", 0)` inside `composite()` instead of from a session-state dict.

**Default for `rennpause`**: 150 days (typical winter break — neutral-ish signal, avoids penalizing horses whose data is missing vs genuine fitness concern).

**Debütant detection**: `all(h["career_starts"] == 0 for h in horses)` — Race 1 is pure debütants. Display note once after notes section.

**`field_gag` for `score_gag`**: only non-zero values (`h["gag"] > 0`). If all zero (Race 1, Race 2 partially), `score_gag` returns 0.50 for all. Safe.

**CSS, page config, GROUND_OPTIONS, GROUND_CODES**: untouched.

**Wettschein structure**: unchanged (Part 1 Hauptwette + Part 2 Kombi-Idee), only Wettschein collection passes new `field_gag` arg.

**Live reactivity**: nothing new stored in session_state. `field_gag` is a local variable computed per re-run.
