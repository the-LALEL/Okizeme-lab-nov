# Okizeme lab

A from-scratch reference for what Classic-controls Ryu can do after every knockdown in Street Fighter 6, against every released character. "Okizeme" (oki) is the pressure applied while the opponent is getting up.

Every number the lab shows is computed by a script from saved source copies, carries a status label and a patch tag, and links to the quote it rests on. Whether a timing-valid setup actually reaches the opponent is tracked separately from its timing and never assumed.

## Layout

| Path | What it holds |
|---|---|
| `core/` | The sealed core: the exhaustive frame-kill solver, verified Ryu inputs and knockdown values, and the lock file with their hashes |
| `tests/` | Proofs that run against the real files |
| `docs/CONTRACT.md` | The two fixed ends of the build, the decisions, the done tests and the never-list |

## Check the core

```
python -m pytest tests/test_core.py -q
```

This proves four things: the core files are unchanged, two solver runs are byte-identical, both published anchors reproduce, and every one of the 1,134 output rows reproduces from the inputs with a separately written implementation of the formula.

## Status

Inch 1 of the build is done (the core runs here and is proven). Inputs were verified on 2026-09-28 against the 2026-08-03 Ryu patch; the freshness proof against today's sources is the next data step.
