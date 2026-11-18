# Ryu data verified Sept 28, 2026

Patch state: the latest Ryu battle change is Aug 3, 2026, which changed pushback, blowback and juggle limits only (5LP and 6HP pushback on block, air Tatsu blowback after 6HK, OD Shoryuken juggles, Modern controls). Mar 17, 2026 (the "Alex patch") changed:
- 6MP block to −3 (2nd-hit blockstun 21→19)
- 5MP whiff recovery (+2)
- target combo knockdowns: 5HP~HK +36→+39, its Denjin cancel +7→+10
- 6HP shadow-lock timing
- the system wake-up input buffer (+3)

Machine-readable inputs are in `ryu_inputs.json`.

## Single-hit inputs (Capcom official)

| Move | Startup | Active | Block | Hit | Whiff total |
|---|---|---|---|---|---|
| 5LP | 4 | 3 | −1 | +4 | 13 |
| 2LP | 4 | 2 | −1 | +4 | 14 |
| 2LK | 5 | 2 | −1 | +3 | 16 |
| 5LK | 5 | 3 | −4 | +2 | 18 |
| 5MP | 6 | 4 | −1 | +7 | 22 (20 on hit/block) |
| 2MP | 6 | 4 | 0 | +5 | 24 (22 on hit/block) |
| 2MK | 8 | 3 | −6 | +1 | — |
| 5MK | 9 | 3 | −4 | +4 | 29 |
| 5HP | 10 | 5 | −2 | +4 | 32 |
| 6HK | 16 | 4 | −4 | +2 | 39 |
| LP Hashogeki | 12 | 6 | −3 | +2 | — |
| OD Hashogeki | 18 | 6* | +3 | +3 | — |
| Denjin OD Hashogeki | 18 | 6 | +4 | KD +87 crumple | — |
| HK High Blade Kick | 27 | 9 | −3 | KD | — |
| Throws | 5 | 3 (5–7) | — | KD | — |

\* OD Hashogeki: Capcom lists 18–22 (5 active); SuperCombo, FAT, UFD and seesaawiki list 6. SuperCombo has shown 6 active / 43 total unchanged since at least Dec 2024. Masaguru (Dec 2, 2024) reports "LK Tatsu → whiff 5LP → OD Hashogeki: +8 on hit or block", which requires 6. **Test-card item 1** settles it.

Other preparations:
- Whiff totals: 2HK 34, 2HP 35, 6HP 40, 6MP 42, 4HK 43.
- Forward dash 19, Denjin Charge 52 (the stock arrives on frame 50 or 51 depending on source).
- Instant raw Drive Rush 11.

## Multi-hit meaty values (R = remaining frames when pressed)

These are derived by `scripts/recompute.py` from the per-hit data in `ryu_inputs.json`, and every published value is reproduced. The table is for reading only.

| Move | R → block / hit | Status |
|---|---|---|
| 6HP Solar Plexus Strike (hits 20–21, 22–24; blockstun 8, 22; hitstun 25, 25; total 40) | 19–21 → +3/+6, 22 → +4/+7, 23 → +5/+8 | All derived; R20–23 also published (nikotaro, Cauterize, SuperCombo). Per-hit data identical June 2025 → Sept 2026 |
| 6MP Collarbone Breaker (hits 20, 21–23; blockstun 17, 19; hitstun 17, 25; total 42) | 19–20 → −3/+3, 21 → **−2**/+4, 22 → **−1**/+5 | **Post Mar 17, 2026** (2nd-hit blockstun 21→19, SuperCombo revs 357767→358561). The pre-patch blockstun reproduces the 2025 notes' 0/+1. R19–20 with Drive Rush = +1/+7, Capcom's "+1 with a Drive Rush"; the audited file had omitted these 7 rows |
| HP Hashogeki | +2 on block for any contact within its 6 active frames (startup 30) | Published at R29, 32, 33. Identical June 2025 → Sept 2026. A stored Denjin forces the Denjin version (startup 20, +3), so rows assume no stock |

Drive Rush adds +4 to the 6HP and 6MP values.

## Knockdown advantage by ender (current)

| Ender | KD | Notes |
|---|---|---|
| Forward throw / back throw | +17 / +11 | Back throw: no strike/throw oki even in the corner |
| Sweep / Sweep Punish Counter | +40 / HKD +47 | The old Strategy page's +32 is outdated |
| 5HP~HK / Denjin cancel | +39 / +10 | The PC field still shows +37 on Data |
| 5MP~LK~HK / Denjin cancel | +36 / +7 | |
| L / M / H DP | +38 / +34 / +37 on active frames 1–2 (+29 on later frames or juggles) | HP DP +37 after a 2025 change; some Strategy rows still say +29 |
| OD DP | +29 | |
| L Tatsu / M Tatsu (hit 1, 2) / H Tatsu (hits 1, 2, 3) / OD Tatsu | +35 / +23, +38 / +20, +35, +50 / +57 | LK Tatsu +35 unchanged since Dec 2024 |
| 6HK > air Tatsu (grounded / juggle) / > OD air Tatsu | +38 / +41–46 / +47–48 | |
| L / M / H blade | +42–46 / +40–46 / +45–51 | H blade PC: +96–102 tumble. OD blade: +49 / wall bounce +65 |
| HP Hashogeki / Denjin HP Hashogeki / Denjin OD Hashogeki | +61 / +62 / +87 (PC +91) | |
| OD Hadoken / Denjin HP Hadoken / Denjin OD Hadoken | +54 / **+54** / +57 | UFD gives a +52 minimum for Denjin HP |
| SA1 / Denjin SA1 / SA2 uncharged / SA2 tumble / SA3 and CA | +26 / +27 / +20 / +78 / HKD +14 | |
| Drive Reversal / Drive Impact | +23 / +35 (wall splat +65) | |

## Open items (as of Sept 28, 2026)

1. **OD Hashogeki 5 vs 6 active frames.** Frame-meter test: LK Tatsu → whiff 5LP → OD Hashogeki, expect +8.
2. **6MP post-patch values.** Derived from per-hit data, not measured; this also validates the derivation method. Test: LK Tatsu → whiff 5LP → 6MP, expect −1.
3. **HK High Blade Kick +5 on active frame 9.** SuperCombo's note says the best meaty is on frame 7 (+3). Test: M DP (+34) → HK blade immediately.
