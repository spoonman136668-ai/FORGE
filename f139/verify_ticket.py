"""F139 GitHub-hosted development worker ticket and receipt, no scientific grant."""
from __future__ import annotations
import argparse
import hashlib
import hmac
import json
import os
from pathlib import Path
import re

REPO = "spoonman136668-ai/FORGE"
WORKFLOW = "forge-f139-development-worker.yml"
SCHEMA = "forge.f139.development-worker-receipt.v1"
SHA = re.compile(r"[a-f0-9]{40}\Z")
TICKET = re.compile(r"f139-[a-z0-9][a-z0-9-]{2,47}\Z")
LANES = {"Wingless", "Yggdrasil", "Qualification"}
D2K_PACKAGES = {"./planner", "./dreamrsi", "./optimizerstages"}
D2K_RECEIPT_SCHEMA = "forge.f139.d2k.package-diagnostic-receipt.v1"
D2K_DIAGNOSTIC_SCHEMA = "forge.f139.d2k.package-diagnostic.v1"

class Untrusted(ValueError):
    pass

def demand(ok, reason):
    if not ok:
        raise Untrusted("F139_" + reason)

def signature(secret, ticket, lane, source_sha, epoch, *,
              issue_number="", issue_id="", body_sha256="", target_package=""):
    demand(isinstance(secret, str) and len(secret) >= 32, "NO_WORKER_KEY")
    demand(isinstance(ticket, str) and TICKET.fullmatch(ticket)
           and lane in LANES and isinstance(source_sha, str)
           and SHA.fullmatch(source_sha)
           and isinstance(epoch, str) and re.fullmatch(r"[1-9][0-9]*", epoch),
           "DISPATCH_FIELDS_INVALID")
    if ticket.startswith("f139-d2k-"):
        demand(re.fullmatch(r"[1-9][0-9]*", issue_number) is not None
               and re.fullmatch(r"[1-9][0-9]*", issue_id) is not None
               and re.fullmatch(r"[a-f0-9]{64}", body_sha256) is not None
               and target_package in D2K_PACKAGES
               and ticket == "f139-d2k-i" + issue_number + "-" +
                   source_sha[:12] + "-" + body_sha256[:8],
               "D2K_SIGNED_ISSUE_FIELDS_INVALID")
        fields = ("F139-DISPATCH-V2", REPO, WORKFLOW, ticket, lane,
                  source_sha, epoch, issue_number, issue_id,
                  body_sha256, target_package)
    else:
        demand(not (issue_number or issue_id or body_sha256 or target_package),
               "UNEXPECTED_D2K_WORK_FIELDS")
        fields = ("F139-DISPATCH-V1", REPO, WORKFLOW, ticket, lane,
                  source_sha, epoch)
    raw = "\n".join(fields) + "\n"
    return hmac.new(secret.encode(), raw.encode(), hashlib.sha256).hexdigest()

def admit(inputs):
    expected = signature(inputs.get("key"), inputs.get("ticket"), inputs.get("lane"),
                         inputs.get("source_sha"), inputs.get("epoch"),
                         issue_number=inputs.get("issue_number",""),
                         issue_id=inputs.get("issue_id",""),
                         body_sha256=inputs.get("body_sha256",""),
                         target_package=inputs.get("target_package",""))
    actual = inputs.get("signature")
    demand(isinstance(actual, str) and re.fullmatch(r"[a-f0-9]{64}", actual)
           and hmac.compare_digest(actual, expected), "TICKET_SIGNATURE_REJECTED")
    demand(inputs.get("repository") == REPO
           and inputs.get("ref") in (
               "refs/heads/main",
               "refs/heads/f139-owner-release-"+inputs.get("source_sha",""))
           and inputs.get("event") == "workflow_dispatch"
           and inputs.get("head_sha") == inputs.get("source_sha")
           and inputs.get("run_attempt") == "1"
           and re.fullmatch(r"[1-9][0-9]*", inputs.get("run_id", "")),
           "GITHUB_SOURCE_OR_EVENT_DRIFT")
    demand(inputs.get("os") in {"windows-latest", "ubuntu-latest"}, "OS_UNTRUSTED")
    return True

def receipt(inputs, advisory_raw):
    admit(inputs)
    demand(not inputs["ticket"].startswith("f139-d2k-"),
           "D2K_DIAGNOSTIC_REQUIRED")
    demand(isinstance(advisory_raw, bytes) and 0 < len(advisory_raw) < 2_000_000,
           "MODEL_FREE_ADVISORY_MISSING")
    try:
        data = json.loads(advisory_raw)
    except (ValueError, UnicodeDecodeError) as exc:
        raise Untrusted("F139_ADVISORY_NOT_JSON") from exc
    demand(isinstance(data, dict)
           and data.get("schema") == "forge.model-free.two-lane-untested-advisory.v1"
           and data.get("source_commit_sha") == inputs["head_sha"]
           and data.get("scientific_first_use_authorized") is False
           and data.get("real_research_progress_established") is False
           and data.get("policy_promotion_authorized") is False
           and data.get("accepted_ref_mutations") == 0
           and data.get("new_scientific_originals") == 0
           and data.get("model_invocations") == 0
           and data.get("codex_invocations") == 0
           and isinstance(data.get("lanes"), list)
           and [item.get("lane") for item in data["lanes"]] == ["Wingless", "Yggdrasil"],
           "ADVISORY_FALSE_SCIENCE_OR_IDENTITY")
    return {"schema": SCHEMA, "ticket": inputs["ticket"],
            "lane": inputs["lane"], "epoch": int(inputs["epoch"]),
            "run_id": int(inputs["run_id"]), "os": inputs["os"],
            "source_sha": inputs["head_sha"],
            "model_free_advisory_sha256": hashlib.sha256(advisory_raw).hexdigest(),
            "development_only": True, "scientific_first_use_authorized": False,
            "scientific_originals_dispatched": 0, "accepted_ref_mutations": 0,
            "paid_model_calls": 0, "codex_calls": 0}

def diagnostic_receipt(inputs, diagnostic_raw):
    """Authenticate a measured, issue-specific source diagnostic, including negatives."""
    admit(inputs)
    demand(inputs["ticket"].startswith("f139-d2k-")
           and isinstance(diagnostic_raw, bytes)
           and 0 < len(diagnostic_raw) <= 32768, "D2K_DIAGNOSTIC_MISSING")
    try:
        diagnostic = json.loads(diagnostic_raw)
    except (ValueError, UnicodeDecodeError) as exc:
        raise Untrusted("F139_D2K_DIAGNOSTIC_INVALID_JSON") from exc
    demand(isinstance(diagnostic, dict) and set(diagnostic) == {
        "schema", "source_sha", "issue_number", "issue_id", "body_sha256",
        "target_package", "run_id", "os", "outcome", "returncode",
        "duration_ms", "output_sha256", "output_excerpt", "output_bytes",
        "scientific_first_use", "paid_model_calls",
    }, "D2K_DIAGNOSTIC_FIELDS")
    demand(diagnostic["schema"] == D2K_DIAGNOSTIC_SCHEMA
           and diagnostic["source_sha"] == inputs["head_sha"]
           and str(diagnostic["issue_number"]) == inputs["issue_number"]
           and str(diagnostic["issue_id"]) == inputs["issue_id"]
           and diagnostic["body_sha256"] == inputs["body_sha256"]
           and diagnostic["target_package"] == inputs["target_package"]
           and str(diagnostic["run_id"]) == inputs["run_id"]
           and diagnostic["os"] == inputs["os"]
           and diagnostic["outcome"] in {"PASS", "TEST_FAILURE", "TIMEOUT"}
           and type(diagnostic["returncode"]) is int
           and -1 <= diagnostic["returncode"] <= 255
           and type(diagnostic["duration_ms"]) is int
           and 0 <= diagnostic["duration_ms"] <= 120000
           and isinstance(diagnostic["output_excerpt"],str)
           and len(diagnostic["output_excerpt"].encode()) <= 16384
           and type(diagnostic["output_bytes"]) is int
           and 0 <= diagnostic["output_bytes"] <= 100000
           and re.fullmatch(r"[a-f0-9]{64}", diagnostic["output_sha256"])
           and diagnostic["scientific_first_use"] is False
           and diagnostic["paid_model_calls"] == 0,
           "D2K_DIAGNOSTIC_IDENTITY_OR_BUDGET")
    demand((diagnostic["outcome"] == "PASS" and diagnostic["returncode"] == 0)
           or (diagnostic["outcome"] == "TIMEOUT" and diagnostic["returncode"] == -1)
           or (diagnostic["outcome"] == "TEST_FAILURE" and diagnostic["returncode"] > 0),
           "D2K_DIAGNOSTIC_OUTCOME_FALSE")
    return {
        "schema": D2K_RECEIPT_SCHEMA,
        "ticket": inputs["ticket"], "lane": inputs["lane"],
        "source_sha": inputs["head_sha"], "epoch":int(inputs["epoch"]),
        "run_id":int(inputs["run_id"]), "os":inputs["os"],
        "issue_number":int(inputs["issue_number"]),
        "issue_id":int(inputs["issue_id"]),
        "body_sha256":inputs["body_sha256"],
        "target_package":inputs["target_package"],
        "diagnostic_sha256":hashlib.sha256(diagnostic_raw).hexdigest(),
        "outcome":diagnostic["outcome"],
        "development_only":True, "scientific_first_use_authorized":False,
        "scientific_originals_dispatched":0, "accepted_ref_mutations":0,
        "paid_model_calls":0, "codex_calls":0,
    }

def inputs_from_env():
    names = {
        "key":"F139_WORKER_HMAC_KEY", "ticket":"F139_TICKET",
        "lane":"F139_LANE", "source_sha":"F139_SOURCE_SHA",
        "epoch":"F139_EPOCH", "signature":"F139_SIGNATURE",
        "repository":"GITHUB_REPOSITORY", "ref":"GITHUB_REF",
        "event":"GITHUB_EVENT_NAME", "head_sha":"GITHUB_SHA",
        "run_attempt":"GITHUB_RUN_ATTEMPT", "run_id":"GITHUB_RUN_ID",
        "os":"F139_RUNNER_OS",
        "issue_number":"F139_ISSUE_NUMBER", "issue_id":"F139_ISSUE_ID",
        "body_sha256":"F139_BODY_SHA256",
        "target_package":"F139_TARGET_PACKAGE",
    }
    return {key:os.environ.get(value, "") for key,value in names.items()}

def main():
    p=argparse.ArgumentParser()
    group=p.add_mutually_exclusive_group(required=True)
    group.add_argument("--advisory",type=Path)
    group.add_argument("--diagnostic",type=Path)
    p.add_argument("--output-dir",type=Path,required=True)
    args=p.parse_args()
    root=args.output_dir
    demand(root.is_dir() and not (root/"f139-receipt.json").exists(),
           "RECEIPT_PATH_EXISTS")
    inputs=inputs_from_env()
    if args.diagnostic:
        data=diagnostic_receipt(inputs,args.diagnostic.read_bytes())
    else:
        data=receipt(inputs,args.advisory.read_bytes())
    raw=(json.dumps(data,sort_keys=True,separators=(",",":"))+"\n").encode()
    with (root/"f139-receipt.json").open("xb") as f:
        f.write(raw)
    with (root/"f139-receipt.sha256").open("xb") as f:
        f.write((hashlib.sha256(raw).hexdigest()+"  f139-receipt.json\n").encode())
    print("F139_DEV_WORKER_SIGNED_TICKET_AND_RECEIPT=PASS")
    print("F139_NEW_ORIGINAL_SCIENCE=ZERO")

if __name__=="__main__":
    try:
        main()
    except (Untrusted,OSError) as e:
        raise SystemExit("F139_WORKER_FAIL_CLOSED "+str(e)) from e
