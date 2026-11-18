# Okizeme lab

A from-scratch reference for what Classic-controls Ryu can do after every knockdown in Street Fighter 6, against every released character. "Okizeme" (oki) is the pressure applied while the opponent is getting up.

Every number the lab shows is computed by a script from saved source copies, carries a status label and a patch tag, and links to the quote it rests on. Whether a timing-valid setup actually reaches the opponent is tracked separately from its timing and never assumed.

## Layout

| Path | What it holds |
|---|---|
| `core/` | The sealed core: the exhaustive frame-kill solver, verified Ryu inputs and knockdown values, and the lock file with their hashes |
| `lab/` | The build layer outside the core: it runs the solver, checks the output against the lock, then selects and labels rows for display. It does no frame arithmetic |
| `site/` | The built page. It only looks things up in the data the build embedded |
| `tests/` | Proofs that run against the real files |
| `docs/CONTRACT.md` | The two fixed ends of the build, the decisions, the done tests and the never-list |

## Check the core

```
python -m pytest tests/test_core.py -q
```

This proves four things: the core files are unchanged, two solver runs are byte-identical, both published anchors reproduce, and every one of the 1,134 output rows reproduces from the inputs with a separately written implementation of the formula.

## Build the page

```
python lab/build_site.py
python -m pytest tests -q
node tests/card_smoke.js <screenshot_dir>
```

The tests prove the build is deterministic, that every row on the page equals the solver's row field by field, and that each pick obeys the stated selection rule. The browser check opens the page at 390x844 in light and dark and fails on any sideways scroll or script error.

## Status

- Inch 1: the core runs here and is proven.
- Inch 2: one real card (LK Tatsu) reads as an answer on a phone-sized page. It shows timing only; opponent data, reach, throws, shimmies and safe jumps are marked as not built yet.

Inputs were verified on 2026-09-28 against the 2026-08-03 Ryu patch; the freshness proof against today's sources is the next step.
