"""Build the site from the sealed core's output.

This layer sits outside core/ and never edits it. It runs the solver as a
subprocess (once for the 40 named enders, once for every knockdown number from
1 to 110), checks the named run against the lock, then SELECTS and LABELS rows
for display. It does no frame arithmetic: every number on the page is a number
the solver printed.

Usage: python lab/build_site.py
Writes: out/ (scratch solver output) and site/index.html
"""
import hashlib
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

K_MIN, K_MAX = 1, 110  # every knockdown number the frame meter could plausibly show

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


def sha(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def run_solver(calc_path, prefix):
    """Run the sealed solver. Reuses a previous output only when solver, inputs and calc are unchanged."""
    stamp = pathlib.Path(str(prefix) + ".stamp")
    key = "|".join(sha(p) for p in (CORE / "fk_calc.py", CORE / "ryu_inputs.json", calc_path))
    out_json = pathlib.Path(str(prefix) + ".json")
    if not (out_json.exists() and stamp.exists() and stamp.read_text() == key):
        subprocess.run([sys.executable, str(CORE / "fk_calc.py"), str(CORE / "ryu_inputs.json"),
                        str(calc_path), "--out", str(prefix)], check=True, capture_output=True, text=True)
        stamp.write_text(key)
    return json.loads(out_json.read_text())


def run_core():
    lock = json.loads((CORE / "CORE_LOCK.json").read_text())
    OUT.mkdir(exist_ok=True)
    named = run_solver(CORE / "ryu_calc.json", OUT / "Ryu_frame_kills")
    if named["output_sha256"] != lock["expected_output"]["output_sha256"]:
        raise SystemExit("solver output differs from core/CORE_LOCK.json; refusing to build")
    # The same solver, asked about every knockdown number instead of the named enders.
    calc_all = {"prevalence_source": "none: every knockdown number", "move_flags": json.loads(
        (CORE / "ryu_calc.json").read_text())["move_flags"],
        "enders": [{"name": f"Knockdown +{k}", "kd": k, "combo_count": None} for k in range(K_MIN, K_MAX + 1)]}
    calc_path = OUT / "calc_all_k.json"
    calc_path.write_text(json.dumps(calc_all, indent=1, sort_keys=True) + "\n")
    every_k = run_solver(calc_path, OUT / "all_k")
    return named, every_k, lock


def load_freshness(lock):
    """The freshness check (lab/freshness.py) is optional input: without it the page says 'pending'."""
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


CONTACT_ACTIVE = re.compile(r"^active (\d+)(?:-(\d+))?/(\d+)")
CONTACT_FRAME = re.compile(r"^move frame (\d+)(?:-(\d+))? on wake-up")


def contact_for(text):
    m = CONTACT_ACTIVE.match(text)
    if m:
        return {"kind": "active", "first": int(m.group(1)), "last": int(m.group(2) or m.group(1)),
                "of": int(m.group(3)), "text": text}
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


def slug(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def shape_rows(solver_rows, move_flags, prep_disputes, published):
    rows = []
    for row in solver_rows:
        dispute = None
        if "conflict" in row["flags"]:
            flag = move_flags[row["follow_up"]]
            dispute = flag if isinstance(flag, str) else flag["text"]
        rows.append({
            "seq": row["seq"],
            "prep": row["prep"],
            "meaty": row["follow_up"],
            "block": row["block"],
            "hit": row["hit"],
            "drive": row["drive"],
            "frames_spent": row["frames_spent"],
            "actions": row["actions"],
            "contact": contact_for(row["contact"]),
            "flags": [f for f in row["flags"] if f in FLAG_TEXT],
            "dispute": dispute,
            "prep_dispute": next((prep_disputes[p] for p in row["prep"] if p in prep_disputes), None),
            "published": row["seq"] in published,
        })
    return rows


def tiers_for(rows):
    # Selection only: the solver already ordered rows by block advantage, then Drive cost,
    # then fewer actions. A tier's pick is its first row; the sturdier pick is its first
    # row that is not on a last active frame and rests on no disputed number.
    tiers = []
    for drive in sorted({r["drive"] for r in rows}, key=drive_order):
        in_tier = [i for i, r in enumerate(rows) if r["drive"] == drive]
        top = in_tier[0]
        sturdy = next((i for i in in_tier if not {"last active frame", "conflict"} & set(rows[i]["flags"])
                       and not rows[i]["prep_dispute"]), None)
        tiers.append({"drive": drive, "label": drive_label(drive), "pick": top,
                      "sturdier": sturdy if sturdy != top else None, "count": len(in_tier)})
    return tiers


def build_card(ender, move_flags, prep_disputes, published=frozenset(), named=True):
    rows = shape_rows(ender["rows"], move_flags, prep_disputes, published)
    card = {
        "id": slug(ender["name"]) if named else f"k{ender['kd']}",
        "ender": ender["name"],
        "named": named,
        "kd": ender["kd"],
        "tiers": tiers_for(rows),
        "rows": rows,
    }
    if named:
        card["prevalence"] = {"rank": ender["prevalence_rank"], "combo_count": ender["combo_count"]}
        card["reach_note"] = ender["reach"]
        # For a knockdown that varies with spacing, the solver also names the top row at each exact value.
        card["per_kd"] = [{"kd": x["kd"], "seq": x["row"]["seq"] if x["row"] else None,
                           "block": x["row"]["block"] if x["row"] else None} for x in ender["per_kd"]]
    return card


def build_data(named, every_k, lock):
    freshness, prep_disputes = load_freshness(lock)
    inputs = json.loads((CORE / "ryu_inputs.json").read_text())
    p = inputs["preparations"]
    prep_table = {name: {"kind": "whiff", "label": "whiff " + name, "frames": frames} for name, frames in p["whiff"].items()}
    prep_table["dash"] = {"kind": "move", "label": "dash", "frames": p["dash"]}
    prep_table["instant DR"] = {"kind": "drive", "label": "Drive Rush", "frames": p["instant_dr"]}
    prep_table["Denjin"] = {"kind": "stock", "label": "Denjin Charge", "frames": p["denjin"]}

    anchors = {}
    for a in lock["anchors"]:
        anchors.setdefault(a["ender"], set()).add(a["seq"])
    enders = [build_card(e, named["move_flags"], prep_disputes, frozenset(anchors.get(e["name"], ())))
              for e in named["enders"]]
    by_k = sorted((build_card(e, every_k["move_flags"], prep_disputes, named=False) for e in every_k["enders"]),
                  key=lambda c: c["kd"])
    return {
        "enders": enders,
        "by_k": by_k,
        "k_range": [K_MIN, K_MAX],
        "preps": prep_table,
        "status": {"inputs_verified_on": lock["inputs_verified_on"],
                   "patch_state": lock["patch_state_at_verification"], "freshness": freshness},
        "ranking_rule": "Ranked by block advantage within each Drive cost. This is a stand-in until "
                        "opponent data exists; the real ranking is what each pick beats.",
        "no_rows_text": "No modelled strike can be timed to meet wake-up from this knockdown with at least +0 on block.",
        "no_rows_range_text": "No single timing works at every value in this range. Open the exact value below.",
        "flag_text": FLAG_TEXT,
        "not_yet": NOT_YET,
        "prevalence_source": named["prevalence_source"],
        "search": {"exhaustive": named["options"]["exhaustive"] and every_k["options"]["exhaustive"],
                   "depth": every_k["options"]["search_depth"], "timings": every_k["options"]["signatures"],
                   "meaties": len(named["options"]["meaties"])},
        "provenance": {"output": named["output_sha256"][:12], "every_k_output": every_k["output_sha256"][:12],
                       "inputs": named["inputs_sha256"][:12], "calc": named["calc_sha256"][:12]},
    }


def render(data):
    blob = json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    page = TEMPLATE.read_text(encoding="utf-8")
    if page.count("__LAB_JSON__") != 1:
        raise SystemExit("template must contain __LAB_JSON__ exactly once")
    return page.replace("__LAB_JSON__", blob)


def main():
    named, every_k, lock = run_core()
    data = build_data(named, every_k, lock)
    SITE.mkdir(exist_ok=True)
    html = render(data)
    (SITE / "index.html").write_text(html, encoding="utf-8")
    empty = [c["kd"] for c in data["by_k"] if not c["rows"]]
    print(f"site/index.html: {len(data['enders'])} named enders, knockdown numbers {K_MIN}-{K_MAX} "
          f"({len(empty)} with no qualifying strike: {empty}), {len(html) // 1024} KB, "
          f"solver output {data['provenance']['output']} / {data['provenance']['every_k_output']}")


if __name__ == "__main__":
    main()
