"""Snapshot SuperCombo wiki data through its MediaWiki API (exact bytes, no agent in between).

Usage:
  python tools/fetch_supercombo.py ryu        # Ryu data: revisions, database rows, wikitext
  python tools/fetch_supercombo.py system     # system-rule pages: revisions and wikitext
  python tools/fetch_supercombo.py roster     # database rows for every character
"""
import json
import sys
import urllib.parse

import snap

API = "https://wiki.supercombo.gg/api.php"
GROUP = "community-wiki"  # FAT shares contributors with the wiki, so they count as one voice

RYU_PAGES = ["Ryu", "Ryu/Data", "Ryu/Strategy", "Ryu/Combos", "Ryu/Matchups", "Ryu/Resources"]
SYSTEM_PAGES = ["Offense", "Defense", "Gauges", "Movement", "Game_Data", "Glossary", "Version/2.05"]


def api(**params):
    params["format"] = "json"
    url = API + "?" + urllib.parse.urlencode(params)
    return url, snap.fetch(url)


def latest_revisions(pages, limit=30):
    out = {}
    for page in pages:
        title = "Street_Fighter_6/" + page
        url, data = api(action="query", prop="revisions", titles=title,
                        rvprop="ids|timestamp|comment", rvlimit=str(limit))
        slug = page.replace("/", "_")
        snap.record(f"supercombo/revisions/{slug}.json", data, url=url, route="curl MediaWiki API",
                    family="supercombo", independence_group=GROUP, note=f"revision history of {title}")
        revs = next(iter(json.loads(data)["query"]["pages"].values())).get("revisions", [])
        out[page] = revs
    return out


def wikitext(page, revid):
    url, data = api(action="parse", oldid=str(revid), prop="wikitext")
    slug = page.replace("/", "_")
    snap.record(f"supercombo/wikitext/{slug}@{revid}.json", data, url=url, route="curl MediaWiki API",
                family="supercombo", independence_group=GROUP, revid=revid,
                note=f"wikitext of Street_Fighter_6/{page} at revision {revid}")


def cargo_fields(table):
    url, data = api(action="cargofields", table=table)
    snap.record(f"supercombo/cargo/{table}.fields.json", data, url=url, route="curl MediaWiki API",
                family="supercombo", independence_group=GROUP, note=f"field list of database table {table}")
    return list(json.loads(data)["cargofields"].keys())


def cargo_rows(table, fields, where, snapshot_id, note):
    rows, offset = [], 0
    while True:
        url, data = api(action="cargoquery", tables=table, fields=",".join(fields), where=where,
                        limit="500", offset=str(offset), order_by="_pageName,_ID")
        batch = [r["title"] for r in json.loads(data)["cargoquery"]]
        rows.extend(batch)
        if len(batch) < 500:
            break
        offset += 500
    body = json.dumps(rows, indent=0, sort_keys=True, ensure_ascii=False).encode()
    snap.record(snapshot_id, body, url=API + f"?action=cargoquery&tables={table}&where={urllib.parse.quote(where)}",
                route="curl MediaWiki API (paged, rows re-serialised sorted)", family="supercombo",
                independence_group=GROUP, note=note, rows=len(rows))
    return rows


def main(what):
    if what == "ryu":
        revs = latest_revisions(RYU_PAGES)
        for page, r in revs.items():
            print(f"{page}: latest revid {r[0]['revid']} at {r[0]['timestamp']}")
        wikitext("Ryu/Data", revs["Ryu/Data"][0]["revid"])
        wikitext("Ryu/Strategy", revs["Ryu/Strategy"][0]["revid"])
        wikitext("Ryu/Combos", revs["Ryu/Combos"][0]["revid"])
        for table in ("SF6_FrameData", "SF6_CharacterData"):
            fields = cargo_fields(table)
            rows = cargo_rows(table, fields, 'chara="Ryu"', f"supercombo/cargo/{table}.Ryu.json",
                              f"database rows of {table} for Ryu")
            print(f"{table}: {len(fields)} fields, {len(rows)} Ryu rows")
    elif what == "system":
        revs = latest_revisions(SYSTEM_PAGES)
        for page, r in revs.items():
            if not r:
                print(f"{page}: no such page")
                continue
            print(f"{page}: latest revid {r[0]['revid']} at {r[0]['timestamp']}")
            wikitext(page, r[0]["revid"])
    elif what == "roster":
        for table in ("SF6_FrameData", "SF6_CharacterData"):
            fields = cargo_fields(table)
            rows = cargo_rows(table, fields, "1=1", f"supercombo/cargo/{table}.roster.json",
                              f"database rows of {table} for every character")
            print(f"{table}: {len(rows)} rows across {len({r.get('chara') for r in rows})} characters")
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "")
