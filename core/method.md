# Method: the meaty formula, its assumptions, and known traps

## Formula

K = knockdown advantage, T = frames spent on preparation (whiffs, dashes, instant raw Drive Rush), S = the meaty's startup, A = its active frames, R = K − T (remaining frames).

- Contact active frame: **c = R − S + 2**. It is a true meaty only if 1 ≤ c ≤ A.
- Single-hit advantage = listed block or hit + (c − 1), plus 4 for a Drive-Rush-enhanced normal or command normal.
- Multi-hit moves use published mappings keyed by R (below), never the single-hit formula.

**Derivation:** the attacker is free on frame 1 and the defender on frame K+1. An attack pressed on frame T+1 with startup S is first active on frame T+S. Contact on frame K+1 is therefore active frame K+1−(T+S)+1.

**Worked example:** Light Tatsu (+35), dash (19f), LP Hashogeki (12 startup, 6 active, −3 on block). R = 16, c = 6, block = −3+5 = **+2**, hit = +2+5 = **+7**. Masaguru, nikotaro, Cauterize and sf6wiki all publish +2/+7.

## Assumptions and their status (Sept 28, 2026)

| # | Assumption | Status | Evidence |
|---|---|---|---|
| 1 | "KD +X" means the defender first acts on frame X+1 | **Confirmed** | st6noob (Luke 5HK at +15 hits on its last active frame, 7); DeeJay Drive Impact meaty "at most +26" (26f startup, 2 active; the rival convention predicts +27); SuperCombo Offense (+5 throw, "+11 into Drive Rush") |
| 2 | Quick rise and back rise have the same timing | **Confirmed** | SuperCombo Defense: no difference in knockdown advantage; only spacing differs |
| 3 | Throws on wake-up | **1f throw invincibility** | SuperCombo Offense and the nylonhat wiki. A throw whose first active frame meets wake-up frame 1 connects on its 2nd active frame (wake-up frame 2); it still beats a 4f mash. A throw at +6 whiffs |
| 4 | Raw (parry) Drive Rush = 11 frames before the attack starts | **Confirmed** | SuperCombo Gauges: Parry Drive Rush "3+8"; 1+8 after a held successful parry; 9 for a Drive Rush cancel |
| 5 | +4 on hit and block for Drive-Rush normals and command normals, none for specials | **Confirmed** for normals and command normals; specials are left out by omission | SuperCombo Gauges; Capcom Mar 17, 2026 notes (overheads "-3 on block, so +1 with a Drive Rush") |
| 6 | Each later active frame adds +1 to block and hit (single-hit moves) | **Confirmed** | st6noob: Luke 5HK has fixed blockstun on every active frame |
| 7 | Multi-hit meaties | **Derived** from per-hit data: the move frame meeting wake-up is R + 1; hits ending earlier whiff; the last connecting hit sets advantage = stun − (total − contact frame) − 1 | Reproduces every published Ryu 6HP and 6MP value, including pre-patch 6MP from the pre-patch blockstun |
| 8 | Fixed-advantage multi-hits (Ryu HP Hashogeki +2) | **Structural:** the final hit is always move frame 35, so advantage is constant for contact 1–6 | SuperCombo "2 hits, even if it connects on final active frame"; published at R 29, 32, 33 |
| 9 | Mar 17, 2026 wake-up buffer change (+3 buffered input) and the Apr 15, 2026 Drive Rush adjustment | **No effect on attacker timing** | They change only how early the defender can pre-input |

## Traps (each one has already happened)

- **Notes predate patches and are incomplete.** Ryu 6MP's meaty values (0/+1) came from 2025 notes; the Mar 17, 2026 patch cut its 2nd-hit blockstun 21→19, making them −2/−1. The notes also skipped the R19–20 timings, which hid 7 valid Drive Rush rows. Derive from per-hit data instead.
- **Whiff recovery differs from block/hit recovery.** Ryu 5MP totals 20 but 22 on whiff, and 2MP 22 but 24. Use whiff totals for preparations.
- **Active-frame counts disagree by language.** OD Hashogeki: Capcom and Japanese wikis say 5, English databases say 6. A published in-game result decides it (Masaguru +8 → 6).
- **Last-active-frame rows are fragile.** Any conflict on the active count or the convention breaks them first, so put them first on the test card.
- **Old strategy pages lag the data pages.** Sweep was +32 on the old Strategy page vs +40 on Data; HP Shoryuken +29 vs +37 after a 2025 change. Check edit dates.
- **Knockdown values can be minimums or ranges.** UFD's "+52 minimum" Denjin Hadoken vs SuperCombo's +54.
- **Frame data can't show reach.** Pushback (Aug 3, 2026: Ryu 5LP and 6HP on block), knockback and back-rise distance decide whether a timing-valid row connects. Only the game or published setups settle reach.
- **Projectiles, jumps and moves with hit gaps don't fit the formula.** Exclude them or model them separately.
