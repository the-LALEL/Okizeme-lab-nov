"""Inch 7, step 2: cross-check every draft wake-up profile against Capcom's official frame page.

For each character, the moves Capcom's page says are strike-invulnerable from frame 1 are compared
with the draft's reversal list (parsed from SuperCombo's database) by startup and by the last
invulnerable frame. Anything on one side only is recorded, never dropped or patched here.

Usage: python lab/opponents_check.py
Writes: data/opponents/_capcom_check.json
"""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "lab"))
import snap  # noqa: E402
from freshness import ints  # noqa: E402
from opponents import windows  # noqa: E402

CAPCOM_SLUG = {"a-k-i": "aki", "akuma": "gouki_akuma", "c-viper": "cviper", "chun-li": "chunli", "dee-jay": "deejay",
               "e-honda": "ehonda", "m-bison": "vega_mbison"}
INVULN = re.compile(r"(Completely invincible|Invincible to strikes[a-z ]*?)\s+(?:from|on|between|for)\s+frames?\s*(\d+)\s*(?:-|to frame)\s*(\d+)")


def main():
    out, totals = {}, {"matched": 0, "capcom_only": 0, "draft_only": 0}
    for entry in json.loads((ROOT / "data" / "opponents" / "_roster.json").read_text()):
        slug = entry["slug"]
        profile = json.loads((ROOT / "data" / "opponents" / f"{slug}.json").read_text())
        rows = [r for r in json.loads(snap.read(f"capcom/frame-{CAPCOM_SLUG.get(slug, slug)}.rows.json")) if len(r) > 5]
        official = {}
        for r in rows:
            if r[0].startswith("Drive Reversal") or r[0].startswith("Perfect Parry"):
                continue
            for kind, start, end in INVULN.findall(re.sub(r"\s+", " ", r[-1])):
                if int(start) == 1 and ints(r[1]):
                    official.setdefault((ints(r[1])[0], int(end)), {"name": r[0], "startup_text": r[1], "kind": kind})
        draft = {}
        for m in profile["reversals"]:
            end = next((w["to"] for w in windows(m["invuln_text"]) if w["from"] == 1 and w["type"] in ("Full", "Strike", "Strike/Throw")), None)
            draft.setdefault((m["startup"], end), m)
        both = sorted(set(official) & set(draft))
        capcom_only = [{"startup": k[0], "invulnerable_to_frame": k[1], **official[k]} for k in sorted(set(official) - set(draft))]
        draft_only = [{"startup": k[0], "invulnerable_to_frame": k[1], "input": draft[k]["input"], "name": draft[k]["name"],
                       "invuln_text": draft[k]["invuln_text"]} for k in sorted(set(draft) - set(official), key=str)]
        out[slug] = {"character": profile["character"], "matched": len(both), "capcom_only": capcom_only, "draft_only": draft_only}
        totals["matched"] += len(both); totals["capcom_only"] += len(capcom_only); totals["draft_only"] += len(draft_only)
        flag = "" if not (capcom_only or draft_only) else "  <-- differs"
        print(f"{profile['character']:10} matched {len(both)}  capcom-only {len(capcom_only)}  draft-only {len(draft_only)}{flag}")
        for x in capcom_only:
            print(f"     capcom-only: {x['name'][:44]} startup {x['startup_text']} invulnerable 1-{x['invulnerable_to_frame']} ({x['kind']})")
        for x in draft_only:
            print(f"     draft-only:  {x['input']} {x['name'][:34]} startup {x['startup']} [{x['invuln_text'][:40]}]")
    (ROOT / "data" / "opponents" / "_capcom_check.json").write_text(json.dumps({"totals": totals, "characters": out}, indent=1, ensure_ascii=False) + "\n")
    print(totals)


if __name__ == "__main__":
    main()
