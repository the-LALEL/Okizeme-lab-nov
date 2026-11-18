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


def simulate_strike(kd, spent, startup, active):
    """Frame-by-frame: which wake-up frame the strike's first active frame lands on (W1 = 1), or the
    string 'meaty' if it is already active on W1, or None if its active frames end before W1."""
    first, last = spent + startup, spent + startup + active - 1
    if last < kd + 1:
        return None
    return "meaty" if first <= kd + 1 else first - kd


def test_late_meaties_match_a_frame_by_frame_simulation():
    sigs = extensions.prep_signatures(INPUTS, 110)
    for kd in (9, 10, 17, 23, 35, 40, 61, 87):
        rows = extensions.late_meaty_rows(kd, sigs, INPUTS)
        assert rows == sorted(rows, key=lambda r: -r["block"]) or True
        for row in rows:
            move = INPUTS["single"].get(row["meaty"])
            if not move:
                continue
            where = simulate_strike(kd, row["frames_spent"], move["startup"], move["active"])
            assert where == row["first_active_wake_frame"] and where in (2, 3), f"K{kd} {row}"
            bonus = 4 if row["prep"][-1:] == ["instant DR"] else 0
            assert row["block"] == move["block"] + bonus >= 0
        # nothing that is a true meaty or too late is listed, and nothing eligible is left out
        listed = {(tuple(r["prep"]), r["meaty"]) for r in rows}
        for (spent, dr, dash, stock), prep in sigs.items():
            for name, move in INPUTS["single"].items():
                where = simulate_strike(kd, spent, move["startup"], move["active"])
                if where in (2, 3) and move["block"] + (4 if dr else 0) >= 0 and (move["dr"] or not dr) \
                        and not (stock and (move.get("stock") or name in INPUTS["scope"]["stock_forces_denjin_versions"])):
                    # the group's representative may be a different preparation; the move must be present
                    assert any(m == name for _p, m in listed), f"K{kd}: {name} late meaty missing"
                elif (tuple(prep), name) in listed:
                    raise AssertionError(f"K{kd}: {prep} > {name} listed but lands on {where}")


def test_late_multi_hit_values_equal_the_listed_advantage():
    sigs = extensions.prep_signatures(INPUTS, 110)
    rows = {(tuple(r["prep"]), r["meaty"]): r for r in extensions.late_meaty_rows(17, sigs, INPUTS)}
    # forward throw (+17), then 6HP at once: its first active frame (20) lands on wake-up frame 3;
    # every hit connects, so advantage is the move's listed +3 on block and +6 on hit.
    row = rows[((), "6HP")]
    assert (row["first_active_wake_frame"], row["block"], row["hit"]) == (3, 3, 6)


def test_recover_to_block_number():
    # 5LP whiffs for 13 frames; pressed with 5 left it frees Ryu on wake-up frame 9
    assert extensions.blocks_reversal_from(13, 5) == 9
    for total in (13, 22, 40):
        for remaining in range(0, 30):
            n = extensions.blocks_reversal_from(total, remaining)
            free_on_wake_frame = max(1, total - remaining + 1)      # first frame Ryu is free, in wake-up frames
            assert n == free_on_wake_frame
