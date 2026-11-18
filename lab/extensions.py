"""Option classes the sealed core does not model. Everything here sits outside core/.

Each extension reads the core's inputs, enumerates the SAME preparations as the core
(tests prove this against every row the core prints), and applies one stated timing rule.
The rules are the conventions in core/method.md; the rules ledger attaches quotes to them.

Frames are counted the core's way: after a knockdown of +K the attacker is free on frame 1
and the defender first acts on frame K+1, called wake-up frame 1 (W1). Spending T frames on
preparation leaves R = K - T.
"""
import itertools

THROW_STARTUP = 5        # core/ryu-verified-data.md: throws 5 startup, 3 active (frames 5-7)
THROW_ACTIVE = 3
WAKEUP_THROW_INVULNERABLE = 1   # core/method.md assumption 3: a throw first connects on W2
FASTEST_BUTTON = 4       # the fastest normal any character has; a button pressed on W1 is active on W4


def action_table(inputs):
    """Preparation actions exactly as the core builds them: (name, frames, kind)."""
    p = inputs["preparations"]
    stock = dict(p.get("stock", {}))
    if "denjin" in p:
        stock.setdefault("Denjin", p["denjin"])
    actions = [("dash", p["dash"], "dash")] if "dash" in p else []
    actions += [(k, v, "whiff") for k, v in sorted(p["whiff"].items(), key=lambda kv: (kv[1], kv[0]))]
    actions += [(k, v, "stock") for k, v in sorted(stock.items())]
    frames = {a[0]: a[1] for a in actions}
    frames["instant DR"] = p["instant_dr"]
    return actions, frames


def prep_signatures(inputs, max_kd):
    """Distinct (frames spent, ends in Drive Rush, dash used, stock used) -> the fewest-action,
    then alphabetically first, preparation. Mirrors the core's search, including its bound:
    no preparation longer than `bound` actions fits inside the longest knockdown."""
    actions, frames = action_table(inputs)
    kind = {a[0]: a[2] for a in actions}
    names = [a[0] for a in actions]
    bound = max_kd // min(a[1] for a in actions) + 1
    best = {}
    for n in range(bound + 1):
        for combo in itertools.combinations_with_replacement(names, n):
            stock = sum(kind[x] == "stock" for x in combo)
            if stock > 1:
                continue
            for prep in [combo] + ([] if stock else [combo + ("instant DR",)]):
                spent = sum(frames[p] for p in prep)
                if spent > max_kd:
                    continue
                sig = (spent, prep[-1:] == ("instant DR",), "dash" in prep, bool(stock))
                cur = best.get(sig)
                if cur is None or len(prep) < len(cur) or (len(prep) == len(cur) and " > ".join(prep) < " > ".join(cur)):
                    best[sig] = prep
    return best


def throw_rows(kd, signatures):
    """Meaty throw timings after a knockdown of +kd.

    The throw is pressed with R frames left, so its active frames are W(5-R) to W(7-R).
    W1 cannot be thrown, so it connects on the first active frame at or after W2: that needs
    R <= 5 (at R = 6 the last active frame is W1 and the throw whiffs).
    A button pressed on W1 is active on W4, so the throw beats it only if it connects by W3:
    that needs R >= 2. The window is therefore R = 2 to 5.
    """
    rows = []
    for (spent, drive_rush, dash, stock), prep in signatures.items():
        remaining = kd - spent
        if not 2 <= remaining <= 5:
            continue
        first_active_wake = THROW_STARTUP - remaining          # W-number of the throw's first active frame
        connects_on = max(first_active_wake, 1 + WAKEUP_THROW_INVULNERABLE)
        assert connects_on < FASTEST_BUTTON
        active_frame = connects_on - first_active_wake + 1      # which of the throw's 3 active frames connects
        rows.append({
            "prep": list(prep),
            "frames_spent": spent,
            "remaining": remaining,
            "connects_on_wake_frame": connects_on,
            "throw_active_frame": active_frame,
            "drive": sum(p == "instant DR" for p in prep),
            "dash": dash,
            "stock": stock,
            "actions": len(prep),
            "flags": ["last active frame"] if active_frame == THROW_ACTIVE else [],
        })
    # Sturdier first (not on the throw's last active frame), then fewer actions, then less Drive, then text.
    rows.sort(key=lambda r: (r["drive"], bool(r["flags"]), r["actions"], r["frames_spent"], " > ".join(r["prep"])))
    return rows
