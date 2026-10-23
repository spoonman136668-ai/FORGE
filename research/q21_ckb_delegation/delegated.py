"""Q21 delegated *execution worker*; CKB remains the sole research authority.

FORGE is a cross-platform runtime only. A manually supplied CKB run ID is a
lookup hint, never authority. Verify the CKB owner's live GitHub run, one-time
first-use history, successful owner-once job, exact admitted source tree, and
the FORGE worker's own non-replayed owner dispatch before loading any model.
The deployed CKB source is the already-qualified protected main at
3fc3b5ddd6d5a105a95ea83dbabaccc989dc6dbc; no draft PR #600 dependency.
Source-free prospective Q21 development only. No protected first-use.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
MIRROR = HERE.parent / "q21_ckb_native_mirror"
sys.path.insert(0, str(MIRROR))
import admit_exact as owner
import execute_dev as ckbdev

WORKFLOW = "q21-forge-delegated-development.yml"
CKB_AUTHORIZED_COMMIT = "3fc3b5ddd6d5a105a95ea83dbabaccc989dc6dbc"
CKB_TREE = "2ae819ca348a90827595f7dbcbfcf7d412deeb67"
CKB_WORKFLOW_BLOB = "ef0689ed1ad7de7a93af73a8ccc63224942ff03d"
CKB_OWNER_TEST_BLOB = "ea99a2a92c431087e885c7ccc8ee93bc9728fd97"
SOURCE = owner.SOURCE
SCOPE = "FRESH_Q21_FIT_TRAIN_FIT_VALID_DEV_ONLY"


class Blocked(RuntimeError):
    pass


def need(ok, why):
    if not ok:
        raise Blocked("Q21_DELEGATE_" + why)


def nonnegative_id(value):
    need(isinstance(value, str) and value.isdecimal() and int(value)>0,
         "OWNER_RUN_ID_UNSAFE")
    return int(value)


def history(get, repo, workflow, actual_run):
    listing = get("/repos/" + repo + "/actions/workflows/" + workflow +
                  "/runs?event=workflow_dispatch&per_page=100")
    runs = listing.get("workflow_runs")
    need(listing.get("total_count") == 1 and type(runs) is list and
         len(runs) == 1 and runs[0].get("id") == actual_run,
         "FIRST_USE_HISTORY_CONSUMED_OR_INCOMPLETE")


def attest(owner_run_id, env, get):
    need(env.get("GITHUB_REPOSITORY") == owner.FORGE and
         env.get("GITHUB_EVENT_NAME") == "workflow_dispatch" and
         env.get("GITHUB_REF") == "refs/heads/main" and
         env.get("GITHUB_RUN_ATTEMPT") == "1" and
         env.get("GITHUB_ACTOR") == owner.OWNER and
         env.get("GITHUB_WORKFLOW_REF") ==
             owner.FORGE + "/.github/workflows/" + WORKFLOW + "@refs/heads/main",
         "NOT_OWNER_DISPATCH_ON_PROTECTED_FORGE_MAIN")
    current = nonnegative_id(env.get("GITHUB_RUN_ID", ""))
    ckb_id = nonnegative_id(str(owner_run_id))
    sha = env.get("GITHUB_SHA")
    need(type(sha) is str and len(sha)==40 and
         all(c in "0123456789abcdef" for c in sha), "FORGE_RUN_SOURCE_INVALID")
    active = get("/repos/" + owner.FORGE + "/actions/runs/" + str(current))
    need(active.get("id")==current and active.get("head_sha")==sha and
         active.get("head_branch")=="main" and
         active.get("event")=="workflow_dispatch" and
         active.get("path")==".github/workflows/"+WORKFLOW and
         active.get("run_attempt")==1 and
         (active.get("actor") or {}).get("login")==owner.OWNER and
         (active.get("triggering_actor") or {}).get("login")==owner.OWNER and
         active.get("status") in ("queued","in_progress") and
         active.get("conclusion") is None,
         "FORGE_DISPATCH_NOT_AUTHENTICATED")
    history(get, owner.FORGE, WORKFLOW, current)

    ckb = get("/repos/" + owner.CKB + "/actions/runs/" + str(ckb_id))
    need(ckb.get("id")==ckb_id and
         ckb.get("event")=="workflow_dispatch" and
         ckb.get("head_branch")=="main" and
         ckb.get("path")==".github/workflows/"+owner.WORKFLOW and
         ckb.get("run_attempt")==1 and
         (ckb.get("actor") or {}).get("login")==owner.OWNER and
         (ckb.get("triggering_actor") or {}).get("login")==owner.OWNER and
         ckb.get("status") in ("in_progress","completed") and
         ckb.get("conclusion") in (None,"success"),
         "CKB_OWNER_RUN_NOT_AUTHENTICATED")
    history(get, owner.CKB, owner.WORKFLOW, ckb_id)

    ckb_sha = ckb.get("head_sha")
    need(ckb_sha == CKB_AUTHORIZED_COMMIT,
         "CKB_DEPLOYED_OWNER_SOURCE_NOT_EXACT")
    tree = get("/repos/" + owner.CKB + "/git/commits/" + ckb_sha)
    need((tree.get("tree") or {}).get("sha") == CKB_TREE,
         "CKB_AUTHORIZED_EXACT_TREE_DRIFT")
    for path, digest in (
        (".github/workflows/"+owner.WORKFLOW, CKB_WORKFLOW_BLOB),
        ("research/q21/admit_exact.py", "cebda244cf0899e60ef07162969b594340b67b74"),
        ("research/q21/test_admit_exact.py", CKB_OWNER_TEST_BLOB),
    ):
        item = get("/repos/" + owner.CKB + "/contents/"+path+"?ref="+ckb_sha)
        need(item.get("sha")==digest and item.get("type")=="file",
             "CKB_AUTHENTICATED_SOURCE_BYTES_DRIFT")

    jobs = get("/repos/"+owner.CKB+"/actions/runs/"+str(ckb_id)+
               "/jobs?per_page=100")
    named = jobs.get("jobs")
    need(type(named) is list and jobs.get("total_count")==len(named),
         "CKB_JOB_HISTORY_TRUNCATED")
    gates = [x for x in named if x.get("name")=="owner-once"]
    need(len(gates)==1 and gates[0].get("status")=="completed" and
         gates[0].get("conclusion")=="success",
         "CKB_OWNER_ADMISSION_JOB_NOT_SUCCESS")

    receipts = get("/repos/"+owner.CKB+"/actions/runs/"+str(ckb_id)+
                   "/artifacts?per_page=100")
    rows = receipts.get("artifacts")
    need(type(rows) is list and receipts.get("total_count")==len(rows),
         "CKB_OWNER_ARTIFACT_HISTORY_TRUNCATED")
    selected = [x for x in rows if
                x.get("name")=="q21-owner-admission-"+str(ckb_id)]
    need(len(selected)==1 and selected[0].get("expired") is False and
         type(selected[0].get("size_in_bytes")) is int and
         0<selected[0]["size_in_bytes"]<=100000,
         "OWNER_ADMISSION_RECEIPT_MISSING")
    return {"ckb_run_id":ckb_id, "ckb_source_sha":ckb_sha,
            "forge_delegate_run_id":current, "forge_delegate_source_sha":sha,
            "scope":SCOPE}


def execute(env, ckb_id, candidate, output, get):
    # The two authenticated first-use histories and CKB owner-success
    # precede every access to the sourcefree generator or fit data.
    auth = attest(ckb_id, env, get)
    ckbdev.verify_source(candidate)
    need(output.is_absolute() and not output.exists(), "OUTPUT_EXISTS_OR_RELATIVE")
    system = ckbdev.native_os()
    sourcefree, runner, checker = ckbdev.sourcefree_import(candidate)
    need(sourcefree.PROTOCOL_BLOB==owner.PROTOCOL, "FROZEN_PROTOCOL_DRIFT")
    report = runner.execute_development(sourcefree.protocol())
    envelope = {"schema":"forge.q21.external-readonly-envelope.v1",
                "os_name":system, "candidate_source_sha":owner.SOURCE,
                "ckb_owner_run_id":auth["ckb_run_id"],
                "ckb_owner_source_sha":auth["ckb_source_sha"],
                "ckb_owner_scope":auth["scope"], "scientific_first_use":False,
                "forge_delegate_run_id":auth["forge_delegate_run_id"],
                "runner_report":report}
    raw=(json.dumps(envelope,sort_keys=True,separators=(",",":"),
                    allow_nan=False)+"\n").encode("utf-8")
    with output.open("xb") as handle: handle.write(raw)
    return {"os":system, "sha256":hashlib.sha256(raw).hexdigest(),
            "ckb_run_id":auth["ckb_run_id"], "bytes":len(raw),
            "frozen_preliminary_decision":report["frozen_preliminary_decision"],
            "protected_scientific_first_use":False}


def preflight():
    return {"schema":"forge.q21.ckb-delegation.sourceonly.v1",
            "owner_admission":"NOT_REQUESTED", "q21_episodes_generated":0,
            "development_execution":"NOT_PERFORMED",
            "delegated_authority":"NONE"}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--mode",required=True,choices=("preflight","run"))
    parser.add_argument("--ckb-run-id")
    parser.add_argument("--candidate")
    parser.add_argument("--output")
    args=parser.parse_args()
    if args.mode=="preflight":
        print(json.dumps(preflight(),sort_keys=True)); return
    need(bool(args.ckb_run_id and args.candidate and args.output),
         "MISSING_INPUT")
    token=os.environ.get("GH_TOKEN","")
    output=Path(args.output).resolve()
    try:
        receipt=execute(dict(os.environ),args.ckb_run_id,
                        Path(args.candidate).resolve(),output,
                        lambda route:owner.github_get(token,route))
    except Exception as err:
        # Preserve the possibility of consumed prospective data after any
        # failure. Do not misclassify a partial result as a new qualified run.
        if output.is_absolute() and not output.exists():
            abort={"schema":"forge.q21.ckb-delegated.abort.v1",
                   "status":"ABORTED_ONE_SHOT_NO_RETRY",
                   "ckb_run_id":str(args.ckb_run_id),
                   "possible_development_cohorts_consumed":True,
                   "protected_scientific_first_use":False,
                   "failure_type":type(err).__name__}
            try:
                with output.open("xb") as h:
                    h.write((json.dumps(abort,sort_keys=True)+"\n").encode())
            except OSError: pass
        raise
    print(json.dumps(receipt,sort_keys=True))


if __name__=="__main__":
    main()
