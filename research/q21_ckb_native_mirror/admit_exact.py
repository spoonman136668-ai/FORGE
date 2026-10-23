"""Authenticated one-shot FORGE Q21 source-free development owner admission.

Only the already-qualified CKB owner may invoke this inside its protected
workflow_dispatch context. GitHub metadata is fetched independently from the
API using a GitHub-issued token; caller-provided claims never suffice.
The GitHub Actions workflow history, including unsuccessful prior attempts,
forms a conservative first-use fence. No Q21 experiment is executed here.
"""
from __future__ import annotations
import argparse
import json
import os
from urllib.request import Request, build_opener, HTTPRedirectHandler

CKB = "spoonman136668-ai/ckb-plane"
FORGE = "spoonman136668-ai/FORGE"
OWNER = "spoonman136668-ai"
WORKFLOW = "q21-ckb-owner-once.yml"
SOURCE = "0d49a1cc01e9dff9db060ca0981beaf6748f3127"
TREE = "7142d128982091c478294854d02961b8f696325a"
PROTOCOL = "d7c35c10f80b36a758b78e0deedf36d74bf5767d"
CKB_INTAKE = "e9fafc82c4f0079f0687137ef0dc1251a5e7530e"
CKB_INTAKE_TESTS = "af6622bb4168a2011152b9f6773ac4e4bd0eb7d6"
CKB_QUAL_HEAD = "43363d900cd206e1a66c4346e3b5754b22a3465a"
CKB_QUAL_RUN = 39874952886
FORGE_FOCUSED_RUN = 39869808273
FORGE_FULL_RUN = 39869813788


class Refused(RuntimeError):
    pass


def need(condition: bool, code: str) -> None:
    if not condition:
        raise Refused("Q21_AUTH_" + code)


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, url):
        raise Refused("Q21_AUTH_REDIRECT_FORBIDDEN")


def github_get(token: str, route: str) -> dict:
    need(type(token) is str and len(token) >= 21 and
         not any(x in token for x in ("\r", "\n")), "NO_AUTHENTICATED_GITHUB_TOKEN")
    need(route.startswith("/repos/") and "\n" not in route and
         "\r" not in route and ".." not in route, "ROUTE_NOT_ALLOWED")
    req = Request("https://api.github.com" + route, headers={
        "Authorization": "Bearer " + token,
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "ckb-q21-one-shot"})
    with build_opener(NoRedirect()).open(req, timeout=18) as reply:
        need(reply.status == 200, "API_HTTP_NOT_OK")
        raw = reply.read(524289)
        need(len(raw) <= 524288, "API_RESPONSE_TOO_LARGE")
    obj = json.loads(raw)
    need(type(obj) is dict, "API_RESPONSE_INVALID")
    return obj


def current_context(env: dict) -> dict:
    need(env.get("GITHUB_REPOSITORY") == CKB, "WRONG_REPOSITORY")
    need(env.get("GITHUB_EVENT_NAME") == "workflow_dispatch", "NOT_OWNER_DISPATCH")
    need(env.get("GITHUB_REF") == "refs/heads/main", "NOT_PROTECTED_MAIN")
    need(env.get("GITHUB_RUN_ATTEMPT") == "1", "RERUN_FORBIDDEN")
    need(env.get("GITHUB_ACTOR") == OWNER, "NOT_CKB_OWNER")
    need(env.get("GITHUB_WORKFLOW_REF") ==
         CKB + "/.github/workflows/" + WORKFLOW + "@refs/heads/main",
         "WRONG_WORKFLOW")
    sha = env.get("GITHUB_SHA", "")
    need(type(sha) is str and len(sha) == 40 and
         all(c in "0123456789abcdef" for c in sha), "INVALID_CKB_SOURCE")
    run_id = env.get("GITHUB_RUN_ID", "")
    need(type(run_id) is str and run_id.isdecimal() and int(run_id) > 0,
         "INVALID_RUN_ID")
    return {"run_id": int(run_id), "ckb_sha": sha}


def fully_attested(ctx: dict, get) -> None:
    run = get("/repos/" + CKB + "/actions/runs/" + str(ctx["run_id"]))
    need(run.get("id") == ctx["run_id"] and
         run.get("event") == "workflow_dispatch" and
         run.get("run_attempt") == 1 and
         run.get("head_sha") == ctx["ckb_sha"] and
         run.get("head_branch") == "main" and
         run.get("path") == ".github/workflows/" + WORKFLOW and
         (run.get("actor") or {}).get("login") == OWNER and
         (run.get("triggering_actor") or {}).get("login") == OWNER and
         run.get("status") in ("queued", "in_progress") and
         run.get("conclusion") is None, "CURRENT_RUN_NOT_AUTHENTICATED")

    # A workflow_dispatch attempt consumes the only allowed one-shot,
    # whether it succeeded or failed; never retry or accept another dispatch.
    history = get("/repos/" + CKB + "/actions/workflows/" +
                  WORKFLOW + "/runs?event=workflow_dispatch&per_page=100")
    runs = history.get("workflow_runs")
    need(history.get("total_count") == 1 and type(runs) is list and
         len(runs) == 1 and runs[0].get("id") == ctx["run_id"],
         "FIRST_USE_ALREADY_CONSUMED_OR_HISTORY_INCOMPLETE")

    # CKB source-only native evidence and original Git objects must match.
    qualified = get("/repos/" + CKB + "/actions/runs/" + str(CKB_QUAL_RUN))
    need(qualified.get("id") == CKB_QUAL_RUN and
         qualified.get("status") == "completed" and
         qualified.get("conclusion") == "success" and
         qualified.get("head_sha") == CKB_QUAL_HEAD, "CKB_QUALIFICATION_UNVERIFIED")
    for path, expected in (
        ("snapshot/source/internal/plane/forge_q21_intake_v1.go", CKB_INTAKE),
        ("snapshot/source/internal/plane/forge_q21_intake_v1_test.go", CKB_INTAKE_TESTS)):
        doc = get("/repos/" + CKB + "/contents/" + path +
                  "?ref=" + ctx["ckb_sha"])
        need(doc.get("sha") == expected and doc.get("type") == "file",
             "CKB_INTAKE_SOURCE_CHANGED")

    commit = get("/repos/" + FORGE + "/git/commits/" + SOURCE)
    need((commit.get("tree") or {}).get("sha") == TREE,
         "FORGE_SOURCE_TREE_UNVERIFIED")
    blob = get("/repos/" + FORGE + "/git/blobs/" + PROTOCOL)
    need(blob.get("sha") == PROTOCOL, "FROZEN_PROTOCOL_UNVERIFIED")
    for run_id in (FORGE_FOCUSED_RUN, FORGE_FULL_RUN):
        qual = get("/repos/" + FORGE + "/actions/runs/" + str(run_id))
        need(qual.get("id") == run_id and
             qual.get("head_sha") == SOURCE and
             qual.get("conclusion") == "success" and
             qual.get("status") == "completed", "FORGE_QUALIFICATION_UNVERIFIED")
    focused_jobs = get("/repos/" + FORGE + "/actions/runs/" +
                       str(FORGE_FOCUSED_RUN) + "/jobs?per_page=100")
    jobs = focused_jobs.get("jobs")
    need(type(jobs) is list and focused_jobs.get("total_count") == len(jobs),
         "QUALIFIER_JOB_LIST_NOT_COMPLETE")
    need(any("windows" in str(j.get("name", "")).lower() and
             j.get("conclusion") == "success" for j in jobs) and
         any("ubuntu" in str(j.get("name", "")).lower() and
             j.get("conclusion") == "success" for j in jobs),
         "TWO_NATIVE_OPERATING_SYSTEMS_NOT_PROVEN")


def admit(env: dict, get) -> dict:
    ctx = current_context(env)
    fully_attested(ctx, get)
    return {
        "schema": "ckb.forge-q21.authenticated-one-shot.v1",
        "decision": "OWNER_AUTHENTICATED_SOURCEFREE_DEVELOPMENT_ONLY",
        "ckb_run_id": ctx["run_id"],
        "ckb_source_sha": ctx["ckb_sha"],
        "forge_source_sha": SOURCE,
        "forge_tree_sha": TREE,
        "frozen_protocol_blob": PROTOCOL,
        "scope": "FRESH_Q21_FIT_TRAIN_FIT_VALID_DEV_ONLY",
        "first_use_history": "SINGLE_CKB_WORKFLOW_DISPATCH_RUN",
        "no_original_or_protected_sources": True,
        "production_authority": False,
        "paid_external_models": False,
        "scientific_execution_performed": False
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("preflight", "admit"), required=True)
    args = parser.parse_args()
    if args.mode == "preflight":
        print(json.dumps({"status": "Q21_OWNER_AUTH_SOURCE_ONLY_PREFLIGHT",
                          "api_calls": 0, "scientific_execution": False},
                         sort_keys=True))
        return
    token = os.environ.get("GH_TOKEN", "")
    output = admit(dict(os.environ), lambda path: github_get(token, path))
    dest = os.environ.get("Q21_RECEIPT_PATH", "")
    need(dest and os.path.isabs(dest), "RECEIPT_PATH_NOT_ABSOLUTE")
    # Receipt is a local artifact of *this* authenticated admission only.
    # GitHub run history is the durable and fail-closed replay fence.
    with open(dest, "x", encoding="utf-8") as fd:
        json.dump(output, fd, sort_keys=True, separators=(",", ":"))
        fd.write("\n")
    print(json.dumps(output, sort_keys=True))


if __name__ == "__main__":
    main()
