# Contract

This file fixes both ends of the build. Later work may add to the middle; it never edits these two ends to make something easier.

## Purpose end

After any knockdown Ryu scores, the lab answers in three taps on a phone:

> I landed this, here, against this character, with these resources. Here is the top option, what it beats, what it loses to, and how sure the lab is.

Scope: Classic-controls Ryu, Street Fighter 6, every released character on the opponent side (32 as of the 2026-10-13 patch).

## Artifact end

The sealed core in `core/`: the exhaustive frame-kill solver, the verified Ryu inputs and the 40 knockdown values, as audited on 2026-09-28. `core/CORE_LOCK.json` records their hashes and the solver's expected output. `tests/test_core.py` proves the seal, two byte-identical runs, both published anchors, and an independent re-evaluation of every row.

## Decisions (2026-11-18)

1. Built from scratch. The earlier site is not opened during research or build; a separate agent compares the two only after release.
2. Every released character is covered on the opponent side.
3. Private community documents are supplied by the owner. In-game checks and match data are not, so nothing may depend on them.
4. The full pipeline was approved: about 63 agents across eleven research waves, built one inch at a time.

## Done tests

Each is run or opened, never argued.

1. A situation card (ender, position, opponent, resources) shows a top option, what it beats, what it loses to, and separate confidence for timing, reach, rules and opponent data.
2. Any knockdown number from 1 to 110 returns a card or an explicit "no qualifying option, because…", equal to a direct solver run.
3. Every opponent has a wake-up card whose every number matches a quote in a saved source copy.
4. Every row carries exactly one status label; one page lists everything unconfirmed and every coverage gap.
5. Burnout and resource toggles change rows exactly as the cited rules say.
6. Every published setup either reproduces or its difference is explained by a named patch.
7. Two builds from the same inputs are byte-identical.
8. Every number on the page resolves to a source copy and quote, or to a derivation from ones that do.

## Never

- Never open the earlier site before the release tag.
- Never commit raw third-party pages or any text from private documents: this repository is public.
- Never show a number without a status label, a patch tag and a source.
- Never let timing evidence stand in for reach evidence; they are separate badges.
- Never write "optimal" or "best" without naming the rule, its scope and its evidence.
- Never resolve a disagreement between sources silently, and never ship a system rule without a quote.
- Never edit `core/`.

## Status labels

| Label | Meaning |
|---|---|
| confirmed in game | Measured on the training-mode frame meter by the owner |
| verified | Inputs match current sources, the convention is cited, the arithmetic was reproduced independently |
| verified* | Verified except for one named conflicting input |
| calc only | The arithmetic reproduces but no published result exists for that exact timing |
| corrected | A value was changed; the changelog gives the evidence |

Reach, spacing and back-rise distance are never covered by these labels. They get their own badge.

## Working interpretations (not yet decided by the owner)

- "Top option" means the option that beats or is safe against the most of that opponent's available wake-up options, then block advantage. It is shown on the first card so it can be changed there.
- "Common enders" are ranked from combo guides, because no match data is used.
- Outer layers requested later (training-mode recipe per card, practice log with spaced review, execution notes, print sheet, automatic retest flags after a patch) are added outward at seams once the core lab works. Cutting any of them off must leave everything inside working.
