"""Inch 5: option classes outside the sealed core.

  1. the extension layer enumerates exactly the preparations the core does: same count, and
     every row the core prints uses the same representative preparation;
  2. meaty throw timing reproduces the audited convention (+5 connects, +6 whiffs) and agrees
     with a separately written frame-by-frame simulation for every remaining-frame value.
"""
import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "lab"))
import extensions  # noqa: E402

INPUTS = json.loads((ROOT / "core" / "ryu_inputs.json").read_text())


def solver(name):
    path = ROOT / "out" / f"{name}.json"
    if not path.exists():
        import subprocess
        subprocess.run([sys.executable, str(ROOT / "lab" / "build_site.py")], check=True, capture_output=True)
    return json.loads(path.read_text())


@pytest.mark.parametrize("run", ["Ryu_frame_kills", "all_k"])
def test_preparations_are_the_cores(run):
    result = solver(run)
    max_kd = max(e["kd"] if isinstance(e["kd"], int) else e["kd"][1] for e in result["enders"])
    sigs = extensions.prep_signatures(INPUTS, max_kd)
    assert len(sigs) == result["options"]["signatures"]
    checked = 0
    for ender in result["enders"]:
        for row in ender["rows"]:
            prep = tuple(row["prep"])
            sig = (row["frames_spent"], prep[-1:] == ("instant DR",), "dash" in prep, "Denjin" in prep)
            assert sigs[sig] == prep, f"{ender['name']} > {row['seq']}"
            checked += 1
    assert checked == sum(len(e["rows"]) for e in result["enders"])


def simulate_throw(kd, spent):
    """Frame-by-frame, written without the window formula: returns the wake-up frame on which the
    throw connects if it beats a 4-frame button pressed on the first wake-up frame, else None."""
    throw_active = range(spent + 5, spent + 8)      # pressed on frame spent+1, 5 startup, 3 active
    first_wake = kd + 1                             # defender's first actionable frame
    button_active = first_wake + 3                  # 4-frame button pressed on W1: 4th frame is active
    for frame in throw_active:
        if frame >= first_wake + 1 and frame < button_active:   # W1 cannot be thrown
            return frame - kd
    return None


def test_throw_window_matches_a_frame_by_frame_simulation():
    sigs = extensions.prep_signatures(INPUTS, 110)
    for kd in range(1, 111):
        rows = {r["frames_spent"]: r for r in extensions.throw_rows(kd, {s: p for s, p in sigs.items()})}
        for (spent, _dr, _dash, _stock) in sigs:
            if spent > kd + 3:
                continue
            connects = simulate_throw(kd, spent)
            if connects is None:
                assert spent not in rows, f"K{kd} T{spent} should not be a meaty throw"
            else:
                assert rows[spent]["connects_on_wake_frame"] == connects, f"K{kd} T{spent}"


def test_throw_anchors_from_the_audited_convention():
    sigs = extensions.prep_signatures(INPUTS, 110)
    at = lambda kd: {tuple(r["prep"]): r for r in extensions.throw_rows(kd, sigs)}
    # core/method.md, assumption 3: a throw pressed at +5 connects on wake-up frame 2; at +6 it whiffs.
    assert at(5)[()]["connects_on_wake_frame"] == 2 and at(5)[()]["flags"] == ["last active frame"]
    assert () not in at(6)
    # forward throw (+17), whiff 5LP (13 frames) leaves +4: a throw connects on wake-up frame 2
    assert at(17)[("5LP",)]["remaining"] == 4 and at(17)[("5LP",)]["connects_on_wake_frame"] == 2
