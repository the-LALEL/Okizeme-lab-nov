"""Source snapshots: a saved copy of a source with its date, revision and fingerprint.

Raw copies go to sources/raw/ (never committed: this repository is public).
sources/manifest.json is committed and records, for every snapshot, where it came
from, when, and its sha256, so any later reader can tell whether a re-fetch matches.

Builds read snapshots only; they never fetch.
"""
import datetime
import hashlib
import json
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "sources" / "raw"
MANIFEST = ROOT / "sources" / "manifest.json"
USER_AGENT = "okizeme-lab-research/0.1 (personal frame-data research)"


def load_manifest():
    return json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}


def save_manifest(manifest):
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest, indent=1, sort_keys=True, ensure_ascii=False) + "\n")


def record(snapshot_id, data, *, url, route, family, independence_group, note="", **extra):
    """Store bytes under sources/raw/<snapshot_id> and register them in the manifest."""
    path = RAW / snapshot_id
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    manifest = load_manifest()
    previous = manifest.get(snapshot_id, {})
    entry = {
        "url": url,
        "route": route,
        "family": family,
        "independence_group": independence_group,
        # an unchanged source keeps the date it was first saved, so re-runs are reproducible
        "retrieved_on": previous["retrieved_on"] if previous.get("sha256") == hashlib.sha256(data).hexdigest()
        else datetime.date.today().isoformat(),
        "sha256": hashlib.sha256(data).hexdigest(),
        "bytes": len(data),
    }
    if note:
        entry["note"] = note
    entry.update({k: v for k, v in extra.items() if v is not None})
    manifest[snapshot_id] = entry
    save_manifest(manifest)
    return path


def fetch(url, timeout=60):
    """Fetch bytes with curl through the session proxy. Raises on a non-200 answer."""
    proc = subprocess.run(
        ["curl", "-sS", "-m", str(timeout), "-A", USER_AGENT, "-w", "\n%{http_code}", url],
        capture_output=True, check=True)
    body, _, code = proc.stdout.rpartition(b"\n")
    if code != b"200":
        raise RuntimeError(f"{url} answered HTTP {code.decode()}")
    return body


def read(snapshot_id):
    """Read a snapshot and check it still matches the manifest fingerprint."""
    data = (RAW / snapshot_id).read_bytes()
    want = load_manifest()[snapshot_id]["sha256"]
    if hashlib.sha256(data).hexdigest() != want:
        raise RuntimeError(f"snapshot {snapshot_id} does not match its manifest fingerprint")
    return data
