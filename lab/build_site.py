"""Build the site from the sealed core's output.

This layer sits outside core/ and never edits it. It runs the solver as a
subprocess, checks the output against the lock, then SELECTS and LABELS rows
for display. It does no frame arithmetic: every number on the page is a number
the solver printed.

Usage: python lab/build_site.py
Writes: out/Ryu_frame_kills.{json,md} (scratch) and site/index.html
"""
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
CORE = ROOT / "core"
OUT = ROOT / "out"
SITE = ROOT / "site"
TEMPLATE = ROOT / "lab" / "templates" / "page.html"

# The one card built so far. Later inches replace this with every situation.
FIRST_CARD = "LK Tatsu"

FLAG_TEXT = {
    "ceiling": "The most this move can ever give, at any timing.",
    "last active frame": "Lands on the move's last active frame. If any number here is off by one, it whiffs.",
    "conflict": "Rests on a number that sources disagree about.",
}

NOT_YET = [
    {"title": "Against your opponent",
     "text": "Which of their wake-up options each pick beats and which it loses to."},
    {"title": "Reach",
     "text": "Whether the pick still connects after a back rise. Frame data cannot show this."},
    {"title": "Throws, shimmies and safe jumps",
     "text": "Only meaty strikes are computed so far."},
]


def run_core():
    lock = json.loads((CORE / "CORE_LOCK.json").read_text())
    OUT.mkdir(exist_ok=True)
    prefix = OUT / "Ryu_frame_kills"
    subprocess.run(
        [sys.executable, str(CORE / "fk_calc.py"), str(CORE / "ryu_inputs.json"),
         str(CORE / "ryu_calc.json"), "--out", str(prefix)],
        check=True, capture_output=True, text=True)
    result = json.loads(pathlib.Path(str(prefix) + ".json").read_text())
    if result["output_sha256"] != lock["expected_output"]["output_sha256"]:
        raise SystemExit("solver output differs from core/CORE_LOCK.json; refusing to build")
    return result, lock


def steps_for(row, prep_cost):
    steps = []
    for name in row["prep"]:
        if name == "dash":
            steps.append({"kind": "move", "label": "dash", "frames": prep_cost[name]})
        elif name == "instant DR":
            steps.append({"kind": "drive", "label": "Drive Rush", "frames": prep_cost[name]})
        elif name == "Denjin":
            steps.append({"kind": "stock", "label": "Denjin Charge", "frames": prep_cost[name]})
        else:
            steps.append({"kind": "whiff", "label": "whiff " + name, "frames": prep_cost[name]})
    steps.append({"kind": "meaty", "label": row["follow_up"], "frames": None})
    return steps


CONTACT_ACTIVE = re.compile(r"^active (\d+)(?:-(\d+))?/(\d+)")
CONTACT_FRAME = re.compile(r"^move frame (\d+)(?:-(\d+))? on wake-up")


def contact_for(text):
    m = CONTACT_ACTIVE.match(text)
    if m:
        first, last, of = int(m.group(1)), int(m.group(2) or m.group(1)), int(m.group(3))
        return {"kind": "active", "first": first, "last": last, "of": of, "text": text}
    m = CONTACT_FRAME.match(text)
    if m:
        return {"kind": "frame", "first": int(m.group(1)), "last": int(m.group(2) or m.group(1)),
                "of": None, "text": text}
    return {"kind": "other", "first": None, "last": None, "of": None, "text": text}


def drive_order(drive):
    return (int(drive.split()[0]), "stock" in drive)


def drive_label(drive):
    bars = int(drive.split()[0])
    label = "No Drive" if bars == 0 else ("1 Drive bar" if bars == 1 else f"{bars} Drive bars")
    return label + (" and a Denjin stock" if "stock" in drive else "")


def load_freshness(lock):
    """The freshness check (lab/freshness.py) is optional input: without it the card says 'pending'."""
    path = ROOT / "data" / "freshness.json"
    if not path.exists():
        return {"state": "pending"}, {}
    fresh = json.loads(path.read_text())
    if fresh["core_inputs_sha256"] != lock["files"]["ryu_inputs.json"]["sha256"]:
        raise SystemExit("data/freshness.json was computed for different inputs; re-run lab/freshness.py")
    counts = fresh["counts"]
    latest = fresh["patch_state"]["latest_patch"]
    status = {
        "state": "checked",
        "checked_on": fresh["checked_on"],
        "comparisons": sum(counts.values()),
        "match": counts.get("match", 0),
        "explained": counts.get("explained", 0),
        "open_conflicts": counts.get("open_conflict", 0),
        "unexplained": counts.get("MISMATCH", 0),
        "latest_patch": f"{latest[:4]}-{latest[4:6]}-{latest[6:]}",
        "latest_patch_touched_ryu": fresh["patch_state"]["latest_patch_ryu_page_http_status"] == 200,
    }
    # A disputed preparation length puts every row that uses that preparation in doubt.
    prep_disputes = {r["subject"]: r["note"] for r in fresh["rows"]
                     if r["kind"] == "whiff_total" and r["status"] == "open_conflict"}
    return status, prep_disputes


def build_card(result, lock, ender_name):
    freshness, prep_disputes = load_freshness(lock)
    inputs = json.loads((CORE / "ryu_inputs.json").read_text())
    p = inputs["preparations"]
    prep_cost = dict(p["whiff"])
    prep_cost.update({"dash": p["dash"], "Denjin": p["denjin"], "instant DR": p["instant_dr"]})

    ender = next(e for e in result["enders"] if e["name"] == ender_name)
    published = {a["seq"] for a in lock["anchors"] if a["ender"] == ender_name}

    rows = []
    for row in ender["rows"]:
        dispute = None
        if "conflict" in row["flags"]:
            flag = result["move_flags"][row["follow_up"]]
            dispute = flag if isinstance(flag, str) else flag["text"]
        rows.append({
            "seq": row["seq"],
            "steps": steps_for(row, prep_cost),
            "block": row["block"],
            "hit": row["hit"],
            "drive": row["drive"],
            "frames_spent": row["frames_spent"],
            "actions": row["actions"],
            "contact": contact_for(row["contact"]),
            "flags": [f for f in row["flags"] if f in FLAG_TEXT],
            "equivalents": next((f for f in row["flags"] if f not in FLAG_TEXT), None),
            "dispute": dispute,
            "prep_dispute": next((prep_disputes[p] for p in row["prep"] if p in prep_disputes), None),
            "published": row["seq"] in published,
        })

    # Selection only: the solver already ordered rows by block advantage, then Drive cost,
    # then fewer actions. A tier's pick is its first row; the sturdier pick is its first
    # row that is neither on a last active frame nor resting on a disputed number.
    tiers = []
    for drive in sorted({r["drive"] for r in rows}, key=drive_order):
        in_tier = [i for i, r in enumerate(rows) if r["drive"] == drive]
        top = in_tier[0]
        sturdy = next((i for i in in_tier if not {"last active frame", "conflict"} & set(rows[i]["flags"])
                       and not rows[i]["prep_dispute"]), None)
        tiers.append({"drive": drive, "label": drive_label(drive), "pick": top,
                      "sturdier": sturdy if sturdy != top else None, "count": len(in_tier)})

    return {
        "ender": ender["name"],
        "kd": ender["kd"],
        "prevalence": {"rank": ender["prevalence_rank"], "combo_count": ender["combo_count"],
                       "source": result["prevalence_source"]},
        "status": {"inputs_verified_on": lock["inputs_verified_on"],
                   "patch_state": lock["patch_state_at_verification"],
                   "freshness": freshness},
        "ranking_rule": "Ranked by block advantage within each Drive cost. This is a stand-in until "
                        "opponent data exists; the real ranking is what each pick beats.",
        "tiers": tiers,
        "rows": rows,
        "flag_text": FLAG_TEXT,
        "not_yet": NOT_YET,
        "search": {"exhaustive": result["options"]["exhaustive"], "depth": result["options"]["search_depth"],
                   "timings": result["options"]["signatures"], "meaties": len(result["options"]["meaties"])},
        "provenance": {"output": result["output_sha256"][:12], "inputs": result["inputs_sha256"][:12],
                       "calc": result["calc_sha256"][:12]},
    }


def render(card):
    data = json.dumps(card, sort_keys=True, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    page = TEMPLATE.read_text(encoding="utf-8")
    if page.count("__CARD_JSON__") != 1:
        raise SystemExit("template must contain __CARD_JSON__ exactly once")
    return page.replace("__CARD_JSON__", data)


def main():
    result, lock = run_core()
    card = build_card(result, lock, FIRST_CARD)
    SITE.mkdir(exist_ok=True)
    (SITE / "index.html").write_text(render(card), encoding="utf-8")
    print(f"site/index.html: {card['ender']} (KD +{card['kd']}), {len(card['rows'])} rows, "
          f"{len(card['tiers'])} Drive tiers, solver output {card['provenance']['output']}")


if __name__ == "__main__":
    main()
