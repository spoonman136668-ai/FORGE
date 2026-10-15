"""R20B: authenticate six historical source Git blobs and run chronology, READ ONLY.

GitHub identity/clock evidence is NOT independent source-birth, first-use,
scientific acceptance, or optimizer admission. No CLI write operations.
"""
import datetime
import json
import os
import pathlib
import sys
import urllib.error
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "reference/research-originals/20261013-six-recent-archive-cohort.json"
PINS = ROOT / "reference/research-originals/20261015-r20-prereg-source-observations.json"
SCHEMA = "forge.research-archive.r20-source-prereg-observations.v1"
URL = "https://api.github.com/repos/spoonman136668-ai/"
MAX_RESPONSE = 256 * 1024

class Blocked(ValueError):
    pass

def no_dupes(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise Blocked("DUPLICATE_JSON_KEY")
        out[key] = value
    return out

def decode(raw):
    if not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_RESPONSE:
        raise Blocked("JSON_SIZE")
    try:
        return json.loads(raw, object_pairs_hook=no_dupes)
    except (ValueError, UnicodeDecodeError) as exc:
        raise Blocked("INVALID_JSON") from exc

def timestamp(value):
    if not isinstance(value, str) or not value.endswith("Z"):
        raise Blocked("TIMESTAMP_FORMAT")
    try:
        return datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise Blocked("TIMESTAMP_FORMAT") from exc

def fixed_inputs(manifest, pins):
    if not isinstance(manifest, dict) or set(manifest) != {"schema", "entries"} or manifest["schema"] != "forge.research-archive.frozen-cohort.v1":
        raise Blocked("MANIFEST_SCHEMA")
    if not isinstance(pins, dict) or set(pins) != {"schema", "mode", "entries"} or pins["schema"] != SCHEMA or pins["mode"] != "GITHUB_IMMUTABLE_BLOBS_ONLY_NOT_INDEPENDENT_CUSTODY":
        raise Blocked("PIN_SCHEMA")
    src, records = manifest["entries"], pins["entries"]
    if not isinstance(src, list) or not isinstance(records, list) or len(src) != 6 or len(records) != 6:
        raise Blocked("COHORT_SIZE")
    seen = set()
    for row, pin in zip(src, records):
        if not isinstance(row, dict) or not isinstance(pin, dict):
            raise Blocked("SOURCE_SHAPE")
        lane, exp = row.get("lane"), row.get("experiment")
        if lane not in ("Wingless", "Yggdrasil") or (lane, exp) in seen:
            raise Blocked("SOURCE_LANE")
        seen.add((lane, exp))
        if row.get("repository") != "spoonman136668-ai/" + lane or pin.get("repository") != row["repository"] or pin.get("lane") != lane or pin.get("experiment") != exp or pin.get("source_head_sha") != row.get("head_sha"):
            raise Blocked("SOURCE_PIN_DRIFT")
        if any(pin.get(k) is not False for k in ("independent_source_birth_proven", "complete_first_use_reconciled", "scientific_accepted")):
            raise Blocked("FALSE_AUTHORITY")
        p = pin.get("prereg_path")
        h = pin.get("prereg_git_blob_sha")
        if not isinstance(p, str) or not p.startswith("research/contrib/chatgpt/20261013-") or not p.endswith(("/pre.json", "/prereg.json")) or ".." in p or "\\" in p or len(p) > 180:
            raise Blocked("PREREG_PATH")
        if not isinstance(h, str) or len(h) != 40 or any(c not in "0123456789abcdef" for c in h):
            raise Blocked("PREREG_BLOB")
    if sorted(lane for lane, _ in seen) != ["Wingless"] * 3 + ["Yggdrasil"] * 3:
        raise Blocked("LANE_SPLIT")
    return src, records

def audit(manifest, pins, fetch):
    """fetch(lane, suffix) returns decoded GitHub REST JSON; no authority mutation."""
    src, records = fixed_inputs(manifest, pins)
    observed = []
    for row, pin in zip(src, records):
        lane, runid, head = row["lane"], row["run_id"], row["head_sha"]
        run = fetch(lane, "actions/runs/" + str(runid))
        commit = fetch(lane, "commits/" + head)
        content = fetch(lane, "contents/" + pin["prereg_path"] + "?ref=" + head)
        if not all(isinstance(obj, dict) for obj in (run, commit, content)):
            raise Blocked("GITHUB_RESPONSE_SHAPE")
        if (run.get("id") != runid or run.get("run_attempt") != 1 or
            run.get("head_sha") != head or run.get("event") != "push" or
            run.get("status") != "completed" or run.get("conclusion") != "success" or
            run.get("path") != row["workflow_path"] or
            not isinstance(run.get("repository"), dict) or run["repository"].get("full_name") != row["repository"] or
            commit.get("sha") != head or content.get("type") != "file" or
            content.get("path") != pin["prereg_path"] or content.get("sha") != pin["prereg_git_blob_sha"]):
            raise Blocked("LIVE_SOURCE_OR_BLOB_DRIFT")
        commit_obj = commit.get("commit")
        committer = commit_obj.get("committer") if isinstance(commit_obj, dict) else None
        if not isinstance(committer, dict) or timestamp(committer.get("date")) > timestamp(run.get("created_at")):
            raise Blocked("OBSERVED_COMMIT_RUN_CHRONOLOGY_DRIFT")
        observed.append((lane, row["experiment"], head, pin["prereg_git_blob_sha"]))
    return {
        "schema": "forge.research-archive.r20b-github-source-observation.v1",
        "github_prereg_blob_observations": len(observed),
        "wingless_observations": 3,
        "yggdrasil_observations": 3,
        "github_source_run_chronology_consistent": True,
        "independent_source_birth_verified": False,
        "complete_first_use_reconciled": False,
        "external_signer_custody_verified": False,
        "scientific_accepted": False,
        "optimizer_promotion_authorized": False,
        "new_originals_executed": 0,
    }

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None

def live_fetch(lane, suffix):
    if lane not in ("Wingless", "Yggdrasil") or not isinstance(suffix, str) or not (
        suffix.startswith(("actions/runs/", "commits/", "contents/research/contrib/chatgpt/20261013-"))
    ):
        raise Blocked("INVALID_REQUEST_SCOPE")
    url = URL + lane + "/" + urllib.parse.quote(suffix, safe="/?=&-_.")
    token = os.environ.get("GH_TOKEN", "")
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "FORGE-R20B-readonly"}
    if token:
        headers["Authorization"] = "Bearer " + token
    request = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.build_opener(NoRedirect).open(request, timeout=15) as resp:
            if resp.status != 200:
                raise Blocked("REMOTE_STATUS")
            raw = resp.read(MAX_RESPONSE + 1)
    except (urllib.error.URLError, OSError) as exc:
        raise Blocked("GITHUB_READ_UNAVAILABLE") from exc
    return decode(raw)

def main():
    try:
        obs = audit(decode(MANIFEST.read_bytes()), decode(PINS.read_bytes()), live_fetch)
    except (Blocked, OSError, KeyError, TypeError) as exc:
        print("R20B_SOURCE_OBSERVATION=BLOCKED:" + type(exc).__name__, file=sys.stderr)
        return 1
    print(json.dumps(obs, sort_keys=True, separators=(",", ":")))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
