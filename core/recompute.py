"""Clean-room recompute for the sf6-frame-kill-audit skill.

Usage:
  python recompute.py INPUTS.json FRAME_KILL_FILE.md [--tables] [--json OUT.json]

Regenerates every meaty in scope from INPUTS.json (never from the file's rows),
then diffs against the file's catalogue ("### KD +N" sections with columns
Block | Hit | Drive | Preparation > follow-up | Frames spent | Contact [| Status]):
  - value errors (block, hit, contact, frames, Drive cost)
  - rows that are not meaties under the inputs
  - better rows the file omits (best per follow-up / Drive cost / dash / Denjin group)
  - sort-order breaks (block desc, Drive asc with a stored stock counting extra, fewer actions)
With --tables it also checks the summary maximum table, the practical-choices table
and the paid-pressure table.

Convention (confirmed Sept 2026): after KD +K, spending T frames then pressing a move
with startup S makes active frame c = K - T - S + 2 meet the first wake-up frame.
Meaty iff 1 <= c <= active. Single-hit advantage = listed + (c - 1), +4 after instant DR
for normals/command normals. Multi-hit meaties are derived from per-hit data: the move frame
meeting wake-up is R + 1; the last live hit sets advantage = stun - (total - contact) - 1.
"""
import json, re, sys, collections

args = [a for a in sys.argv[1:] if not a.startswith("--")]
if len(args) < 2:
    sys.exit(__doc__)
INP = json.load(open(args[0], encoding="utf-8"))
SRC = args[1]
WANT_TABLES = "--tables" in sys.argv
JSON_OUT = sys.argv[sys.argv.index("--json") + 1] if "--json" in sys.argv else None

P = INP["preparations"]
PREP_FR = dict(P["whiff"], dash=P["dash"], Denjin=P["denjin"], **{"instant DR": P["instant_dr"]})
SINGLE, MULTI = INP["single"], INP["multi"]
MIN_BLOCK = INP["scope"]["min_block"]
STOCK_FORCED = set(INP["scope"]["stock_forces_denjin_versions"])


def evaluate(kd, prep, fu):
    T = sum(PREP_FR[p] for p in prep)
    R = kd - T
    dr = bool(prep) and prep[-1] == "instant DR"
    bonus = 4 if dr else 0
    if fu in SINGLE:
        m = SINGLE[fu]
        if dr and not m["dr"]:
            return None
        c = R - m["startup"] + 2
        if not 1 <= c <= m["active"]:
            return None
        blk = m["block"] + c - 1 + bonus
        hit = m["hit"] if isinstance(m["hit"], str) else m["hit"] + c - 1 + bonus
        return blk, hit, f"active {c}/{m['active']}"
    if fu in MULTI:
        m = MULTI[fu]
        if dr and not m["dr"]:
            return None
        if "fixed_block" in m:
            c = R - m["startup"] + 2
            if not 1 <= c <= m["active"]:
                return None
            return m["fixed_block"], m["hit"], m["label"]
        # Derive from per-hit data. The move frame that meets the defender's first
        # actionable frame is R + 1. Hits that end before it whiff; the first live hit
        # must overlap it (else it isn't a meaty); the LAST live hit sets the advantage.
        f = R + 1
        live = [h for h in m["hits"] if h["last"] >= f]
        if not live or live[0]["first"] > f:
            return None
        last = live[-1]
        contact = max(last["first"], f)
        after = m["total"] - contact
        lab = m.get("labels", {})
        kind = "both" if len(live) > 1 else ("last_first" if contact == last["first"] else "late")
        return (last["blockstun"] - after - 1 + bonus,
                last["hitstun"] - after - 1 + bonus, lab.get(kind, m["label"]))
    return None


def drive_of(prep, fu):
    d = prep.count("instant DR")
    m = SINGLE.get(fu, {})
    d += m.get("drive", 0)
    return f"{d} + stock" if m.get("stock") else f"{d}"


FOLLOW = list(SINGLE) + list(MULTI)

# Cross-check derived multi-hit values against published in-game values (no Drive Rush).
for _mv, _m in MULTI.items():
    for _R, _pub in _m.get("published_check", {}).items():
        _got = evaluate(int(_R), (), _mv)
        if _got is None or _got[0] != _pub:
            print(f"WARNING published check: {_mv} at R{_R} derived {_got} vs published {_pub:+d}")
BASE = [()] + [(w,) for w in list(P["whiff"]) + ["dash", "Denjin"]] + \
       [("dash", w) for w in list(P["whiff"]) + ["dash"]]
PREPS = []
for p in BASE:
    PREPS.append(p)
    if "Denjin" not in p:
        PREPS.append(p + ("instant DR",))


def solve(kd):
    out = []
    for prep in PREPS:
        for fu in FOLLOW:
            if "Denjin" in prep and (fu in STOCK_FORCED or SINGLE.get(fu, {}).get("stock")):
                continue
            r = evaluate(kd, prep, fu)
            if r is None or r[0] < MIN_BLOCK:
                continue
            out.append(dict(prep=prep, fu=fu, block=r[0], hit=r[1], contact=r[2],
                            drive=drive_of(prep, fu), dash="dash" in prep, n=len(prep)))
    return out


def gkey(r):
    return (r["fu"], r["drive"], r["dash"], "Denjin" in r["prep"])


def dnum(d):
    return int(d.split()[0]) + (0.5 if "stock" in d else 0)


def seq(prep, fu):
    return " > ".join(list(prep) + [fu])


lines = open(SRC, encoding="utf-8").read().splitlines()
rows, kd, kds = [], None, []
for i, ln in enumerate(lines, 1):
    m = re.match(r"### KD \+(\d+)", ln)
    if m:
        kd = int(m.group(1)); kds.append(kd); continue
    if ln.startswith("## ") and kd is not None:
        kd = None
    if kd is None or not ln.startswith("|") or ln.startswith("| Block") or ln.startswith("|---"):
        continue
    c = [x.strip() for x in ln.strip("|").split("|")]
    toks = [t.strip() for t in c[3].split(">")]
    rows.append(dict(line=i, kd=kd, block=int(c[0].replace("−", "-")), hit=c[1], drive=c[2], seq=c[3],
                     prep=tuple(toks[:-1]), fu=toks[-1], spent=int(c[4]), contact=c[5]))

rep = collections.defaultdict(list)
for r in rows:
    try:
        res = evaluate(r["kd"], r["prep"], r["fu"])
        T = sum(PREP_FR[p] for p in r["prep"])
    except KeyError as e:
        rep["unknown_token"].append(f"L{r['line']}: {e}"); continue
    if res is None:
        rep["not_meaty"].append(f"L{r['line']} KD+{r['kd']}: {r['seq']}"); continue
    hs = res[1] if isinstance(res[1], str) else f"{res[1]:+d}"
    got = (f"{res[0]:+d}", hs, res[2], T, drive_of(r["prep"], r["fu"]))
    have = (f"{r['block']:+d}", r["hit"], r["contact"], r["spent"], r["drive"])
    if got != have:
        rep["value_diff"].append(f"L{r['line']} KD+{r['kd']} {r['seq']}: file {have} vs {got}")

byk = collections.defaultdict(list)
for r in rows:
    r["dash"] = "dash" in r["prep"]
    byk[r["kd"]].append(r)
for k in kds:
    best = {}
    for s in solve(k):
        g = gkey(s)
        if g not in best or s["block"] > best[g]["block"] or (s["block"] == best[g]["block"] and s["n"] < best[g]["n"]):
            best[g] = s
    fg = collections.defaultdict(list)
    for r in byk[k]:
        fg[gkey(r)].append(r)
    for g, s in best.items():
        if g not in fg or max(x["block"] for x in fg[g]) < s["block"]:
            rep["omitted_better"].append(f"KD+{k}: {seq(s['prep'], s['fu'])} {s['block']:+d}")
    keys = [(-x["block"], dnum(x["drive"]), len(x["prep"])) for x in byk[k]]
    for a, b, x in zip(keys, keys[1:], byk[k][1:]):
        if b < a:
            rep["sort_break"].append(f"KD+{k} at L{x['line']}: {x['seq']}")


def best_for(kd, cost):
    sol = [s for s in solve(kd) if s["drive"] == cost]
    if not sol:
        return None, []
    mx = max(s["block"] for s in sol)
    return mx, [seq(s["prep"], s["fu"]) for s in sol if s["block"] == mx]


if WANT_TABLES:
    def table(start):
        on = False
        for i, ln in enumerate(lines, 1):
            if ln.startswith(start):
                on = True; continue
            if on:
                if not ln.startswith("|"):
                    return
                if not ln.startswith("|---"):
                    yield i, [c.strip() for c in ln.strip("|").split("|")]
    for i, c in table("| Ender / exact KD condition"):
        k = int(c[1].replace("+", ""))
        for col, cost in zip(c[2:5], ["0", "1", "2"]):
            m = re.match(r"([+-]\d+):\s*(.+)$", col)
            mx, routes = best_for(k, cost)
            if not m:
                if col == "—" and mx is not None:
                    rep["summary_dash_but_exists"].append(f"L{i} {c[0]} [{cost} Drive]: solver max {mx:+d} {routes[:2]}")
                continue
            toks = [t.strip() for t in m.group(2).split(">")]
            r = evaluate(k, tuple(toks[:-1]), toks[-1])
            if r is None or r[0] != int(m.group(1)):
                rep["summary_cell_wrong"].append(f"L{i} {c[0]} [{cost}]: '{col}' computes to {r}")
            if mx != int(m.group(1)):
                rep["summary_not_max"].append(f"L{i} {c[0]} [{cost}]: {col} vs max {mx} {routes[:2]}")
    for i, c in table("| Required KD and example"):
        k = int(re.match(r"\+(\d+)", c[0]).group(1))
        toks = [t.strip() for t in c[1].replace(" immediately", "").split(">")]
        r = evaluate(k, tuple(toks[:-1]), toks[-1])
        if r is None or r[0] != int(c[2].replace("−", "-")):
            rep["practical_wrong"].append(f"L{i}: {c[:3]} computes to {r}")
    for i, c in table("| Required KD | Preparation"):
        k = int(c[0].replace("+", ""))
        toks = [t.strip() for t in c[1].split(">")]
        r = evaluate(k, tuple(toks[:-1]), toks[-1])
        if r is None or r[0] != int(c[3]):
            rep["paid_wrong"].append(f"L{i}: {c[:4]} computes to {r}")

print(f"rows parsed: {len(rows)} in {len(kds)} KD buckets")
for k in ["unknown_token", "value_diff", "not_meaty", "omitted_better", "sort_break",
          "summary_cell_wrong", "summary_not_max", "summary_dash_but_exists", "practical_wrong", "paid_wrong"]:
    if k in rep or k in ("value_diff", "not_meaty", "omitted_better", "sort_break"):
        print(f"{k}: {len(rep.get(k, []))}")
        for x in rep.get(k, [])[:25]:
            print("   ", x)
if JSON_OUT:
    json.dump(rep, open(JSON_OUT, "w"), indent=1, ensure_ascii=False)
