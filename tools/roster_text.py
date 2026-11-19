"""Write one citeable text file per character and source for the opponent verification wave.

Usage: python tools/roster_text.py
Writes sources/raw/roster_text/<slug>.capcom.txt (one official table row per line) and
<slug>.supercombo.txt (one database row per line), both from fingerprinted snapshots.
"""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "lab"))
import snap  # noqa: E402
from freshness import clean  # noqa: E402
from opponents_check import CAPCOM_SLUG  # noqa: E402

FIELDS = ["input", "name", "moveType", "startup", "active", "recovery", "total", "guard", "hitAdv", "blockAdv",
          "invuln", "armor", "airborne", "cancel", "notes"]


def main():
    out = snap.RAW / "roster_text"
    out.mkdir(parents=True, exist_ok=True)
    rows = json.loads(snap.read("supercombo/cargo/SF6_FrameData.roster.json"))
    for entry in json.loads((ROOT / "data" / "opponents" / "_roster.json").read_text()):
        slug = entry["slug"]
        cap = json.loads(snap.read(f"capcom/frame-{CAPCOM_SLUG.get(slug, slug)}.rows.json"))
        (out / f"{slug}.capcom.txt").write_text(
            "\n".join(" | ".join(re.sub(r"\s+", " ", c) for c in r) for r in cap if r) + "\n", encoding="utf-8")
        mine = [r for r in rows if r["chara"].replace("_", " ") == entry["character"]]
        (out / f"{slug}.supercombo.txt").write_text(
            "\n".join("; ".join(f"{k}={re.sub(r'\\s+', ' ', clean(r.get(k)))}" for k in FIELDS if clean(r.get(k))) for r in mine) + "\n",
            encoding="utf-8")
    print(len(list(out.glob("*.txt"))), "files in", out.relative_to(ROOT))


if __name__ == "__main__":
    main()
