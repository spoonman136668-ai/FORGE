#!/usr/bin/env python3
"""R21 existing-controller, read-only GitHub source audit.

This only observes source and independently hosted qualification. It NEVER
merges, changes GitHub state, signs FSA custody or starts experiments.
"""
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

REPO = "spoonman136668-ai/FORGE"
ROOT = f"https://api.github.com/repos/{REPO}"
BRANCH = re.compile(r"^proposal/fsa[a-zA-Z0-9/_-]*$")
SHA = re.compile(r"^[0-9a-f]{40}$")
PATH = re.compile(r"^(eligibility|startrecovery|fsaadmission)/[A-Za-z0-9_]+\.go$")
RULESET = 25031517
APP_ID = 15368
PUBLIC = ".github/workflows/qualify.yml"
FSA = ".github/workflows/qualify-fsa-source.yml"


class Blocked(Exception):
    pass


class GitHub:
    def __init__(self, transport=None, token=None):
        self.transport = transport or self._transport
        self.token = os.getenv("GH_TOKEN", "") if token is None else token

    def _transport(self, path):
        if not path.startswith("/") or path.startswith("//"):
            raise Blocked("BAD_GITHUB_PATH")
        req = urllib.request.Request(ROOT + path,
          headers={"Accept": "application/vnd.github+json",
                   "Authorization": "Bearer " + self.token,
                   "X-GitHub-Api-Version": "2022-11-28",
                   "User-Agent": "forge-r21-source-audit"})
        try:
            with urllib.request.urlopen(req, timeout=14) as response:
                if response.headers.get("Link", "").find('rel="next"') != -1:
                    raise Blocked("UNREAD_PAGINATION")
                raw = response.read(2000001)
                if len(raw) > 2000000:
                    raise Blocked("RESPONSE_TOO_LARGE")
                return json.loads(raw)
        except (urllib.error.URLError, ValueError, OSError) as e:
            raise Blocked("GITHUB_READ_FAILED") from e

    def get(self, path):
        if not path.startswith("/") or "//" in path or "://" in path:
            raise Blocked("UNSAFE_GITHUB_PATH")
        return self.transport(path)


def expect(cond, why):
    if not cond:
        raise Blocked(why)


def bounded_list(g, path, key=None, maximum=99):
    data = g.get(path)
    value = data.get(key) if key and isinstance(data, dict) else data
    expect(isinstance(value, list) and len(value) <= maximum,
           "MISSING_OR_UNBOUNDED_GITHUB_PAGE")
    return value


def current_main(g):
    base = g.get("/branches/main")
    expect(isinstance(base, dict) and base.get("protected") is True,
           "MAIN_NOT_PROTECTED")
    oid = base.get("commit", {}).get("sha", "")
    expect(isinstance(oid, str) and SHA.fullmatch(oid),
           "MAIN_COMMIT_UNQUALIFIED")
    return oid


def verify_ruleset(g):
    records = bounded_list(g, "/rulesets?includes_parents=true", maximum=20)
    expect(len(records) == 1 and records[0].get("id") == RULESET
           and records[0].get("enforcement") == "active",
           "RULESET_INVENTORY_CHANGED")
    r = g.get(f"/rulesets/{RULESET}")
    expect(r.get("id") == RULESET and r.get("name") == "FORGE main qualified-source only"
           and r.get("source") == REPO and r.get("target") == "branch"
           and r.get("enforcement") == "active"
           and r.get("conditions", {}).get("ref_name", {}) ==
                  {"include": ["refs/heads/main"], "exclude": []},
           "RULESET_SCOPE_CHANGED")
    # The ephemeral GitHub Actions token may omit bypass_actors. Missing
    # visibility is not the same as an authenticated empty bypass policy.
    expect(isinstance(r.get("bypass_actors"), list),
           "RULESET_BYPASS_VISIBILITY_MISSING")
    expect(r["bypass_actors"] == [] and
           r.get("current_user_can_bypass") == "never",
           "RULESET_BYPASS_OR_CALLER_UNQUALIFIED")
    rules = r.get("rules")
    expect(isinstance(rules, list) and len(rules) == 4,
           "RULESET_RULE_COUNT_CHANGED")
    mapped = {x.get("type"): x for x in rules if isinstance(x, dict)}
    expect(set(mapped) == {"deletion", "non_fast_forward",
                           "pull_request", "required_status_checks"},
           "RULESET_TYPES_CHANGED")
    a = mapped["pull_request"].get("parameters", {})
    expect(a.get("dismiss_stale_reviews_on_push") is True and
           a.get("required_review_thread_resolution") is True and
           a.get("allowed_merge_methods") == ["merge"] and
           a.get("required_approving_review_count") == 0 and
           a.get("require_extra_approval_for_unattributed_changes") is True,
           "RULESET_REVIEW_POLICY_CHANGED")
    a = mapped["required_status_checks"].get("parameters", {})
    checks = a.get("required_status_checks")
    expect(a.get("strict_required_status_checks_policy") is True and
           isinstance(checks, list) and len(checks) == 2 and
           {(x.get("context"), x.get("integration_id")) for x in checks}
             == {("linux", APP_ID), ("windows", APP_ID)},
           "RULESET_CHECK_POLICY_CHANGED")
    return True


def eligible(pr):
    try:
        return (pr["state"] == "open" and pr["draft"] is False
                and pr["user"]["login"] == "spoonman136668-ai"
                and pr["head"]["repo"]["full_name"] == REPO
                and pr["base"]["ref"] == "main"
                and BRANCH.fullmatch(pr["head"]["ref"]) is not None
                and SHA.fullmatch(pr["head"]["sha"]) is not None)
    except (TypeError, KeyError):
        return False


def verify_workflow(g, runs, sha, branch, workflow, event, jobs):
    matches = [r for r in runs if r.get("head_sha") == sha
               and r.get("head_branch") == branch
               and r.get("path") == workflow and r.get("event") == event
               and r.get("status") == "completed" and r.get("conclusion") == "success"
               and r.get("repository", {}).get("full_name") == REPO]
    expect(len(matches) == 1, "EXACT_HEAD_WORKFLOW_NOT_UNIQUE_OR_MISSING")
    run = matches[0]
    expect(isinstance(run.get("id"), int) and run["id"] > 0 and
           run.get("run_attempt") == 1, "UNQUALIFIED_WORKFLOW_ATTEMPT")
    results = bounded_list(g, f"/actions/runs/{run['id']}/jobs?per_page=100",
                           key="jobs")
    observed = {j.get("name"): j for j in results}
    expect(len(results) == len(jobs) and set(observed) == set(jobs),
           "WORKFLOW_JOB_SET_MISMATCH")
    expect(all(j.get("status") == "completed" and
               j.get("conclusion") == "success" and
               j.get("run_id") == run["id"] for j in results),
           "EXACT_HEAD_JOB_FAILED")
    return True


def audit_one(g, pr):
    result = {"PR": pr.get("number"), "HeadSHA": pr.get("head", {}).get("sha", ""),
              "SourceTestsQualified": False, "RulesetVisible": False,
              "MergeAuthorized": False, "ScientificAuthority": False,
              "Reason": "NOT_QUALIFIED"}
    try:
        expect(eligible(pr) and isinstance(pr.get("number"), int)
               and pr["number"] > 0, "NOT_AN_ELIGIBLE_SOURCE_PR")
        num, sha, branch = pr["number"], pr["head"]["sha"], pr["head"]["ref"]
        current = g.get(f"/pulls/{num}")
        expect(eligible(current) and current["head"]["sha"] == sha and
               current["head"]["ref"] == branch, "PR_MUTATED_BEFORE_AUDIT")
        base = current_main(g)
        expect(current["base"]["sha"] == base, "BASE_IDENTITY_CHANGED")
        files = bounded_list(g, f"/pulls/{num}/files?per_page=100", maximum=6)
        expect(bool(files) and all(f.get("status") in ("added", "modified")
               and isinstance(f.get("filename"), str) and
               PATH.fullmatch(f["filename"]) for f in files),
               "UNSAFE_SOURCE_DELTA")
        # An issue comment, self-attestation, or AI review is never an input.
        runs = bounded_list(g, f"/actions/runs?head_sha={sha}&per_page=100",
                            key="workflow_runs")
        verify_workflow(g, runs, sha, branch, PUBLIC, "pull_request",
                        {"linux", "windows"})
        verify_workflow(g, runs, sha, branch, FSA, "pull_request",
                        {"qualify (ubuntu-latest)", "qualify (windows-latest)"})
        result["SourceTestsQualified"] = True
        verify_ruleset(g)
        result["RulesetVisible"] = True
        late = g.get(f"/pulls/{num}")
        latebase = current_main(g)
        expect(eligible(late) and late["head"]["sha"] == sha
               and late["head"]["ref"] == branch
               and late["base"]["sha"] == base and latebase == base,
               "HEAD_OR_BASE_DRIFT")
        result["Reason"] = "SOURCE_ONLY_READ_AUDIT_PASSED_NO_MERGE_AUTHORITY"
    except (Blocked, KeyError, TypeError, ValueError) as exc:
        result["Reason"] = str(exc) if isinstance(exc, Blocked) else "MALFORMED_GITHUB_EVIDENCE"
    return result


def run(g):
    prs = bounded_list(g, "/pulls?state=open&per_page=100")
    candidates = sorted((p for p in prs if eligible(p)), key=lambda x: x["number"])
    results = [audit_one(g, p) for p in candidates]
    return {"Schema": "forge.source-admission.r21.readonly.v1",
            "Candidates": results, "Count": len(results),
            "MergeAuthorized": False, "ScientificAuthority": False}


def main():
    try:
        record = run(GitHub())
        print(json.dumps(record, sort_keys=True, separators=(",", ":")))
        print("AUTONOMOUS_SOURCE_AUDIT=READ_ONLY")
        print("UNTRUSTED_CANDIDATE_WORKFLOW_AUTHORITY=DENIED")
        print("AUTOMERGE=DISABLED")
    except Blocked as exc:
        print("SOURCE_AUDIT_FAILED_CLOSED=" + str(exc), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
