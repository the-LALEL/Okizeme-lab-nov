"""Inch 7, step 1: draft a wake-up profile for every character from one roster-wide data pull.

Script-first: every field is parsed from SuperCombo's database rows (saved snapshot). Nothing is
typed by hand. The draft is then cross-checked against Capcom's official frame pages and FAT by
lab/opponents_check.py, and against people by a verification wave; disagreements are recorded.

Usage: python lab/opponents.py
Writes: data/opponents/<slug>.json and data/opponents/_roster.json
"""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "lab"))
import snap  # noqa: E402
from freshness import clean, ints  # noqa: E402

WINDOW = re.compile(r"(\d+)\s*[-~]\s*(\d+)?\s*([A-Za-z][A-Za-z/ ]*?)\s*(?=\(|,|;|$)")


def windows(text):
    """'1-10 Full, 5-11 Projectile' -> [{'from': 1, 'to': 10, 'type': 'Full'}, ...]."""
    out = []
    for part in re.split(r",\s*(?=\d)", clean(text)):
        m = WINDOW.match(part.strip())
        if m:
            out.append({"from": int(m.group(1)), "to": int(m.group(2)) if m.group(2) else None,
                        "type": m.group(3).strip()})
    return out


def slug(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def resource(row):
    kind = clean(row["moveType"]).lower()
    name = clean(row["name"])
    if kind == "super":
        return "super"
    if name.startswith("OD ") or re.search(r"(PP|KK)\b", row["input"]):
        return "2 Drive bars"
    return "none"


def startup_frames(text):
    """'7' -> 7; '10+10' -> 20 (a lead-in plus the attack); '6+0' -> 6; '5(2)' -> 5; '' -> None."""
    m = re.match(r"\s*(\d+(?:\s*\+\s*\d+)*)", text)
    return sum(int(x) for x in re.findall(r"\d+", m.group(1))) if m else None


def move_ref(row):
    return {"input": row["input"], "name": clean(row["name"]), "move_id": row["moveId"],
            "startup_text": clean(row["startup"]), "startup": startup_frames(clean(row["startup"])),
            "invuln_text": clean(row["invuln"]), "armor_text": clean(row["armor"]),
            "block_text": clean(row["blockAdv"]), "total_text": clean(row["total"]), "resource": resource(row)}


def main():
    rows = json.loads(snap.read("supercombo/cargo/SF6_FrameData.roster.json"))
    stats = {r["chara"]: r for r in json.loads(snap.read("supercombo/cargo/SF6_CharacterData.roster.json"))}
    manifest = snap.load_manifest()["supercombo/cargo/SF6_FrameData.roster.json"]
    by_char = {}
    for r in rows:
        by_char.setdefault(r["chara"], []).append(r)

    out_dir = ROOT / "data" / "opponents"
    out_dir.mkdir(parents=True, exist_ok=True)
    roster = []
    for chara in sorted(by_char):
        st = stats.get(chara) or stats.get(chara.replace("_", " ")) or {}
        jump = ints(clean(st.get("jumpSpd", "")).split("(")[0])   # a bracketed second jump (High Jump) is not the normal jump
        profile = {
            "character": chara.replace("_", " "),
            "slug": slug(chara),
            "source": {"snapshot": "supercombo/cargo/SF6_FrameData.roster.json", "sha256": manifest["sha256"],
                       "retrieved_on": manifest["retrieved_on"]},
            "health": clean(st.get("hp", "")),
            "jump": {"text": clean(st.get("jumpSpd", "")), "prejump": jump[0] if jump else None,
                     "total": sum(jump) if jump else None},
            "backdash_total": clean(st.get("bwdDashSpd", "")),
            "forward_dash_total": clean(st.get("fwdDashSpd", "")),
            "throw_range": clean(st.get("throwRange", "")), "throw_hurtbox": clean(st.get("throwHurtbox", "")),
            "fastest_normals": [], "reversals": [], "throw_immune_from_frame_1": [], "armor": [],
            "command_grabs": [], "drive_reversal_on_wakeup": None,
        }
        normals = [(ints(clean(r["startup"]))[0], r["input"]) for r in by_char[chara]
                   if clean(r["moveType"]) == "ground_normal" and ints(clean(r["startup"]))]
        fastest = min(s for s, _ in normals)
        profile["fastest_normals"] = {"startup": fastest, "inputs": sorted(i for s, i in normals if s == fastest)}
        for r in by_char[chara]:
            kind = clean(r["moveType"]).lower()
            wins = windows(r["invuln"])
            ref = move_ref(r)
            if kind == "drive":
                if "(Recovery)" in ref["name"]:
                    profile["drive_reversal_on_wakeup"] = ref
                continue
            if kind not in ("special", "super"):
                continue
            from_one = [w for w in wins if w["from"] == 1]
            if any(w["type"] in ("Full", "Strike", "Strike/Throw") for w in from_one):
                profile["reversals"].append(ref)
            if any("Throw" in w["type"] or w["type"] == "Full" for w in from_one):
                profile["throw_immune_from_frame_1"].append(ref["input"] + " " + ref["name"])
            arm = ints(ref["armor_text"])
            if ref["armor_text"] and "Break" not in ref["armor_text"] and arm and arm[0] <= 3:
                profile["armor"].append(ref)
            if clean(r["guard"]) == "T":
                profile["command_grabs"].append(ref)
        profile["reversals"].sort(key=lambda m: (m["startup"] or 99, m["name"]))
        (out_dir / f"{profile['slug']}.json").write_text(json.dumps(profile, indent=1, ensure_ascii=False) + "\n")
        roster.append({"character": profile["character"], "slug": profile["slug"]})
        fast = min((m["startup"] for m in profile["reversals"] if m["resource"] == "2 Drive bars" and m["startup"]), default=None)
        print(f"{profile['character']:10} jump {profile['jump']['text']:8} bd {profile['backdash_total']:3} "
              f"fastest {fastest}f  reversals {len(profile['reversals'])} (fastest OD {fast}) "
              f"armor {len(profile['armor'])} grabs {len(profile['command_grabs'])}")
    (out_dir / "_roster.json").write_text(json.dumps(roster, indent=1) + "\n")
    print(len(roster), "profiles written")


if __name__ == "__main__":
    main()
