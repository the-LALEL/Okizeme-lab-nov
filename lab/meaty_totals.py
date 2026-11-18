"""Whiff length (total frames) of every meaty the solver models, from the saved sources.

The core carries whiff lengths only for moves used as preparations. Judging whether Ryu
recovers in time to block a wake-up reversal needs the whiff length of the meaty itself.
Three sources are read; a move whose sources disagree is recorded as a conflict with every
candidate value, never resolved here.

Usage: python lab/meaty_totals.py --fat /path/to/fat/clone
Writes: data/ryu/meaty_totals.json
"""
import argparse
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "lab"))
import snap  # noqa: E402
from freshness import ALIASES, FAT_FILE, capcom_windows, clean, ints  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fat", required=True)
    args = ap.parse_args()
    inputs = json.loads((ROOT / "core" / "ryu_inputs.json").read_text())
    capcom = [r for r in json.loads(snap.read("capcom/frame-ryu.rows.json")) if len(r) > 5]
    cargo = json.loads(snap.read("supercombo/cargo/SF6_FrameData.Ryu.json"))
    fat = list(json.loads((pathlib.Path(args.fat) / FAT_FILE).read_text())["Ryu"]["moves"]["normal"].values())

    out = {}
    for move in list(inputs["single"]) + list(inputs["multi"]):
        inp, cap_name, fat_name = ALIASES[move]
        c = next(r for r in capcom if r[0].startswith(cap_name))
        w = next(r for r in cargo if r["input"] == inp)
        f = next(m for m in fat if (fat_name and m["moveName"] == fat_name) or (not fat_name and m.get("numCmd") == inp))
        extra = re.search(r"(\d+) frames? of recovery added when the attack misses", c[-1])
        official = capcom_windows(c[2])[-1][1] + int(c[3]) + (int(extra.group(1)) if extra else 0)
        wiki, fat_vals = ints(clean(w["total"])), ints(f["total"])
        core_whiff = inputs["preparations"]["whiff"].get(move)
        candidates = {official} | ({core_whiff} if core_whiff else set())
        agreed = official in wiki and official in fat_vals and (core_whiff in (None, official))
        if agreed:
            entry = {"total": official, "status": "agree"}
        else:
            # community value: the one both community sources list that is not Capcom's
            community = sorted(set(wiki) & set(fat_vals)) or sorted(set(wiki) | set(fat_vals))
            entry = {"total": core_whiff or community[-1], "status": "conflict",
                     "candidates": sorted(candidates | set(community))}
        entry["sources"] = {"capcom_derived": official, "capcom_text": f"{c[1]} / {c[2]} / {c[3]}",
                            "supercombo_total": clean(w["total"]), "fat_total": str(f["total"])}
        out[move] = entry
    path = ROOT / "data" / "ryu" / "meaty_totals.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    for move, e in out.items():
        print(f"{move:22} {e['total']:3} {e['status']:9} {e['sources']}")


if __name__ == "__main__":
    main()
