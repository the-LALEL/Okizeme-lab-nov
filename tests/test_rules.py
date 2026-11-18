"""Inch 6: every system rule the page shows is cited, and every quote is really in its source.

The committed ledger must record zero failed quotes and two independent readings of every rule.
When the raw source copies are on this machine, the quote check is re-run from them.
"""
import json
import pathlib
import re
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
LEDGER = ROOT / "data" / "rules" / "rules.json"


def test_ledger_has_two_readings_and_no_failed_quote():
    ledger = json.loads(LEDGER.read_text())
    assert ledger["quote_check"]["failed"] == 0 and ledger["quote_check"]["total"] > 500
    assert len(ledger["rules"]) == 26
    for rule in ledger["rules"]:
        assert "extract" in rule and "blind" in rule, rule["rule_id"]


def test_outside_claims_were_checked_not_assumed():
    checks = json.loads(LEDGER.read_text())["claim_checks"]
    verdicts = {c["claim_id"]: c["verdict"] for c in checks}
    # wake-up throw invulnerability is 1 frame (not 2) and a throw at +5 connects: both quoted
    assert verdicts["C1"] == "contradicted" and verdicts["C2"] == "contradicted"
    for claim in checks:
        assert claim["quotes"], claim["claim_id"]


def test_rules_on_the_page_are_in_the_ledger_with_a_checked_quote():
    subprocess.run([sys.executable, str(ROOT / "lab" / "build_site.py")], check=True, capture_output=True)
    page = (ROOT / "site" / "index.html").read_text()
    blob = re.search(r'<script type="application/json" id="lab">(.*?)</script>', page, re.S).group(1)
    lab = json.loads(blob.replace("<\\/", "</"))
    by_id = {r["rule_id"]: r for r in json.loads(LEDGER.read_text())["rules"]}
    assert lab["rules"]["state"] == "cited" and len(lab["rules"]["rules"]) >= 12
    for shown in lab["rules"]["rules"]:
        quotes = [q["text"] for q in by_id[shown["id"]]["extract"]["quotes"]]
        assert shown["quote"] in quotes
        assert shown["statement"] == by_id[shown["id"]]["extract"]["statement"]
    assert {"R04", "R07"} <= {r["id"] for r in lab["rules"]["rules"]}


def test_quote_check_reproduces_from_raw_copies():
    if not (ROOT / "sources" / "raw" / "supercombo" / "text").exists():
        pytest.skip("raw source copies are not on this machine (they are never committed)")
    before = LEDGER.read_bytes()
    proc = subprocess.run([sys.executable, str(ROOT / "lab" / "rules_ledger.py")], capture_output=True, text=True, check=True)
    assert " 0 failed" in proc.stdout
    assert LEDGER.read_bytes() == before
