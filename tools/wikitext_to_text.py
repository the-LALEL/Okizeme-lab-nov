"""Turn saved wikitext snapshots into plain text files that people and agents can cite by line.

Usage: python tools/wikitext_to_text.py
Reads  sources/raw/supercombo/wikitext/<Page>@<revid>.json
Writes sources/raw/supercombo/text/<Page>@<revid>.txt (one wikitext line per line, unchanged)
"""
import json
import pathlib

import snap

SRC = snap.RAW / "supercombo" / "wikitext"
DST = snap.RAW / "supercombo" / "text"


def main():
    DST.mkdir(parents=True, exist_ok=True)
    for path in sorted(SRC.glob("*.json")):
        text = json.loads(snap.read(f"supercombo/wikitext/{path.name}"))["parse"]["wikitext"]["*"]
        out = DST / (path.stem + ".txt")
        out.write_text(text, encoding="utf-8")
        print(f"{out.relative_to(snap.ROOT)}: {len(text.splitlines())} lines")


if __name__ == "__main__":
    main()
