"""Snapshot Capcom's official pages (rendered in a real browser, registered with fingerprints).

Usage:
  python tools/fetch_capcom.py frame ryu     # official frame table for one character
  python tools/fetch_capcom.py patches       # battle-change version list and the latest patch pages
"""
import json
import pathlib
import subprocess
import sys
import tempfile

import snap

HERE = pathlib.Path(__file__).resolve().parent


def capture(*args):
    with tempfile.TemporaryDirectory() as tmp:
        proc = subprocess.run(["node", str(HERE / "capcom_capture.js"), tmp, *args],
                              capture_output=True, text=True, check=True, timeout=600)
        result = json.loads(proc.stdout.strip().splitlines()[-1])
        files = {p.name: p.read_bytes() for p in pathlib.Path(tmp).iterdir()}
    return result, files


def main(mode, arg=None):
    if mode == "frame":
        result, files = capture("frame", arg)
        page = result["pages"][0]
        if page["status"] != 200 or not page["rows"]:
            raise SystemExit(f"Capcom frame page for {arg} did not load: {page}")
        for name, data in files.items():
            kind = "table rows as rendered" if name.endswith(".json") else "full rendered page"
            snap.record(f"capcom/{name}", data, url=page["url"], route="headless Chromium", family="capcom",
                        independence_group="capcom-official", note=f"{kind}; page title {page['title']!r}",
                        rows=page["rows"] if name.endswith(".json") else None)
        print(f"{arg}: HTTP {page['status']}, {page['rows']} table rows")
    elif mode == "patches":
        result, files = capture("patches")
        by_file = {p.get("file", "versions.json"): p for p in result["pages"]}
        for name, data in files.items():
            page = by_file[name]
            snap.record(f"capcom/{name}", data, url=page["url"], route="headless Chromium", family="capcom",
                        independence_group="capcom-official", http_status=page["status"],
                        note=f"page title {page['title']!r}")
            print(f"{name}: HTTP {page['status']}, {len(data)} bytes")
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main(*sys.argv[1:3])
