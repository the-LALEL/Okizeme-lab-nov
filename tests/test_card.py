"""Inch 2: one real card reads as an answer, and every number on it is the solver's.

  1. the build is deterministic (two builds, identical bytes);
  2. every row embedded in the page equals the solver's row for that ender, field by field;
  3. each Drive tier's pick and sturdier pick obey the stated selection rule;
  4. the page script contains no frame arithmetic on the data (it only formats and looks up).
"""
import json
import pathlib
import re
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
PAGE = ROOT / "site" / "index.html"


def build():
    subprocess.run([sys.executable, str(ROOT / "lab" / "build_site.py")], check=True, capture_output=True, text=True)
    return PAGE.read_bytes()


@pytest.fixture(scope="module")
def built():
    first = build()
    second = build()
    return first, second


def embedded_card(page_bytes):
    m = re.search(r'<script type="application/json" id="card">(.*?)</script>', page_bytes.decode("utf-8"), re.S)
    assert m, "embedded card data not found"
    return json.loads(m.group(1).replace("<\\/", "</"))


def solver_ender(name):
    result = json.loads((ROOT / "out" / "Ryu_frame_kills.json").read_text())
    return next(e for e in result["enders"] if e["name"] == name), result


def test_build_is_deterministic(built):
    assert built[0] == built[1]


def test_every_row_equals_the_solver_row(built):
    card = embedded_card(built[0])
    ender, result = solver_ender(card["ender"])
    assert card["kd"] == ender["kd"]
    assert len(card["rows"]) == len(ender["rows"])
    for shown, src in zip(card["rows"], ender["rows"]):
        for field in ("seq", "block", "hit", "drive", "frames_spent", "actions"):
            assert shown[field] == src[field], f"{src['seq']}: {field}"
        assert shown["contact"]["text"] == src["contact"]
        assert [s["label"].replace("whiff ", "") for s in shown["steps"][:-1]] == \
            [{"instant DR": "Drive Rush", "Denjin": "Denjin Charge"}.get(p, p) for p in src["prep"]]
        assert shown["steps"][-1]["label"] == src["follow_up"]
        assert set(shown["flags"]) <= set(src["flags"])
    assert card["provenance"]["output"] == result["output_sha256"][:12]


def test_tier_picks_obey_the_stated_rule(built):
    card = embedded_card(built[0])
    rows = card["rows"]
    assert sorted({r["drive"] for r in rows}) == sorted(t["drive"] for t in card["tiers"])
    for tier in card["tiers"]:
        in_tier = [i for i, r in enumerate(rows) if r["drive"] == tier["drive"]]
        assert tier["pick"] == in_tier[0]
        assert tier["count"] == len(in_tier)
        sturdy = next((i for i in in_tier if not {"last active frame", "conflict"} & set(rows[i]["flags"])), None)
        assert tier["sturdier"] == (sturdy if sturdy != tier["pick"] else None)
        # the pick is never beaten on block advantage inside its own tier
        assert all(rows[tier["pick"]]["block"][0] >= rows[i]["block"][0] for i in in_tier)


def test_page_script_does_no_frame_arithmetic(built):
    script = re.findall(r"<script>(.*?)</script>", built[0].decode("utf-8"), re.S)[-1]
    # No data field is ever added to, subtracted from or multiplied with another value.
    for field in ("block", "hit", "frames_spent", "kd", "first", "last", "of", "frames"):
        assert not re.search(rf"\.{field}(\[\d\])?\s*[-+*/]\s*(?![\"'])[\w(]", script), f"arithmetic on .{field}"
