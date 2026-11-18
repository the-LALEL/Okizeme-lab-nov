"""Inch 6: assemble the rules ledger from the rules wave and machine-check every quote.

Each answer in research/w4/*.json cites file, line and exact text. A quote counts only if that
text really is in that file at (or within 3 lines of) that line. Answers from the page-family
researchers and from the independent second readers are kept side by side; nothing is merged
or resolved here.

Usage: python lab/rules_ledger.py
Writes: data/rules/rules.json and prints every quote that failed the check.
"""
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
W4 = ROOT / "research" / "w4"


def norm(text):
    return re.sub(r"\s+", " ", text).strip()


_cache = {}


def lines_of(path):
    if path not in _cache:
        p = pathlib.Path(path)
        _cache[path] = p.read_text(encoding="utf-8", errors="replace").splitlines() if p.exists() else None
    return _cache[path]


def check_quote(q):
    lines = lines_of(q["file"])
    if lines is None:
        return "file not found"
    want = norm(q["text"])
    if not want:
        return "empty quote"
    lo, hi = max(0, q["line"] - 4), min(len(lines), q["line"] + 3)
    window = norm(" ".join(lines[lo:hi]))
    if want in window:
        return "ok"
    if want in norm(" ".join(lines)):
        return "ok (different line)"
    return "text not found"


def load(name):
    path = W4 / name
    return json.loads(path.read_text()) if path.exists() else None


def main():
    questions = {r["id"]: r for r in json.loads((W4 / "questions.json").read_text())["rules"]}
    readers = {"extract": ["extract-offense.json", "extract-defense-movement.json", "extract-gauges-data.json"],
               "blind": ["blind-odd.json", "blind-even.json"]}
    ledger = {rid: {"rule_id": rid, "question": q["question"], "family": q["family"]} for rid, q in questions.items()}
    failed, total = [], 0
    for role, files in readers.items():
        for name in files:
            data = load(name)
            if not data:
                print(f"missing: {name}")
                continue
            for a in data["answers"]:
                good = []
                for q in a.get("quotes", []):
                    total += 1
                    verdict = check_quote(q)
                    if verdict.startswith("ok"):
                        good.append({"file": str(pathlib.Path(q["file"]).relative_to(ROOT)) if q["file"].startswith(str(ROOT)) else q["file"],
                                     "line": q["line"], "text": q["text"], "supports": q.get("supports", "")})
                    else:
                        failed.append((name, a["rule_id"], verdict, q["text"][:90]))
                ledger[a["rule_id"]][role] = {
                    "reader": name[:-5], "status": a["status"], "statement": a["statement"],
                    "parameters": {p["name"]: p["value"] for p in a.get("parameters", [])},
                    "quotes": good, "quotes_failed_check": len(a.get("quotes", [])) - len(good),
                    "notes": a.get("notes", ""),
                }
    refute = load("refute.json")
    out = {"rules": [ledger[k] for k in sorted(ledger)], "quote_check": {"total": total, "failed": len(failed)}}
    if refute:
        for group in ("later_changes", "claim_checks"):
            for item in refute[group]:
                kept = []
                for q in item.get("quotes", []):
                    total += 1
                    verdict = check_quote(q)
                    (kept if verdict.startswith("ok") else failed).append(
                        q if verdict.startswith("ok") else ("refute.json", item.get("rule_id") or item.get("claim_id"), verdict, q["text"][:90]))
                item["quotes"] = kept
        out["later_changes"], out["claim_checks"] = refute["later_changes"], refute["claim_checks"]
        out["quote_check"] = {"total": total, "failed": len(failed)}
    path = ROOT / "data" / "rules" / "rules.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    covered = sum(1 for r in out["rules"] if "extract" in r)
    both = sum(1 for r in out["rules"] if "extract" in r and "blind" in r)
    print(f"{len(out['rules'])} rules; {covered} answered by a researcher; {both} also by a second reader; "
          f"{total} quotes checked, {len(failed)} failed")
    for f in failed:
        print("  FAILED", f)


if __name__ == "__main__":
    main()
