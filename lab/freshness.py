"""Inch 3: prove the sealed core's inputs are current against today's sources.

Compares every input the solver uses (core/ryu_inputs.json) and every knockdown value
(core/ryu_calc.json) with three saved sources:
  - Capcom's official frame table      (independent: official)
  - SuperCombo's database rows         (community wiki)
  - FAT's data file at a pinned commit (community; shares contributors with the wiki,
                                        so wiki + FAT count as ONE voice, not two)

Nothing here edits core/. Disagreements are recorded, never resolved silently.

Usage: python lab/freshness.py --fat /path/to/fat/clone
Writes: data/freshness.json  (committed: facts and fingerprints only)
"""
import argparse
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import snap  # noqa: E402

CORE = ROOT / "core"
FAT_FILE = "src/js/constants/framedata/SF6FrameData.json"

# my name -> (SuperCombo input, Capcom name prefix, FAT move name or None to use the input)
ALIASES = {
    "5LP": ("5LP", "Standing Light Punch", None), "2LP": ("2LP", "Crouching Light Punch", None),
    "2LK": ("2LK", "Crouching Light Kick", None), "5LK": ("5LK", "Standing Light Kick", None),
    "5MP": ("5MP", "Standing Medium Punch", None), "2MP": ("2MP", "Crouching Medium Punch", None),
    "2MK": ("2MK", "Crouching Medium Kick", None), "5MK": ("5MK", "Standing Medium Kick", None),
    "5HP": ("5HP", "Standing Heavy Punch", None), "2HP": ("2HP", "Crouching Heavy Punch", None),
    "2HK": ("2HK", "Crouching Heavy Kick", None), "6MP": ("6MP", "Collarbone Breaker", None),
    "6HP": ("6HP", "Solar Plexus Strike", None), "4HK": ("4HK", "Axe Kick", None),
    "6HK": ("6HK", "Whirlwind Kick", None),
    "LP Hashogeki": ("214LP", "L Hashogeki", None), "HP Hashogeki": ("214HP", "H Hashogeki", None),
    "OD Hashogeki": ("214PP", "OD Hashogeki", None),
    "Denjin OD Hashogeki": ("D.214PP", "[Denjin Charge]OD Hashogeki", "OD Denjin Charge Hashogeki"),
    "HK High Blade Kick": ("236HK", "H High Blade Kick", None),
}

# ender name in core/ryu_calc.json -> (SuperCombo input, name contains, field, FAT move name, FAT field)
ENDERS = {
    "HP Shoryuken, active 1-2": ("623HP", "", "hitAdv", "HP Shoryuken", "onHit"),
    "HP Shoryuken, late active or juggle": ("623HP", "", "hitAdv", None, None),
    "SA3 / CA": ("236236K", "Shin Shoryuken", "hitAdv", "Shin Shoryuken", "onHit"),
    "SA1": ("236236P", "Shinku", "hitAdv", "Shinku Hadoken", "onHit"),
    "Denjin SA1": ("236236P", "Denjin", "hitAdv", "Denjin Hadoken", "onHit"),
    "MK Tatsu, 2 hits": ("214MK", "", "hitAdv", "MK Tatsumaki Senpukyaku", "onHit"),
    "MK Tatsu, 1 hit": ("214MK", "", "hitAdv", "MK Tatsumaki Senpukyaku", "onHit"),
    "MK High Blade Kick": ("236MK", "", "hitAdv", "MK High Blade Kick", "onHit"),
    "LK High Blade Kick": ("236LK", "", "hitAdv", "LK High Blade Kick", "onHit"),
    "HK High Blade Kick": ("236HK", "", "hitAdv", "HK High Blade Kick", "onHit"),
    "LP Shoryuken, active 1-2": ("623LP", "", "hitAdv", "LP Shoryuken", "onHit"),
    "MP Shoryuken, active 1-2": ("623MP", "", "hitAdv", "MP Shoryuken", "onHit"),
    "SA2 uncharged": ("214214P", "Shin Hashogeki Lv.1", "hitAdv", "Shin Hashogeki", "onHit"),
    "OD Tatsu": ("214KK", "", "hitAdv", "OD Tatsumaki Senpukyaku", "onHit"),
    "6HK > air Tatsu, grounded": ("6HK~214K", "", "hitAdv", None, None),
    "6HK > air Tatsu, juggle": ("6HK~214K", "", "notes", None, None),
    "LK Tatsu": ("214LK", "", "hitAdv", "LK Tatsumaki Senpukyaku", "onHit"),
    "HK Tatsu, 3 hits": ("214HK", "", "hitAdv", "HK Tatsumaki Senpukyaku", "onHit"),
    "HK Tatsu, 2 hits": ("214HK", "", "hitAdv", "HK Tatsumaki Senpukyaku", "onHit"),
    "HK Tatsu, 1 hit": ("214HK", "", "hitAdv", "HK Tatsumaki Senpukyaku", "onHit"),
    "5HP~HK target combo": ("5HP~HK", "", "hitAdv", "High Double Strike", "onHit"),
    "Forward throw": ("LPLK", "", "hitAdv", "Shoulder Throw", "onHit"),
    "Back throw": ("4LPLK", "", "hitAdv", "Somersault Throw", "onHit"),
    "Sweep (2HK)": ("2HK", "", "hitAdv", "Crouch HK", "onHit"),
    "Sweep, Punish Counter": ("2HK", "", "punishAdv", "Crouch HK", "onPC"),
    "Drive Impact": ("HPHK", "", "hitAdv", None, None),
    "Drive Impact, wall splat": ("HPHK", "", "hitAdv", None, None),
    "Drive Reversal": ("6HPHK", "Recovery", "hitAdv", "Drive Reversal: Chest Strike", "onHit"),
    "5MP~LK~HK target combo": ("5MP~LK~HK", "", "hitAdv", "Fuwa Triple Strike 2", "onHit"),
    "OD Shoryuken": ("623PP", "", "hitAdv", "OD Shoryuken", "onHit"),
    "6HK > OD air Tatsu": ("6HK~214KK", "", "hitAdv", None, None),
    "OD High Blade Kick": ("236KK", "", "hitAdv", "OD High Blade Kick", "onHit"),
    "OD High Blade Kick, wall bounce": ("236KK", "", "hitAdv", "OD High Blade Kick", "onHit"),
    "HP Hashogeki": ("214HP", "", "hitAdv", "HP Hashogeki", "onHit"),
    "Denjin HP Hashogeki": ("D.214HP", "", "hitAdv", None, None),
    "Denjin OD Hashogeki": ("D.214PP", "", "hitAdv", "OD Denjin Charge Hashogeki", "onHit"),
    "OD Hadoken": ("236PP", "", "hitAdv", "OD Hadoken", "onHit"),
    "Denjin HP Hadoken": ("D.236HP", "", "hitAdv", "Denjin Charge Hadoken", "onHit"),
    "Denjin OD Hadoken": ("D.236PP", "", "hitAdv", "OD Denjin Charge Hadoken", "onHit"),
    "SA2 tumble": ("214214[P]", "Shin Hashogeki Lv.3", "hitAdv", "Shin Hashogeki", "onHit"),
}

# Differences that have been read and understood. Each carries the quote that explains it.
EXPLAINED = {
    ("whiff_total", "2HP", "capcom"): "Capcom lists recovery 22; SuperCombo lists '21(22)' and notes "
                                      "'() refers to hit/block recovery on 1st active frame only', so the whiff value is 21.",
}
OPEN_CONFLICTS = {
    ("active", "OD Hashogeki", "capcom"): "Known: Capcom prints 18-22 (5 active); the community databases list 6. "
                                          "Already flagged in the core; rows on active frame 6 depend on it.",
    ("whiff_total", "4HK", "capcom"): "New: Capcom's active window 10-23 gives a 44-frame whiff; SuperCombo and FAT "
                                      "list active 5(5)3 and total 43. Rows that whiff 4HK as preparation depend on it.",
    ("hitstun_hit1", "6MP", "fat"): "FAT lists first-hit hitstun 19; SuperCombo lists 17. No effect on any output: "
                                    "a meaty's advantage is set by the last connecting hit, which is never hit 1 alone.",
}


def clean(value):
    if value is None:
        return ""
    text = re.sub(r"<[^>]+>", "", str(value)).replace("'''", "").strip()
    return "" if re.fullmatch(r"\{\{\{\w+\}\}\}", text) else text


def ints(text):
    return [int(x) for x in re.findall(r"(?<![\w.])[+-]?\d+", str(text).replace("−", "-"))]


def as_int(text):
    text = clean(text)
    return int(text) if re.fullmatch(r"[+-]?\d+", text) else None


def hit_count_sum(text):
    """'3' -> 3, '1,3' or '2*3' -> the per-hit active counts."""
    return [int(x) for x in re.split(r"[,*]", clean(text)) if x.strip().isdigit()]


def capcom_windows(text):
    """'4-6' -> [(4, 6)]; '30-34.35' -> [(30, 34), (35, 35)]."""
    out = []
    for part in re.split(r"[.,]\s*", text.strip()):
        m = re.fullmatch(r"(\d+)(?:-(\d+))?", part.strip())
        if m:
            out.append((int(m.group(1)), int(m.group(2) or m.group(1))))
    return out


class Report:
    def __init__(self):
        self.rows = []

    def add(self, kind, subject, source, mine, theirs, raw=""):
        key = (kind, subject, source)
        if theirs is None:
            status = "not_in_source"
        elif mine == theirs or (isinstance(theirs, (list, set, tuple)) and mine in theirs):
            status = "match"
        elif key in EXPLAINED:
            status = "explained"
        elif key in OPEN_CONFLICTS:
            status = "open_conflict"
        else:
            status = "MISMATCH"
        row = {"kind": kind, "subject": subject, "source": source, "core": mine,
               "source_value": sorted(theirs) if isinstance(theirs, set) else theirs, "status": status}
        if raw:
            row["source_text"] = raw
        if status in ("explained", "open_conflict"):
            row["note"] = EXPLAINED.get(key) or OPEN_CONFLICTS.get(key)
        self.rows.append(row)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fat", required=True, help="path to a clone of D4RKONION/FAT")
    args = ap.parse_args()

    inputs = json.loads((CORE / "ryu_inputs.json").read_text())
    calc = json.loads((CORE / "ryu_calc.json").read_text())
    capcom = [r for r in json.loads(snap.read("capcom/frame-ryu.rows.json")) if len(r) > 5]
    cargo = json.loads(snap.read("supercombo/cargo/SF6_FrameData.Ryu.json"))
    fat_commit = subprocess.run(["git", "-C", args.fat, "rev-parse", "HEAD"], capture_output=True, text=True,
                                check=True).stdout.strip()
    fat_bytes = (pathlib.Path(args.fat) / FAT_FILE).read_bytes()
    fat_ryu = json.loads(fat_bytes)["Ryu"]
    snap.record("fat/SF6FrameData.Ryu.json", json.dumps(fat_ryu, sort_keys=True, ensure_ascii=False).encode(),
                url="https://github.com/D4RKONION/FAT/blob/" + fat_commit + "/" + FAT_FILE, route="git clone (pinned commit)",
                family="fat", independence_group="community-wiki", commit=fat_commit,
                note="Ryu section of FAT's data file, re-serialised sorted; GPL-3.0, used for cross-checking only")
    fat = list(fat_ryu["moves"]["normal"].values())

    def cap_row(prefix):
        return next((r for r in capcom if r[0].startswith(prefix)), None)

    def cargo_row(inp, name_part=""):
        return next((r for r in cargo if r["input"] == inp and name_part in clean(r["name"])), None)

    def fat_row(name=None, num=None):
        return next((m for m in fat if (name and m["moveName"] == name) or (num and m.get("numCmd") == num)), None)

    rep = Report()

    # 1. Single-hit meaties: startup, active count, block, hit.
    for move, spec in inputs["single"].items():
        inp, cap_name, fat_name = ALIASES[move]
        c, w, f = cap_row(cap_name), cargo_row(inp), fat_row(fat_name, None if fat_name else inp)
        wins = capcom_windows(c[2])
        rep.add("startup", move, "capcom", spec["startup"], int(c[1]), c[1])
        rep.add("startup", move, "supercombo", spec["startup"], as_int(w["startup"]), clean(w["startup"]))
        rep.add("startup", move, "fat", spec["startup"], f["startup"], str(f["startup"]))
        rep.add("active", move, "capcom", spec["active"], sum(b - a + 1 for a, b in wins), c[2])
        rep.add("active", move, "supercombo", spec["active"], sum(hit_count_sum(w["active"])), clean(w["active"]))
        rep.add("active", move, "fat", spec["active"], sum(hit_count_sum(f["active"])), str(f["active"]))
        rep.add("block", move, "capcom", spec["block"], as_int(c[5]), c[5])
        rep.add("block", move, "supercombo", spec["block"], (ints(clean(w["blockAdv"])) or [None])[0], clean(w["blockAdv"]))
        rep.add("block", move, "fat", spec["block"], f["onBlock"], str(f["onBlock"]))
        if isinstance(spec["hit"], int):
            rep.add("hit", move, "capcom", spec["hit"], as_int(c[4]), c[4])
            rep.add("hit", move, "supercombo", spec["hit"], (ints(clean(w["hitAdv"])) or [None])[0], clean(w["hitAdv"]))
            rep.add("hit", move, "fat", spec["hit"], f["onHit"], str(f["onHit"]))

    # 2. Multi-hit meaties: per-hit windows, stun and total.
    for move, spec in inputs["multi"].items():
        inp, cap_name, fat_name = ALIASES[move]
        c, w, f = cap_row(cap_name), cargo_row(inp), fat_row(None, inp)
        if "fixed_block" in spec:
            rep.add("block", move, "capcom", spec["fixed_block"], as_int(c[5]), c[5])
            rep.add("block", move, "supercombo", spec["fixed_block"], (ints(clean(w["blockAdv"])) or [None])[0], clean(w["blockAdv"]))
            rep.add("block", move, "fat", spec["fixed_block"], f["onBlock"], str(f["onBlock"]))
            rep.add("startup", move, "capcom", spec["startup"], int(c[1]), c[1])
            rep.add("active", move, "capcom", spec["active"], sum(b - a + 1 for a, b in capcom_windows(c[2])), c[2])
            rep.add("active", move, "supercombo", spec["active"], sum(hit_count_sum(w["active"])), clean(w["active"]))
            continue
        mine_windows = [[h["first"], h["last"]] for h in spec["hits"]]
        for source, row, act, bs, hs, tot in (
                ("supercombo", w, clean(w["active"]), clean(w["blockstun"]), clean(w["hitstun"]), clean(w["total"])),
                ("fat", f, str(f["active"]), str(f["blockstun"]), str(f["hitstun"]), str(f["total"]))):
            start = as_int(row["startup"]) if source == "supercombo" else row["startup"]
            windows, at = [], start
            for n in hit_count_sum(act):
                windows.append([at, at + n - 1])
                at += n
            rep.add("hit_windows", move, source, mine_windows, windows, act)
            rep.add("blockstun_per_hit", move, source, [h["blockstun"] for h in spec["hits"]], ints(bs)[:len(spec["hits"])], bs)
            their_hs = ints(hs)[:len(spec["hits"])]
            rep.add("hitstun_last_hit", move, source, spec["hits"][-1]["hitstun"], their_hs[-1] if their_hs else None, hs)
            if their_hs and their_hs[0] != spec["hits"][0]["hitstun"]:
                rep.add("hitstun_hit1", move, source, spec["hits"][0]["hitstun"], their_hs[0], hs)
            rep.add("total", move, source, spec["total"], set(ints(tot)), tot)
        wins = capcom_windows(c[2])
        rep.add("total", move, "capcom", spec["total"], wins[-1][1] + int(c[3]), f"{c[1]} / {c[2]} / {c[3]}")

    # 3. Preparation lengths: whiff totals, dash, Denjin Charge, instant Drive Rush.
    for move, total in inputs["preparations"]["whiff"].items():
        inp, cap_name, fat_name = ALIASES[move]
        c, w, f = cap_row(cap_name), cargo_row(inp), fat_row(None, inp)
        extra = re.search(r"(\d+) frames? of recovery added when the attack misses", c[-1])
        derived = capcom_windows(c[2])[-1][1] + int(c[3]) + (int(extra.group(1)) if extra else 0)
        rep.add("whiff_total", move, "capcom", total, derived, f"{c[1]} / {c[2]} / {c[3]}" + (" / " + extra.group(0) if extra else ""))
        rep.add("whiff_total", move, "supercombo", total, set(ints(clean(w["total"]))), clean(w["total"]))
        rep.add("whiff_total", move, "fat", total, set(ints(f["total"])), str(f["total"]))
    dash = cap_row("Forward Dash")
    rep.add("dash", "forward dash", "capcom", inputs["preparations"]["dash"], ints(dash[3])[0], dash[3])
    rep.add("dash", "forward dash", "fat", inputs["preparations"]["dash"], int(fat_ryu["stats"]["fDash"]), fat_ryu["stats"]["fDash"])
    den = cap_row("Denjin Charge")
    rep.add("denjin_total", "Denjin Charge", "capcom", inputs["preparations"]["denjin"], ints(den[3])[0], den[3])
    rep.add("denjin_total", "Denjin Charge", "supercombo", inputs["preparations"]["denjin"], as_int(cargo_row("22P")["total"]), clean(cargo_row("22P")["total"]))
    pdr = cargo_row("MPMK~66")
    rep.add("instant_drive_rush", "Parry Drive Rush", "supercombo", inputs["preparations"]["instant_dr"], sum(ints(clean(pdr["startup"]))), clean(pdr["startup"]))

    # 4. Knockdown advantage of every ender.
    for ender in calc["enders"]:
        inp, name_part, field, fat_name, fat_field = ENDERS[ender["name"]]
        want = list(range(ender["kd_range"][0], ender["kd_range"][1] + 1)) if "kd_range" in ender else [ender["kd"]]
        w = cargo_row(inp, name_part)
        text = clean(w[field]) if w else ""
        found = set()
        for lo, hi in re.findall(r"\+(\d+)\s*~\s*\+?(\d+)", text):
            found.update(range(int(lo), int(hi) + 1))
        found.update(abs(n) for n in ints(text))
        ok = all(k in found for k in (want[0], want[-1])) if w else None
        rep.add("knockdown", ender["name"], "supercombo", want if len(want) > 1 else want[0],
                (want if len(want) > 1 else want[0]) if ok else (sorted(found) if w else None), text[:160])
        if fat_name:
            f = fat_row(fat_name)
            ftext = str(f[fat_field])
            rep.add("knockdown", ender["name"], "fat", want[0], set(abs(n) for n in ints(ftext)), ftext)

    counts = {}
    for row in rep.rows:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    manifest = snap.load_manifest()
    used = ["capcom/frame-ryu.rows.json", "supercombo/cargo/SF6_FrameData.Ryu.json", "fat/SF6FrameData.Ryu.json",
            "supercombo/revisions/Ryu_Data.json", "capcom/versions.json", "capcom/battle_change-20261013-en.txt",
            "capcom/battle_change-20261013-ja-jp.txt", "capcom/battle_change-20261013-en-ryu.txt"]
    revs = next(iter(json.loads(snap.read("supercombo/revisions/Ryu_Data.json"))["query"]["pages"].values()))["revisions"]
    versions = [v["value"].rstrip("/").split("/")[-1] for v in json.loads(snap.read("capcom/versions.json")) if v["value"]]
    out = {
        "checked_on": manifest["capcom/frame-ryu.rows.json"]["retrieved_on"],
        "core_inputs_sha256": json.loads((CORE / "CORE_LOCK.json").read_text())["files"]["ryu_inputs.json"]["sha256"],
        "patch_state": {
            "capcom_versions_newest_first": versions[:6],
            "latest_patch": versions[0] if versions else None,
            "latest_patch_ryu_page_http_status": manifest["capcom/battle_change-20261013-en-ryu.txt"].get("http_status"),
            "supercombo_ryu_data_latest_revid": revs[0]["revid"],
            "supercombo_ryu_data_latest_edit": revs[0]["timestamp"],
            "audited_revid_2026_09_28": 378774,
        },
        "counts": dict(sorted(counts.items())),
        "sources": {k: {f: manifest[k][f] for f in ("sha256", "retrieved_on", "url") if f in manifest[k]} for k in used},
        "rows": rep.rows,
    }
    (ROOT / "data").mkdir(exist_ok=True)
    (ROOT / "data" / "freshness.json").write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    print("comparisons:", sum(counts.values()), dict(sorted(counts.items())))
    for row in rep.rows:
        if row["status"] not in ("match",):
            print(f"  {row['status']:14} {row['kind']:18} {row['subject']:32} {row['source']:10} core={row['core']} "
                  f"source={row['source_value']} [{row.get('source_text', '')[:70]}]")
    return 1 if counts.get("MISMATCH") else 0


if __name__ == "__main__":
    sys.exit(main())
