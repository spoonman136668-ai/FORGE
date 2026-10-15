#!/usr/bin/env python3
"""R24: read-only, fail-closed final merge-CAS proof over authentic GitHub state.

No GitHub writes, no merge permission, no scientific authority. This is a
separate diagnostic verifier that reuses the installed R21 source auditor.
GitHub's eventual server-side merge must independently enforce branch rules
and require the exact current PR SHA; this program NEVER calls that endpoint.
"""
import argparse
import hashlib
import json
import re
import os
import sys
from fsa_source_audit import (Blocked, GitHub, SHA, REPO, audit_one,
                              current_main, eligible, verify_ruleset,
                              bounded_list)


def require(condition, reason):
    if not condition:
        raise Blocked(reason)


def canonical_policy(g):
    """Read actual policy without silently substituting absent bypass metadata."""
    verify_ruleset(g)
    raw = g.get("/rulesets/25031517")
    require(isinstance(raw.get("bypass_actors"), list) and not raw["bypass_actors"],
            "UNQUALIFIED_POLICY_BYPASS")
    return hashlib.sha256(json.dumps(raw, sort_keys=True,
                                     separators=(",", ":")).encode()).hexdigest()


def unchanged(current, fresh, expected_sha, expected_main):
    require(eligible(fresh) and fresh.get("number") == current.get("number"),
            "PR_NO_LONGER_ELIGIBLE")
    for item in (current, fresh):
        require(item["head"]["sha"] == expected_sha
                and item["head"]["ref"] == current["head"]["ref"]
                and item["head"]["repo"]["full_name"] == REPO
                and item["base"]["ref"] == "main"
                and item["base"]["sha"] == expected_main,
                "PR_HEAD_BASE_OR_BRANCH_DRIFT")
    require(fresh.get("mergeable") is True
            and fresh.get("mergeable_state") == "clean",
            "GITHUB_MERGEABILITY_NOT_CLEAN")


def preflight(g, number, head, main):
    result = {"Schema": "forge.source-cas.r24.readonly.v1", "PR": number,
              "HeadSHA": head, "MainSHA": main,
              "SourceChecksPassed": False, "StableHeadAndBase": False,
              "PolicyComplete": False, "MergeableObserved": False,
              "MergeAuthorized": False, "ScientificAuthority": False,
              "Reason": "NOT_QUALIFIED"}
    try:
        require(isinstance(number, int) and number > 0 and
                isinstance(head, str) and SHA.fullmatch(head) and
                isinstance(main, str) and SHA.fullmatch(main),
                "INVALID_CAS_INPUT")
        first = g.get(f"/pulls/{number}")
        require(eligible(first) and first.get("number") == number
                and first["head"]["sha"] == head and
                first["base"]["sha"] == main,
                "SOURCE_IDENTITY_OR_BASE_CHANGED")
        require(current_main(g) == main, "MAIN_MOVED_BEFORE_AUDIT")
        verified = audit_one(g, first)
        require(verified["SourceTestsQualified"] is True,
                "SOURCE_VERIFICATION_FAILED:" + verified["Reason"])
        result["SourceChecksPassed"] = True
        require(verified["RulesetVisible"] is True,
                "POLICY_VISIBILITY_BLOCKED:" + verified["Reason"])
        policy1 = canonical_policy(g)
        # All relevant native reviews are read from GitHub, never comments or
        # fabricated AI approvals. A changes-requested review blocks.
        reviews = bounded_list(g, f"/pulls/{number}/reviews?per_page=100")
        require(all(r.get("state") != "CHANGES_REQUESTED" for r in reviews),
                "CHANGES_REQUESTED")
        second = g.get(f"/pulls/{number}")
        unchanged(first, second, head, main)
        require(current_main(g) == main, "MAIN_MOVED_DURING_PREFLIGHT")
        policy2 = canonical_policy(g)
        require(policy1 == policy2, "BRANCH_POLICY_CHANGED_DURING_PREFLIGHT")
        third = g.get(f"/pulls/{number}")
        unchanged(first, third, head, main)
        require(current_main(g) == main, "MAIN_MOVED_AFTER_POLICY")
        result["StableHeadAndBase"] = True
        result["PolicyComplete"] = True
        result["MergeableObserved"] = True
        result["Reason"] = "READ_ONLY_CAS_PREFLIGHT_OBSERVED_NO_MERGE_AUTHORITY"
    except (Blocked, KeyError, TypeError, ValueError, IndexError) as exc:
        result["Reason"] = str(exc) if isinstance(exc, Blocked) else "MALFORMED_GITHUB_EVIDENCE"
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pr", type=int, required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--base", required=True)
    args = parser.parse_args()
    report = preflight(GitHub(), args.pr, args.head, args.base)
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    print("MERGE_AUTHORIZED=FALSE")
    print("NO_GITHUB_MUTATION=TRUE")
    print("R24_OBSERVED_REASON=" + report["Reason"])


if __name__ == "__main__":
    main()
