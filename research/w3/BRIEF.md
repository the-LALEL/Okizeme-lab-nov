# Opponent verification wave: shared brief

You verify draft "wake-up profiles" for four Street Fighter 6 characters. A wake-up profile lists what a character can do on the first frames after getting up from a knockdown that changes what the attacker should do. The project may only use a fact that has an exact quote behind it.

## Files (local only; do not use the web)
For each of your characters `<slug>`, under `/home/user/Okizeme-lab-nov/`:
- `sources/raw/roster_text/<slug>.capcom.txt`: Capcom's official frame table, one row per line, cells separated by ` | ` (move name, start-up, active, recovery, hit, block, cancel, damage, ..., last cell = notes).
- `sources/raw/roster_text/<slug>.supercombo.txt`: the SuperCombo wiki's database rows, one move per line as `field=value; ...` (invuln, armor, airborne, guard, notes among them).
- `data/opponents/<slug>.json`: the draft profile, parsed by script from the SuperCombo rows.
- `data/opponents/_capcom_check.json`: for each character, the reversal entries where the script could not match Capcom and the draft (`capcom_only`, `draft_only`).

## Your two jobs, per character
1. **Differences.** For every entry under `capcom_only` and `draft_only` for the character, read both source files and decide which of these it is: `same_move_values_agree` (the script failed to match wording), `same_move_values_differ` (the two sources give different numbers: report both), `only_in_capcom`, `only_in_supercombo`, or `not_a_wakeup_reversal` (for example it needs a previous move, a stance, a held charge, or is airborne-only). Quote both sources where both have the move.
2. **Completeness.** Read every row of both files for the character and list wake-up-relevant options the draft profile does NOT already contain, in these classes:
   - `reversal`: strike-invulnerable from frame 1 (meterless, Overdrive or super);
   - `throw_immune`: cannot be thrown from frame 1 to at least frame 3 (invulnerable to throws, or airborne that early);
   - `armor`: armor or hit absorption active by frame 3;
   - `counter`: a parry or counter stance that catches strikes by frame 3;
   - `command_grab`: a special or super that is a throw;
   - `evasive`: low-profile, upper-body or lower-body invulnerability starting by frame 3, or a teleport.
   Also confirm or correct the draft's `fastest_normals`, `jump`, `backdash_total` against Capcom's rows where Capcom states them.

## Rules
- Every value you report needs an exact quote: absolute file path, 1-based line number, and text copied exactly from that line (a contiguous excerpt of at most 40 words). A script checks every quote; do not paraphrase inside quotes.
- Never fill a value from memory of the game. If the files do not say, write `not stated`.
- If the two sources disagree, report both values; do not pick a winner.
- Budget: about 30 tool calls. Rewrite your evidence file after each character.
- Write only your evidence file. Do not open anything under `research/` except this brief.

## Evidence file shape (JSON)
```
{"characters": [{"slug": "ken",
  "differences": [{"entry": "236236K Example", "verdict": "same_move_values_differ",
     "capcom": {"startup": "9", "invulnerable": "1-16 strikes and throws"},
     "supercombo": {"startup": "9", "invulnerable": "1-15 Strike/Throw"},
     "quotes": [{"file": "/abs/path", "line": 3, "text": "exact"}], "note": ""}],
  "missed_options": [{"class": "armor", "move": "name and input", "startup": "..", "detail": "what it does and from which frame",
     "resource": "none | 2 Drive bars | super", "quotes": [{"file": "/abs/path", "line": 3, "text": "exact"}]}],
  "stats_check": [{"field": "backdash_total", "draft": "23", "capcom": "23", "quotes": [{"file": "/abs/path", "line": 3, "text": "exact"}]}],
  "notes": ""}]}
```
Your final message: one line per character with the counts of differences resolved and missed options found.
