#!/usr/bin/env python3
"""R19: fail-closed, non-authorizing last-mile FORGE source-merge preflight.

No merge, mutation, scheduler, new authority, or scientific action exists here.
The only network method is GitHub GET via the R18 read-only collector.
"""
import argparse
import hashlib
import json
import os
import re

from fsa_native_review import Source, Denied

REPO = "spoonman136668-ai/FORGE"
EXPECTED_RULESET_ID = 25031517
EXPECTED_NAME = "FORGE main qualified-source only"
EXPECTED_STATUS_INTEGRATION = 15368
OID = re.compile(r"^[a-f0-9]{40}$")
REQUIRED_TYPES = {"deletion", "non_fast_forward", "pull_request", "required_status_checks"}


def sha_object(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def exact_policy(rule_list, detail):
    """Authenticate the observed ruleset; no implicit acceptance on unknown rules."""
    if not isinstance(rule_list, list) or len(rule_list) != 1:
        raise Denied("UNKNOWN_OR_MULTIPLE_BRANCH_RULESETS")
    summary = rule_list[0]
    if (not isinstance(summary, dict)
            or summary.get("id") != EXPECTED_RULESET_ID
            or summary.get("name") != EXPECTED_NAME
            or summary.get("enforcement") != "active"):
        raise Denied("RULESET_LIST_DRIFT")
    if not isinstance(detail, dict) or detail.get("id") != EXPECTED_RULESET_ID:
        raise Denied("RULESET_ID_DRIFT")
    if (detail.get("name") != EXPECTED_NAME or detail.get("enforcement") != "active"
            or detail.get("target") != "branch" or detail.get("source_type") != "Repository"
            or detail.get("source") != REPO):
        raise Denied("RULESET_AUTHORITY_SCOPE_DRIFT")
    if detail.get("bypass_actors") != []:
        raise Denied("RULESET_BYPASS_ACTORS_PRESENT")
    if detail.get("current_user_can_bypass") != "never":
        raise Denied("RULESET_CALLER_BYPASS_VISIBILITY_UNQUALIFIED")
    ref = detail.get("conditions", {}).get("ref_name", {})
    if ref.get("include") != ["refs/heads/main"] or ref.get("exclude") != []:
        raise Denied("RULESET_REF_DRIFT")
    rules = detail.get("rules")
    if not isinstance(rules, list) or len(rules) != len(REQUIRED_TYPES):
        raise Denied("UNKNOWN_RULE_CONTRACT")
    indexed = {r.get("type"): r for r in rules if isinstance(r, dict)}
    if set(indexed) != REQUIRED_TYPES:
        raise Denied("UNKNOWN_RULE_CONTRACT")
    pr = indexed["pull_request"].get("parameters", {})
    if (pr.get("required_approving_review_count") != 0
            or pr.get("dismiss_stale_reviews_on_push") is not True
            or pr.get("required_review_thread_resolution") is not True
            or pr.get("allowed_merge_methods") != ["merge"]
            or pr.get("require_code_owner_review") is not False
            or pr.get("require_last_push_approval") is not False
            or pr.get("require_extra_approval_for_unattributed_changes") is not True):
        raise Denied("REVIEW_POLICY_DRIFT")
    checks = indexed["required_status_checks"].get("parameters", {})
    if (checks.get("strict_required_status_checks_policy") is not True
            or checks.get("do_not_enforce_on_create") is not False):
        raise Denied("STATUS_POLICY_DRIFT")
    required = checks.get("required_status_checks")
    if (not isinstance(required, list) or len(required) != 2
            or {(x.get("context"), x.get("integration_id")) for x in required
                if isinstance(x, dict)} != {
                  ("linux", EXPECTED_STATUS_INTEGRATION),
                  ("windows", EXPECTED_STATUS_INTEGRATION)}):
        raise Denied("STATUS_CONTEXT_DRIFT")
    return sha_object(detail)


def read_rules(read):
    listed = read("rulesets?includes_parents=true")
    # Source.get only accepts dict; the list is retrieved through read-only transport.
    return listed


def check(pr_number, snapshot, review, source):
    """Compute diagnostic pre-merge evidence, with unconditional no-merge result."""
    report = {"Schema": "forge.fsa-r19.lastmile.v1",
              "PR": pr_number, "HeadSHA": "",
              "RulesetVerified": False, "HeadAndBaseStable": False,
              "NativeReviewQualified": False, "EligibleSourcePR": False,
              "WouldSatisfyObservedGate": False,
              "MergeAuthorized": False, "ScientificAuthority": False,
              "Reason": "NOT_QUALIFIED"}
    try:
        if (not isinstance(snapshot, dict) or not isinstance(review, dict)
                or snapshot.get("Repository") != REPO
                or snapshot.get("PR", {}).get("Number") != pr_number
                or review.get("MergeAuthorized") is not False):
            raise Denied("UNTRUSTED_SNAPSHOT_OR_REVIEW")
        expected = snapshot["PR"].get("HeadSHA", "")
        if not OID.fullmatch(expected) or review.get("HeadSHA") != expected:
            raise Denied("REVIEW_HEAD_IDENTITY_MISMATCH")
        report["HeadSHA"] = expected
        # Read first PR/base, rules, then read PR/base and rules AGAIN.
        # This is only a read-only drift check, not an atomic GitHub merge fence.
        first = source.get(f"pulls/{pr_number}")
        base = source.get("branches/main")
        if first.get("head", {}).get("sha") != expected:
            raise Denied("PR_HEAD_CHANGED_BEFORE_RULES")
        if not OID.fullmatch(first.get("base", {}).get("sha", "")):
            raise Denied("BASE_REF_UNQUALIFIED")
        if first["base"]["sha"] != base.get("commit", {}).get("sha"):
            raise Denied("BASE_COMMIT_IDENTITY_MISMATCH")
        # The native GET /rulesets list may be a JSON array.
        response, _ = source.transport(
            "GET", f"https://api.github.com/repos/{REPO}/rulesets?includes_parents=true", None)
        rule = source.get(f"rulesets/{EXPECTED_RULESET_ID}")
        digest = exact_policy(response, rule)
        late = source.get(f"pulls/{pr_number}")
        lastbase = source.get("branches/main")
        response2, _ = source.transport(
            "GET", f"https://api.github.com/repos/{REPO}/rulesets?includes_parents=true", None)
        rule2 = source.get(f"rulesets/{EXPECTED_RULESET_ID}")
        if digest != exact_policy(response2, rule2):
            raise Denied("RULESET_CHANGED_DURING_READ")
        report["RulesetVerified"] = True
        report["RuleContractSHA256"] = digest
        if (first["head"]["sha"] != late.get("head", {}).get("sha")
                or first["head"]["ref"] != late.get("head", {}).get("ref")
                or first["base"]["sha"] != late.get("base", {}).get("sha")
                or first["base"]["ref"] != late.get("base", {}).get("ref")
                or first.get("draft") != late.get("draft")
                or first.get("state") != late.get("state")
                or base.get("commit", {}).get("sha") != lastbase.get("commit", {}).get("sha")):
            raise Denied("PR_OR_BASE_MOVED_DURING_READ")
        report["HeadAndBaseStable"] = True
        if (first.get("state") != "open" or first.get("draft") is not False
                or first.get("head", {}).get("repo", {}).get("full_name") != REPO
                or first.get("base", {}).get("ref") != "main"
                or not re.fullmatch(r"proposal/fsa[a-zA-Z0-9/_-]*",
                                    first.get("head", {}).get("ref", ""))
                or first.get("user", {}).get("login") != "spoonman136668-ai"):
            raise Denied("INELIGIBLE_SOURCE_PR")
        report["EligibleSourcePR"] = True
        if (review.get("SourceQualified") is not True or
                review.get("Reason") != "SOURCE_REVIEW_QUALIFIED_NO_MERGE_AUTHORITY"):
            raise Denied("CURRENT_HEAD_NATIVE_REVIEW_MISSING")
        report["NativeReviewQualified"] = True
        # GitHub's mergeability answer is advisory, and cannot replace its
        # final authenticated merge API's status/rules verification.
        if (first.get("mergeable") is not True or
                first.get("mergeable_state") != "clean"):
            raise Denied("GITHUB_MERGEABILITY_NOT_CLEAN")
        report["WouldSatisfyObservedGate"] = True
        report["Reason"] = "READ_ONLY_GATE_OBSERVED_NO_MERGE_AUTHORITY"
    except (Denied, KeyError, TypeError, ValueError, IndexError) as exc:
        report["Reason"] = str(exc) if isinstance(exc, Denied) else "MALFORMED_GITHUB_EVIDENCE"
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pr", type=int, required=True)
    parser.add_argument("--snapshot", required=True)
    parser.add_argument("--review", required=True)
    args = parser.parse_args()
    if (args.pr <= 0 or
            any(not os.path.isabs(p) or os.path.islink(p) or os.path.getsize(p) > 2_000_000
                for p in (args.snapshot, args.review))):
        raise SystemExit("INVALID_INPUT_PATH")
    try:
        with open(args.snapshot, encoding="utf-8") as f:
            snapshot = json.load(f)
        with open(args.review, encoding="utf-8") as f:
            review = json.load(f)
        report = check(args.pr, snapshot, review,
                       Source(REPO, os.getenv("GH_TOKEN", "")))
    except (OSError, ValueError) as exc:
        raise SystemExit("INVALID_READ_ONLY_EVIDENCE") from exc
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
