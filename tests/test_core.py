"""Inch 1: the sealed core runs here and gives the same answer twice.

Checks, all against the world rather than argued:
  1. every core file still has the hash recorded in core/CORE_LOCK.json (the seal);
  2. two solver runs are byte-identical and match the locked output hashes;
  3. both published anchors appear in the output;
  4. every output row reproduces from the inputs with a separately written
     implementation of the meaty formula (core/method.md), not the solver's own code.
"""
import hashlib
import json
import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
CORE = ROOT / "core"
LOCK = json.loads((CORE / "CORE_LOCK.json").read_text())


def sha(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def run_solver(out_dir):
    prefix = out_dir / "Ryu_frame_kills"
    proc = subprocess.run(
        [sys.executable, str(CORE / "fk_calc.py"), str(CORE / "ryu_inputs.json"),
         str(CORE / "ryu_calc.json"), "--out", str(prefix)],
        capture_output=True, text=True, check=True)
    return prefix, proc.stdout


@pytest.fixture(scope="module")
def runs(tmp_path_factory):
    a, out_a = run_solver(tmp_path_factory.mktemp("run_a"))
    b, out_b = run_solver(tmp_path_factory.mktemp("run_b"))
    return a, b, out_a, out_b


def test_core_files_are_sealed():
    for name, meta in LOCK["files"].items():
        assert sha(CORE / name) == meta["sha256"], f"core/{name} differs from the lock"


def test_two_runs_are_byte_identical_and_match_the_lock(runs):
    a, b, out_a, out_b = runs
    exp = LOCK["expected_output"]
    for ext, key in ((".json", "json_file_sha256"), (".md", "md_file_sha256")):
        assert sha(str(a) + ext) == sha(str(b) + ext) == exp[key]
    result = json.loads(pathlib.Path(str(a) + ".json").read_text())
    assert result["output_sha256"] == exp["output_sha256"]
    assert len(result["enders"]) == exp["enders"]
    assert sum(len(e["rows"]) for e in result["enders"]) == exp["rows"]
    assert sum(1 for e in result["enders"] if not e["rows"]) == exp["enders_without_rows"]
    assert "WARNING" not in out_a + out_b, "a published multi-hit check failed"


def test_published_anchors_reproduce(runs):
    result = json.loads(pathlib.Path(str(runs[0]) + ".json").read_text())
    by_name = {e["name"]: e for e in result["enders"]}
    for anchor in LOCK["anchors"]:
        rows = [r for r in by_name[anchor["ender"]]["rows"] if r["seq"] == anchor["seq"]]
        assert len(rows) == 1, f"anchor row missing: {anchor['ender']} > {anchor['seq']}"
        assert rows[0]["block"] == [anchor["block"], anchor["block"]]
        if "hit" in anchor:
            assert rows[0]["hit"] == [anchor["hit"], anchor["hit"]]


def independent_block(inputs, prep, follow_up, kd):
    """Block advantage from core/method.md, written without reference to fk_calc.evaluate."""
    p = inputs["preparations"]
    cost = dict(p["whiff"])
    cost.update({"dash": p["dash"], "Denjin": p["denjin"], "instant DR": p["instant_dr"]})
    spent = sum(cost[step] for step in prep)
    remaining = kd - spent
    bonus = 4 if prep and prep[-1] == "instant DR" else 0
    if follow_up in inputs["single"]:
        move = inputs["single"][follow_up]
        contact = remaining - move["startup"] + 2
        assert 1 <= contact <= move["active"], "not a true meaty"
        return spent, move["block"] + (contact - 1) + bonus
    move = inputs["multi"][follow_up]
    if "fixed_block" in move:
        contact = remaining - move["startup"] + 2
        assert 1 <= contact <= move["active"], "not a true meaty"
        return spent, move["fixed_block"]
    wake_frame = remaining + 1
    live = [h for h in move["hits"] if h["last"] >= wake_frame]
    assert live and live[0]["first"] <= wake_frame, "not a true meaty"
    last = live[-1]
    frames_after = move["total"] - max(last["first"], wake_frame)
    return spent, last["blockstun"] - frames_after - 1 + bonus


def test_every_row_reproduces_from_the_inputs(runs):
    inputs = json.loads((CORE / "ryu_inputs.json").read_text())
    result = json.loads(pathlib.Path(str(runs[0]) + ".json").read_text())
    checked = 0
    for ender in result["enders"]:
        kds = [ender["kd"]] if isinstance(ender["kd"], int) else range(ender["kd"][0], ender["kd"][1] + 1)
        for row in ender["rows"]:
            values = []
            for kd in kds:
                spent, block = independent_block(inputs, row["prep"], row["follow_up"], kd)
                assert spent == row["frames_spent"]
                values.append(block)
            assert [min(values), max(values)] == row["block"], f"{ender['name']} > {row['seq']}"
            checked += 1
    assert checked == LOCK["expected_output"]["rows"]
