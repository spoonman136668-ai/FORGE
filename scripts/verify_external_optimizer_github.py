#!/usr/bin/env python3
"""Verify *public GitHub run and artifact metadata*, never raw original ZIPs.

This authenticates current HTTPS API metadata against independently recorded
source identities. It does NOT establish artifact-byte integrity, source-birth
custody, scientific results, signed Dream histories, or optimizer causality.
"""
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

API = "https://api.github.com/repos/spoonman136668-ai/"
MAX_RESPONSE = 1_000_000

def get_json(url: str) -> dict:
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    failure = None
    for authenticated in ((True, False) if token else (False,)):
        headers = {
            "User-Agent": "forge-external-optimizer-intake-source-only",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if authenticated:
            headers["Authorization"] = "Bearer " + token
        req = urllib.request.Request(url, headers=headers, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=20) as response:
                if response.status != 200:
                    raise RuntimeError("non-200 GitHub metadata")
                payload = response.read(MAX_RESPONSE + 1)
            if len(payload) > MAX_RESPONSE:
                raise RuntimeError("GitHub metadata response exceeded bound")
            return json.loads(payload)
        except urllib.error.HTTPError as exc:
            failure = f"HTTP {exc.code}"
            if authenticated and exc.code in (401, 403, 404):
                continue
            break
        except (OSError, ValueError, RuntimeError) as exc:
            failure = type(exc).__name__
            break
    raise RuntimeError("GitHub metadata unavailable: " + str(failure))

def verify(path: str) -> None:
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    assert doc["schema"] == "forge.optimizer.external-training-observations.v1"
    assert doc["mode"] == "READ_ONLY_GITHUB_TRAIN_ONLY_NOT_SIGNED_POLICY_HISTORY"
    rows = doc["studies"]
    assert len(rows) in (8, 12)
    unique_run = set()
    unique_artifact = set()
    for item in rows:
        lane = item["lane"]
        assert lane in ("Wingless", "Yggdrasil")
        assert item["scientific_gate"] == "FAILED_PREREGISTERED_TRAIN_ONLY"
        assert not any(item[x] for x in (
            "original_first_use", "randomized_optimizer_assignment",
            "independent_source_custody", "scientific_accepted"))
        assert re.fullmatch("[a-f0-9]{40}", item["head_sha"])
        assert re.fullmatch("[a-f0-9]{64}", item["artifact_sha256"])
        rid, aid = item["run_id"], item["artifact_id"]
        assert rid not in unique_run and aid not in unique_artifact
        unique_run.add(rid)
        unique_artifact.add(aid)
        base = API + lane + "/actions/runs/" + str(rid)
        run = get_json(base)
        assert run["id"] == rid
        assert run["status"] == "completed" and run["conclusion"] == "success"
        assert run["run_attempt"] == 1 and run["event"] == "push"
        assert run["head_sha"] == item["head_sha"]
        assert run["path"] == item["workflow_path"]
        assert run["repository"]["full_name"] == "spoonman136668-ai/" + lane
        result = get_json(base + "/artifacts?per_page=100")
        matches = [x for x in result.get("artifacts", []) if x.get("id") == aid]
        assert len(matches) == 1
        art = matches[0]
        assert not art["expired"] and art["size_in_bytes"] > 0
        assert art["name"] == item["artifact_name"]
        assert art["digest"] == "sha256:" + item["artifact_sha256"]
        assert art["workflow_run"]["id"] == rid
        assert art["workflow_run"]["head_sha"] == item["head_sha"]
    print("FORGE_EXTERNAL_GITHUB_RUN_ARTIFACT_METADATA_MATCHED=" + str(len(rows)))
    print("FORGE_EXTERNAL_STUDY_RESULT_ZIPS_BYTE_VERIFIED=FALSE")
    print("FORGE_EXTERNAL_SIGNED_RANDOMIZED_POLICY_HISTORY=FALSE")
    print("FORGE_EXTERNAL_ORIGINAL_FIRST_USES_CONSUMED=0")
    print("FORGE_EXTERNAL_OPTIMIZER_LIVE_DISPATCH_AUTHORIZED=FALSE")

if __name__ == "__main__":
    if len(sys.argv) != 2 or not Path(sys.argv[1]).is_file():
        raise SystemExit("Usage: verify_external_optimizer_github.py <existing manifest>")
    try:
        verify(sys.argv[1])
    except (AssertionError, RuntimeError, ValueError, KeyError, TypeError, OSError) as exc:
        print("FORGE_EXTERNAL_GITHUB_METADATA_NOT_VERIFIED:" + type(exc).__name__, file=sys.stderr)
        raise SystemExit(1)
