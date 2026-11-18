"""fk_calc.py - every qualifying best frame kill for every ender (sf6-frame-kills skill).

Usage: python fk_calc.py INPUTS.json CALC.json [--max-actions 3] [--min-block N] [--out PREFIX]

INPUTS.json: sf6-frame-kill-audit format (single, multi, preparations, scope).
CALC.json:   enders [{name, kd | kd_range [lo, hi], combo_count (int|null), group?, reach?}],
             prevalence_source, move_flags {move: unresolved-conflict text}.

Timing (confirmed Sept 2026): after KD +K, spending T frames then pressing a move with startup S
puts active frame c = R - S + 2 (R = K - T) on the defender's first wake-up frame. Meaty iff
1 <= c <= active. Single-hit advantage = listed + (c - 1), +4 after instant Drive Rush for normals
and command normals. Multi-hit: the move frame meeting wake-up is R + 1; hits ending earlier whiff;
the last live hit sets advantage = stun - (total - contact frame) - 1.

Search: every multiset of up to --max-actions preparation actions (dash, whiffed normals, one
stock-building action), optionally ending in instant Drive Rush, collapsed to distinct signatures
(frames, Drive Rush, dash used, stock used) with the fewest actions kept. "Best" per group
(meaty, Drive cost, dash used, stock used) = the Pareto front of higher block advantage vs fewer
actions. A row whose block equals the meaty's ceiling (its best possible value at any timing) is
provably the maximum: no longer preparation can beat it.

Determinism: pure function of the input files and options; every sort is a total order ending in
the sequence text; the output carries a sha256 of its canonical JSON.
"""
import argparse, hashlib, itertools, json

ap = argparse.ArgumentParser()
ap.add_argument("inputs"); ap.add_argument("calc")
ap.add_argument("--max-actions", type=int, default=None,
                help="cap on preparation actions before the optional instant DR (default: exhaustive bound)")
ap.add_argument("--min-block", type=int, default=None)
ap.add_argument("--out", default="frame_kills")
A = ap.parse_args()

raw_in, raw_calc = open(A.inputs, "rb").read(), open(A.calc, "rb").read()
INP, CALC = json.loads(raw_in), json.loads(raw_calc)
P, SINGLE, MULTI, SCOPE = INP["preparations"], INP["single"], INP["multi"], INP["scope"]
MIN_BLOCK = SCOPE.get("min_block", 0) if A.min_block is None else A.min_block
FLAGS = CALC.get("move_flags", {})
STOCK_PREPS = dict(P.get("stock", {}))
if "denjin" in P:
    STOCK_PREPS.setdefault("Denjin", P["denjin"])
STOCK_FORCED = set(SCOPE.get("stock_forces_denjin_versions", SCOPE.get("stock_forced", [])))

ACTIONS = [("dash", P["dash"], "dash")] if "dash" in P else []
ACTIONS += [(k, v, "whiff") for k, v in sorted(P["whiff"].items(), key=lambda kv: (kv[1], kv[0]))]
ACTIONS += [(k, v, "stock") for k, v in sorted(STOCK_PREPS.items())]
FR = {a[0]: a[1] for a in ACTIONS}; FR["instant DR"] = P["instant_dr"]
KIND = {a[0]: a[2] for a in ACTIONS}
FOLLOW = sorted(SINGLE) + sorted(MULTI)


def evaluate(R, dr, fu):
    """(block, hit, c, active) when pressing fu with R frames left, or None if not a meaty."""
    bonus = 4 if dr else 0
    if fu in SINGLE:
        m = SINGLE[fu]
        if dr and not m["dr"]:
            return None
        c = R - m["startup"] + 2
        if not 1 <= c <= m["active"]:
            return None
        hit = m["hit"] if isinstance(m["hit"], str) else m["hit"] + c - 1 + bonus
        return m["block"] + c - 1 + bonus, hit, c, m["active"]
    m = MULTI[fu]
    if dr and not m["dr"]:
        return None
    if "fixed_block" in m:
        c = R - m["startup"] + 2
        if not 1 <= c <= m["active"]:
            return None
        return m["fixed_block"], m["hit"], c, m["active"]
    f = R + 1
    live = [h for h in m["hits"] if h["last"] >= f]
    if not live or live[0]["first"] > f:
        return None
    last = live[-1]
    after = m["total"] - max(last["first"], f)
    return last["blockstun"] - after - 1 + bonus, last["hitstun"] - after - 1 + bonus, f, None


CEIL = {}
for fu in FOLLOW:
    for dr in (False, True):
        vals = [r[0] for r in (evaluate(R, dr, fu) for R in range(0, 300)) if r]
        CEIL[fu, dr] = max(vals) if vals else None

for mv, m in MULTI.items():
    for R, pub in m.get("published_check", {}).items():
        got = evaluate(int(R), False, mv)
        if got is None or got[0] != pub:
            print(f"WARNING published check: {mv} at R{R} derived {got} vs published {pub:+d}")

MAX_KD = max(max(e.get("kd_range", [e.get("kd", 0)])) for e in CALC["enders"])
# No preparation longer than BOUND actions fits inside the longest knockdown, so searching BOUND is exhaustive.
BOUND = MAX_KD // min(a[1] for a in ACTIONS) + 1
DEPTH = BOUND if A.max_actions is None else A.max_actions
EXHAUSTIVE = DEPTH >= BOUND


def signatures():
    """Distinct (T, dr, dash, stock) -> fewest-action, then alphabetically first, preparation."""
    best = {}
    names = [a[0] for a in ACTIONS]
    for n in range(DEPTH + 1):
        for combo in itertools.combinations_with_replacement(names, n):
            stock = sum(KIND[x] == "stock" for x in combo)
            if stock > 1:
                continue
            variants = [combo] + ([] if stock else [combo + ("instant DR",)])
            for prep in variants:
                T = sum(FR[p] for p in prep)
                if T > MAX_KD:
                    continue
                sig = (T, prep[-1:] == ("instant DR",), "dash" in prep, bool(stock))
                cur = best.get(sig)
                if cur is None or len(prep) < len(cur[0]):
                    best[sig] = [prep, 1]
                elif len(prep) == len(cur[0]):
                    cur[1] += 1
                    if " > ".join(prep) < " > ".join(cur[0]):
                        cur[0] = prep
    return {s: (v[0], v[1]) for s, v in best.items()}


SIGS = signatures()


def drive_of(prep, fu):
    d = prep.count("instant DR") + SINGLE.get(fu, {}).get("drive", 0)
    return f"{d} + stock" if SINGLE.get(fu, {}).get("stock") else str(d)


def dnum(d):
    return int(d.split()[0]) + (0.5 if "stock" in d else 0)


def rows_for(kds):
    groups = {}
    for (T, dr, dash, stock), (prep, alts) in sorted(SIGS.items()):
        for fu in FOLLOW:
            if stock and (fu in STOCK_FORCED or SINGLE.get(fu, {}).get("stock")):
                continue
            res = [evaluate(k - T, dr, fu) for k in kds]
            if any(r is None for r in res):
                continue
            blocks = [r[0] for r in res]
            if min(blocks) < MIN_BLOCK:
                continue
            hits = [r[1] for r in res]
            cs, act = [r[2] for r in res], res[0][3]
            span = f"{min(cs)}" + (f"-{max(cs)}" if max(cs) != min(cs) else "")
            contact = f"active {span}/{act}" if act else f"move frame {span} on wake-up"
            if fu in MULTI and "fixed_block" in MULTI[fu]:
                contact += f" ({MULTI[fu]['label']})"
            flags = []
            if min(blocks) == CEIL[fu, dr]:
                flags.append("ceiling")
            if act and max(cs) == act and act > 1 and not (fu in MULTI):
                flags.append("last active frame")
            fl = FLAGS.get(fu)
            if fl and (isinstance(fl, str) or not act or max(cs) >= fl.get("from_active", 1)):
                flags.append("conflict")
            if alts > 1:
                flags.append(f"{alts - 1} equivalent prep" + ("s" if alts > 2 else ""))
            row = dict(seq=" > ".join(list(prep) + [fu]), prep=list(prep), follow_up=fu, frames_spent=T,
                       block=[min(blocks), max(blocks)],
                       hit=hits[0] if isinstance(hits[0], str) else [min(hits), max(hits)],
                       drive=drive_of(prep, fu), contact=contact, actions=len(prep), flags=flags)
            groups.setdefault((fu, row["drive"], dash, stock), []).append(row)
    out = []
    for g in groups.values():
        g.sort(key=lambda r: (-r["block"][0], -r["block"][1], r["actions"], r["seq"]))
        fewest = None
        for r in g:  # Pareto front: keep a row only if it needs fewer actions than every better row
            if fewest is None or r["actions"] < fewest:
                out.append(r); fewest = r["actions"]
    out.sort(key=lambda r: (-r["block"][0], -r["block"][1], dnum(r["drive"]), r["actions"], r["seq"]))
    return out


enders = []
for e in CALC["enders"]:
    kds = list(range(e["kd_range"][0], e["kd_range"][1] + 1)) if "kd_range" in e else [e["kd"]]
    rows = rows_for(kds)
    per_kd = []  # knockdown ranges depend on spacing: also give the top row at each exact value
    if len(kds) > 1:
        for k in kds:
            top = rows_for([k])
            per_kd.append(dict(kd=k, row=top[0] if top else None))
    enders.append(dict(name=e["name"], group=e.get("group", e["name"]), kd=kds[0] if len(kds) == 1 else [kds[0], kds[-1]],
                       combo_count=e.get("combo_count"), reach=e.get("reach"), rows=rows, per_kd=per_kd,
                       best_block=rows[0]["block"][0] if rows else None))

NEG = -10 ** 6
gbest = {}
for e in enders:
    gbest[e["group"]] = max(gbest.get(e["group"], NEG), e["best_block"] if e["best_block"] is not None else NEG)
gcount = {e["group"]: e["combo_count"] for e in enders}
enders.sort(key=lambda e: (gcount[e["group"]] is None, -(gcount[e["group"]] or 0), -gbest[e["group"]], e["group"],
                           -(e["best_block"] if e["best_block"] is not None else NEG), e["name"]))
counts = sorted({e["combo_count"] for e in enders if e["combo_count"] is not None}, reverse=True)
for e in enders:
    e["prevalence_rank"] = counts.index(e["combo_count"]) + 1 if e["combo_count"] is not None else None

result = dict(character=INP.get("character"), generator="fk_calc.py",
              inputs_sha256=hashlib.sha256(raw_in).hexdigest(), calc_sha256=hashlib.sha256(raw_calc).hexdigest(),
              prevalence_source=CALC.get("prevalence_source"), move_flags=FLAGS,
              options=dict(search_depth=DEPTH, exhaustive_bound=BOUND, exhaustive=EXHAUSTIVE, min_block=MIN_BLOCK,
                           signatures=len(SIGS), meaties=FOLLOW),
              enders=enders)
canon = json.dumps(result, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
result["output_sha256"] = hashlib.sha256(canon.encode()).hexdigest()
json.dump(result, open(A.out + ".json", "w", encoding="utf-8"), indent=1, ensure_ascii=False, sort_keys=True)


def fmt(v):
    if isinstance(v, str):
        return v
    return f"{v[0]:+d}" if v[0] == v[1] else f"{v[0]:+d} to {v[1]:+d}"


L = [f"# {result['character']} frame kills by ender", "",
     f"fk_calc.py output sha256 `{result['output_sha256'][:16]}` (inputs `{result['inputs_sha256'][:12]}`, "
     f"calc `{result['calc_sha256'][:12]}`). Search: "
     + (f"exhaustive (every preparation up to {DEPTH} actions; none longer fits the longest knockdown), "
        if EXHAUSTIVE else f"capped at {DEPTH} actions, NOT exhaustive (bound {BOUND}), ")
     + "plus optional instant Drive Rush, "
     f"minimum block {MIN_BLOCK:+d}, {len(SIGS)} distinct preparation timings x {len(FOLLOW)} meaties.", "",
     "**Order.** Enders by prevalence evidence, most common first; enders with equal evidence share a rank and "
     "are ordered by their best block advantage; enders with no evidence come last. Rows inside an ender: block "
     "advantage, highest first. **Ranked quantity:** block advantage after the meaty connects (worst case across "
     f"a knockdown range). Prevalence evidence: {result['prevalence_source']}.", "",
     "**Best.** For each meaty, Drive cost, dash and stock use, the rows kept are the trade-off front: the highest "
     "block advantage, plus any lower-advantage row that needs fewer actions. **Flags:** `ceiling` = the meaty's "
     "best possible value, so no other preparation beats it; `last active frame` = fragile to any data error; "
     "`conflict` = depends on an unresolved input (see below).", ""]
if FLAGS:
    L += ["**Unresolved inputs:**", ""] + [f"- {k}: {v if isinstance(v, str) else v['text']}" for k, v in sorted(FLAGS.items())] + [""]
for e in enders:
    kd = f"+{e['kd']}" if isinstance(e["kd"], int) else f"+{e['kd'][0]} to +{e['kd'][1]}, rows valid across the range"
    pr = (f"prevalence rank {e['prevalence_rank']} ({e['combo_count']} combos)" if e["prevalence_rank"]
          else "no prevalence evidence")
    L += [f"## {e['name']} (KD {kd}) - {pr}", ""]
    if e["reach"]:
        L += [f"Reach: {e['reach']}", ""]
    if e["per_kd"]:
        L += ["Top row at each exact knockdown value (read the value off the frame meter):", "",
              "| KD | Block | Hit | Drive | Preparation > meaty | Contact | Flags |", "|---|---|---|---|---|---|---|"]
        for x in e["per_kd"]:
            r = x["row"]
            L.append(f"| +{x['kd']} | " + (f"{fmt(r['block'])} | {fmt(r['hit'])} | {r['drive']} | {r['seq']} | {r['contact']} | "
                                          f"{', '.join(r['flags'])} |" if r else "none | | | | | |"))
        L += ["", "Rows that work at every value in the range:" if e["rows"] else "No single row works across the whole range.", ""]
    if not e["rows"]:
        if not e["per_kd"]:
            L += ["No qualifying meaty in the searched scope.", ""]
        continue
    L += ["| Block | Hit | Drive | Preparation > meaty | Frames spent | Contact | Flags |", "|---|---|---|---|---|---|---|"]
    for r in e["rows"]:
        L.append(f"| {fmt(r['block'])} | {fmt(r['hit'])} | {r['drive']} | {r['seq']} | {r['frames_spent']} | "
                 f"{r['contact']} | {', '.join(r['flags'])} |")
    L.append("")
open(A.out + ".md", "w", encoding="utf-8").write("\n".join(L))
print(f"{len(enders)} enders, {sum(len(e['rows']) for e in enders)} rows, "
      f"{sum(1 for e in enders if not e['rows'])} enders without rows, sha256 {result['output_sha256']}")
