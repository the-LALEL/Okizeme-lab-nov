"""Inch 3: the sealed core's inputs are current against today's sources.

The committed record (data/freshness.json) must be for the sealed inputs and must hold
no unexplained mismatch. When the raw source copies are present on this machine, the
comparison is re-run from them and must reproduce the committed record exactly.
"""
import json
import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
RECORD = ROOT / "data" / "freshness.json"
FAT_CLONE = pathlib.Path("/home/user/d4rkonion/fat")


def test_record_is_for_the_sealed_inputs_and_has_no_unexplained_mismatch():
    record = json.loads(RECORD.read_text())
    lock = json.loads((ROOT / "core" / "CORE_LOCK.json").read_text())
    assert record["core_inputs_sha256"] == lock["files"]["ryu_inputs.json"]["sha256"]
    assert record["counts"].get("MISMATCH", 0) == 0
    assert sum(record["counts"].values()) == len(record["rows"])
    # every difference carries the sentence that explains or names it
    for row in record["rows"]:
        if row["status"] in ("explained", "open_conflict"):
            assert row["note"]


def test_every_ender_and_every_solver_input_was_compared():
    record = json.loads(RECORD.read_text())
    inputs = json.loads((ROOT / "core" / "ryu_inputs.json").read_text())
    calc = json.loads((ROOT / "core" / "ryu_calc.json").read_text())
    compared = {(r["kind"], r["subject"]) for r in record["rows"]}
    for ender in calc["enders"]:
        assert ("knockdown", ender["name"]) in compared
    for move in inputs["single"]:
        for kind in ("startup", "active", "block"):
            assert (kind, move) in compared
    for move in inputs["preparations"]["whiff"]:
        assert ("whiff_total", move) in compared
    for move, spec in inputs["multi"].items():
        assert (("block" if "fixed_block" in spec else "hit_windows"), move) in compared


def test_rerun_from_raw_copies_reproduces_the_record():
    if not (ROOT / "sources" / "raw" / "capcom" / "frame-ryu.rows.json").exists() or not FAT_CLONE.exists():
        pytest.skip("raw source copies are not on this machine (they are never committed)")
    before = RECORD.read_bytes()
    proc = subprocess.run([sys.executable, str(ROOT / "lab" / "freshness.py"), "--fat", str(FAT_CLONE)],
                          capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout[-800:]
    assert RECORD.read_bytes() == before
