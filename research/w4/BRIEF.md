# Rules-ledger wave: shared brief

You are one worker in a rules-ledger wave for a Street Fighter 6 project. The project computes okizeme (pressure on a character who is getting up from a knockdown) and may only use a system rule that has a quote behind it.

## Goal
For each question you are assigned in `research/w4/questions.json`, state what the saved sources say, with exact quotes.

## Sources (local files only; do not use the web, do not fetch anything)
All under `/home/user/Okizeme-lab-nov/sources/raw/`:
- `supercombo/text/Offense@380932.txt` (SuperCombo SF6 Offense page, 2026-10-13)
- `supercombo/text/Defense@364973.txt` (Defense page, 2026-05-30)
- `supercombo/text/Gauges@376566.txt` (Gauges page: the Drive system, 2026-08-26)
- `supercombo/text/Movement@376569.txt` (Movement page, 2026-08-26)
- `supercombo/text/Game_Data@384214.txt` (Game Data page, 2026-10-26)
- `supercombo/text/Glossary@367082.txt` (Glossary, 2026-06-20)
- `supercombo/text/Version_2.05@380923.txt` (notes on game version 2.05, the 2026-10-13 patch)
- `capcom/frame-ryu.rows.json` (Capcom's official Ryu frame table as rendered 2026-11-18; one JSON array of cell texts per row; see the rows for throws, dashes, Drive Impact, Drive Reversal, Drive Rush, Drive Parry)
- `capcom/battle_change-20260803-en.txt`, `-20260528-en.txt`, `-20260415-en.txt`, `-20260317-en.txt`, `-202506-en.txt`, `-202405-en.txt` (Capcom's official battle-change overview pages; universal and system changes are in these)

## How to work
- Read `questions.json` first. Read the source files you need with the Read tool (whole files, up to 2,000 lines per call) and use Grep to locate terms.
- For every assigned question, fill EVERY parameter name listed for it, as a short string. Use exactly `not stated` when the sources do not say. Never fill a value from memory of the game: if you know something the files do not say, leave `not stated` and mention it in `notes` prefixed `from memory, unquoted:`.
- Every value other than `not stated` needs at least one quote: the absolute file path, the 1-based line number where the quote starts, and the quoted text copied EXACTLY as it appears on that line (a contiguous excerpt of at most 40 words, wiki markup included). A script checks each quote against the file, so do not paraphrase inside quotes and do not stitch text from different lines.
- If two sources disagree, set status `sources_conflict`, quote both, and do not pick a winner.
- status is one of: `quoted`, `partly_quoted`, `not_found`, `sources_conflict`.
- Hard budget: about 25 tool calls. After each question, rewrite your evidence file with everything so far.
- Write only your evidence file. Do not read any other file under `research/` except `questions.json` and this brief.
- Report only what you read.

## Evidence file shape (JSON)
```
{"answers": [{"rule_id": "R04", "status": "quoted", "statement": "one or two plain sentences",
  "parameters": [{"name": "...", "value": "..."}],
  "quotes": [{"file": "/abs/path", "line": 12, "text": "exact text", "supports": "parameter name(s)"}],
  "notes": ""}]}
```
