"""Inches 2 and 4: every card reads as an answer, and every number on it is the solver's.

  1. the build is deterministic (two builds, identical bytes);
  2. every row of every named-ender card equals the solver's row, field by field;
  3. every knockdown number from 1 to 110 has a card whose rows equal a direct solver run,
     and for each named ender with a single knockdown value the two runs agree;
  4. each Drive tier's pick and sturdier pick obey the stated selection rule;
  5. the page script contains no frame arithmetic on the data (it only formats and looks up).
"""
import json
import pathlib
import re
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "lab"))
import extensions  # noqa: E402

PAGE = ROOT / "site" / "index.html"
ROW_FIELDS = ("seq", "block", "hit", "drive", "frames_spent", "actions")


def build():
    subprocess.run([sys.executable, str(ROOT / "lab" / "build_site.py")], check=True, capture_output=True, text=True)
    return PAGE.read_bytes()


@pytest.fixture(scope="module")
def built():
    first = build()
    second = build()
    return first, second


@pytest.fixture(scope="module")
def lab(built):
    m = re.search(r'<script type="application/json" id="lab">(.*?)</script>', built[0].decode("utf-8"), re.S)
    assert m, "embedded data not found"
    return json.loads(m.group(1).replace("<\\/", "</"))


def solver(name):
    return json.loads((ROOT / "out" / f"{name}.json").read_text())


def assert_rows_equal(card, ender):
    assert card["kd"] == ender["kd"]
    assert len(card["rows"]) == len(ender["rows"])
    for shown, src in zip(card["rows"], ender["rows"]):
        for field in ROW_FIELDS:
            assert shown[field] == src[field], f"{ender['name']} > {src['seq']}: {field}"
        assert shown["contact"]["text"] == src["contact"]
        assert shown["prep"] == src["prep"] and shown["meaty"] == src["follow_up"]
        assert set(shown["flags"]) <= set(src["flags"])


def test_build_is_deterministic(built):
    assert built[0] == built[1]


def test_every_named_card_equals_the_solver(lab):
    result = solver("Ryu_frame_kills")
    assert [c["ender"] for c in lab["enders"]] == [e["name"] for e in result["enders"]]
    for card, ender in zip(lab["enders"], result["enders"]):
        assert_rows_equal(card, ender)
    assert lab["provenance"]["output"] == result["output_sha256"][:12]
    assert len({c["id"] for c in lab["enders"]}) == len(lab["enders"])


def test_every_knockdown_number_has_an_answer(lab):
    result = solver("all_k")
    lo, hi = lab["k_range"]
    solver_by_k = {e["kd"]: e for e in result["enders"]}
    assert [c["kd"] for c in lab["by_k"]] == list(range(lo, hi + 1)) == sorted(solver_by_k)
    assert result["options"]["exhaustive"] is True
    for card in lab["by_k"]:
        ender = solver_by_k[card["kd"]]
        assert card["id"] == f"k{card['kd']}"
        assert_rows_equal(card, ender)
        assert bool(card["tiers"]) == bool(card["rows"])
    assert lab["no_rows_text"]


def test_number_cards_agree_with_named_cards(lab):
    by_k = {c["kd"]: c for c in lab["by_k"]}
    checked = 0
    for card in lab["enders"]:
        if not isinstance(card["kd"], int):
            continue
        twin = by_k[card["kd"]]
        assert [[r[f] for f in ROW_FIELDS] for r in card["rows"]] == [[r[f] for f in ROW_FIELDS] for r in twin["rows"]], card["ender"]
        checked += 1
    assert checked >= 30
    # a knockdown range's per-value table points at the same top row as that number's own card
    for card in lab["enders"]:
        for x in card["per_kd"]:
            top = by_k[x["kd"]]["rows"]
            assert (x["seq"], x["block"]) == ((top[0]["seq"], top[0]["block"]) if top else (None, None))


def test_tier_picks_obey_the_stated_rule(lab):
    for card in lab["enders"] + lab["by_k"]:
        rows = card["rows"]
        assert sorted({r["drive"] for r in rows}) == sorted(t["drive"] for t in card["tiers"])
        for tier in card["tiers"]:
            in_tier = [i for i, r in enumerate(rows) if r["drive"] == tier["drive"]]
            assert tier["pick"] == in_tier[0]
            assert tier["count"] == len(in_tier)
            sturdy = next((i for i in in_tier if not {"last active frame", "conflict"} & set(rows[i]["flags"])
                           and not rows[i]["prep_dispute"]), None)
            assert tier["sturdier"] == (sturdy if sturdy != tier["pick"] else None)
            # the pick is never beaten on block advantage inside its own tier
            assert all(rows[tier["pick"]]["block"][0] >= rows[i]["block"][0] for i in in_tier)


def test_disputed_preparations_are_marked(lab):
    fresh = json.loads((ROOT / "data" / "freshness.json").read_text())
    disputed = {r["subject"] for r in fresh["rows"] if r["kind"] == "whiff_total" and r["status"] == "open_conflict"}
    assert disputed, "expected at least the known 4HK whiff-length disagreement"
    for card in lab["enders"] + lab["by_k"]:
        for row in card["rows"]:
            assert bool(row["prep_dispute"]) == bool(disputed & set(row["prep"])), row["seq"]


def test_page_script_does_no_frame_arithmetic(built):
    script = re.findall(r"<script>(.*?)</script>", built[0].decode("utf-8"), re.S)[-1]
    # No data field is ever added to, subtracted from or multiplied with another value.
    for field in ("block", "hit", "frames_spent", "kd", "first", "last", "of", "frames"):
        assert not re.search(rf"\.{field}(\[\d\])?\s*[-+*/]\s*(?![\"'])[\w(]", script), f"arithmetic on .{field}"


def test_throw_timings_on_cards_are_the_extension_rows(lab):
    inputs = json.loads((ROOT / "core" / "ryu_inputs.json").read_text())
    sigs = extensions.prep_signatures(inputs, lab["k_range"][1])
    seen = 0
    for card in lab["enders"] + lab["by_k"]:
        if not isinstance(card["kd"], int):
            assert card["throws"] is None
            continue
        want = extensions.throw_rows(card["kd"], sigs)
        got = card["throws"]["rows"]
        assert [(r["prep"], r["remaining"], r["connects_on_wake_frame"], r["drive"], r["flags"]) for r in got] == \
            [(r["prep"], r["remaining"], r["connects_on_wake_frame"], r["drive"], r["flags"]) for r in want]
        for tier in card["throws"]["tiers"]:
            in_tier = [i for i, r in enumerate(got) if r["drive"] == tier["drive"]]
            assert tier["pick"] == in_tier[0] and tier["count"] == len(in_tier)
        seen += bool(got)
    assert seen > 100


def test_late_strikes_and_block_numbers_come_from_the_extension_layer(lab):
    inputs = json.loads((ROOT / "core" / "ryu_inputs.json").read_text())
    totals = json.loads((ROOT / "data" / "ryu" / "meaty_totals.json").read_text())
    sigs = extensions.prep_signatures(inputs, lab["k_range"][1])
    shown = 0
    for card in lab["enders"] + lab["by_k"]:
        kd_low = card["kd"] if isinstance(card["kd"], int) else card["kd"][0]
        for row in card["rows"]:
            assert row["blocks_from"] == extensions.blocks_reversal_from(totals[row["meaty"]]["total"], kd_low - row["frames_spent"])
        if not isinstance(card["kd"], int):
            assert card["late"] is None
            continue
        want = extensions.late_meaty_rows(card["kd"], sigs, inputs)
        got = card["late"]["rows"]
        assert [(r["prep"], r["meaty"], r["block"][0], r["first_active_wake_frame"]) for r in got] == \
            [(r["prep"], r["meaty"], r["block"], r["first_active_wake_frame"]) for r in want]
        best_true = {}
        for r in card["rows"]:
            best_true.setdefault(r["drive"], r["block"][0])
        for tier in card["late"]["tiers"]:
            pick = got[tier["pick"]]
            assert pick["drive"] == tier["drive"]
            assert tier["drive"] not in best_true or pick["block"][0] > best_true[tier["drive"]]
            shown += 1
    assert shown > 0
    # forward throw (+17): the late 6HP (+3 on block) beats every true meaty available without Drive
    k17 = next(c for c in lab["by_k"] if c["kd"] == 17)
    top = k17["late"]["rows"][k17["late"]["tiers"][0]["pick"]]
    assert (top["prep"], top["meaty"], top["block"][0]) == ([], "6HP", 3)


def test_opponent_profiles_on_the_page_are_the_data_files(lab):
    folder = ROOT / "data" / "opponents"
    roster = json.loads((folder / "_roster.json").read_text())
    check = json.loads((folder / "_capcom_check.json").read_text())["characters"]
    assert [o["slug"] for o in lab["opponents"]] == [e["slug"] for e in roster] and len(roster) == 32
    for shown in lab["opponents"]:
        prof = json.loads((folder / f"{shown['slug']}.json").read_text())
        assert [(m["name"], m["startup"], m["invuln"]) for m in shown["reversals"]] == \
            [(m["name"], m["startup"], m["invuln_text"]) for m in prof["reversals"]]
        differs = len(check[shown["slug"]]["capcom_only"]) + len(check[shown["slug"]]["draft_only"])
        assert shown["status"] == ("matches Capcom" if differs == 0 else "under review")
    ken = next(o for o in lab["opponents"] if o["slug"] == "ken")
    assert ken["status"] == "matches Capcom" and any(m["name"] == "OD Shoryuken" and m["startup"] == 6 for m in ken["reversals"])
