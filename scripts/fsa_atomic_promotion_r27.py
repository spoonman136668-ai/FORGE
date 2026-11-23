#!/usr/bin/env python3
"""R27: native exact-head atomic promotion preflight; intentionally read-only.

No source merge, no branch write, no GitHub review simulation, no science use.
Every candidate is re-read after independent source and policy verification.
An incomplete GitHub Actions bypass actor read is a denial, not permission.
"""
import json
import sys

from fsa_source_audit import (Blocked, GitHub, SHA, audit_one, bounded_list,
                              list_open_prs,
                              current_main, eligible, expect, REPO)
from fsa_policy_anchor_r26 import observe as policy_anchor


def check(api, number, expected_head, expected_main):
    result = {
        "Schema": "forge.source-promotion.r27.readonly.v1",
        "PR": number,
        "HeadSHA": expected_head,
        "MainSHA": expected_main,
        "SourceTestsQualified": False,
        "PolicyAnchorUnchanged": False,
        "FullRulesetVisible": False,
        "NativeMergeabilityClean": False,
        "NativeReviewsUnblocked": False,
        "HeadAndBaseStable": False,
        "MergeAuthorized": False,
        "ScientificAuthority": False,
        "Reason": "NOT_CHECKED",
    }
    try:
        expect(isinstance(number, int) and number > 0 and
               isinstance(expected_head, str) and SHA.fullmatch(expected_head) and
               isinstance(expected_main, str) and SHA.fullmatch(expected_main),
               "R27_INVALID_ATOMIC_SOURCE_IDENTITY")
        initial = api.get(f"/pulls/{number}")
        expect(eligible(initial) and initial.get("number") == number and
               initial["head"]["sha"] == expected_head and
               initial["base"]["sha"] == expected_main,
               "R27_PR_SOURCE_OR_BASE_DRIFT")
        expect(current_main(api) == expected_main, "R27_MAIN_MOVED_BEFORE_AUDIT")

        source = audit_one(api, initial)
        expect(source["SourceTestsQualified"] is True,
               "R27_SOURCE_CHECKS_NOT_QUALIFIED:" + source["Reason"])
        result["SourceTestsQualified"] = True
        expect(source["Reason"] in (
                   "RULESET_BYPASS_VISIBILITY_MISSING",
                   "SOURCE_ONLY_READ_AUDIT_PASSED_NO_MERGE_AUTHORITY"),
               "R27_SOURCE_POLICY_DENIED:" + source["Reason"])
        # Pinned continuity is a separate fact from fresh visibility.
        expect(source["PolicyAnchorUnchanged"] is True,
               "R27_PINNED_POLICY_CHANGED:" + source["Reason"])
        result["PolicyAnchorUnchanged"] = True

        native_reviews = bounded_list(
            api, f"/pulls/{number}/reviews?per_page=100", maximum=99)
        expect(all(isinstance(item, dict) and
                   item.get("state") in ("APPROVED", "COMMENTED")
                   for item in native_reviews),
               "R27_NATIVE_REVIEW_BLOCKED_OR_UNKNOWN")
        result["NativeReviewsUnblocked"] = True

        # GitHub's server-reported mergeability includes protected branch
        # state, but is an *observation*, never a merge capability.
        mid = api.get(f"/pulls/{number}")
        expect(eligible(mid) and mid.get("number") == number and
               mid["head"]["sha"] == expected_head and
               mid["base"]["sha"] == expected_main,
               "R27_HEAD_BASE_DRIFT_DURING_AUDIT")
        expect(mid.get("mergeable") is True and
               mid.get("mergeable_state") == "clean",
               "R27_NATIVE_MERGEABILITY_NOT_CLEAN")
        result["NativeMergeabilityClean"] = True

        first_policy = policy_anchor(api)
        expect(first_policy["PinnedSourcePolicyUnchanged"] is True,
               "R27_POLICY_IDENTITY_DRIFT:" + first_policy["Reason"])
        expect(current_main(api) == expected_main,
               "R27_MAIN_MOVED_DURING_AUDIT")
        second_policy = policy_anchor(api)
        expect(second_policy["PinnedSourcePolicyUnchanged"] is True,
               "R27_POLICY_CHANGED_DURING_AUDIT:" + second_policy["Reason"])
        expect(first_policy["FullRulesetAuthenticated"] ==
               second_policy["FullRulesetAuthenticated"],
               "R27_POLICY_VISIBILITY_CHANGED")
        result["FullRulesetVisible"] = (
            first_policy["FullRulesetAuthenticated"]
            and second_policy["FullRulesetAuthenticated"])

        last = api.get(f"/pulls/{number}")
        expect(eligible(last) and last.get("number") == number and
               last["head"]["sha"] == expected_head and
               last["base"]["sha"] == expected_main and
               last["head"]["ref"] == initial["head"]["ref"] and
               last.get("mergeable") is True and
               last.get("mergeable_state") == "clean",
               "R27_FINAL_HEAD_BASE_OR_MERGEABILITY_DRIFT")
        expect(current_main(api) == expected_main,
               "R27_FINAL_MAIN_DRIFT")
        result["HeadAndBaseStable"] = True

        if not result["FullRulesetVisible"]:
            result["Reason"] = "R27_REDACTED_BYPASS_ACTORS_NO_MERGE_AUTHORITY"
        else:
            result["Reason"] = "R27_READ_ONLY_ATOMIC_PREFLIGHT_NO_MERGE_AUTHORITY"
    except (Blocked, KeyError, TypeError, ValueError, IndexError) as error:
        result["Reason"] = str(error) if isinstance(error, Blocked) else \
            "R27_MALFORMED_NATIVE_GITHUB_EVIDENCE"
    return result


def run(api):
    open_prs = list_open_prs(api)
    current = current_main(api)
    eligible_prs = sorted((p for p in open_prs if eligible(p)),
                          key=lambda p: p["number"])
    records = [check(api, p["number"], p["head"]["sha"], current)
               for p in eligible_prs]
    return {
        "Schema": "forge.source-promotion.r27.batch.readonly.v1",
        "CurrentMainSHA": current,
        "Candidates": records,
        "Count": len(records),
        "MergeAuthorized": False,
        "ScientificAuthority": False,
    }


if __name__ == "__main__":
    try:
        report = run(GitHub())
        print(json.dumps(report, separators=(",", ":"), sort_keys=True))
        print("R27_SOURCE_PROMOTION=DRY_RUN_ONLY")
        print("R27_ATOMIC_GITHUB_MERGE=DISABLED")
    except Blocked as error:
        print("R27_SOURCE_PRECHECK_FAILED_CLOSED=" + str(error), file=sys.stderr)
        sys.exit(1)
