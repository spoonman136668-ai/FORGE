import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fsa_lastmile import (check, exact_policy, Denied, REPO, EXPECTED_NAME,
                          EXPECTED_RULESET_ID)

OID = "a" * 40
BASE = "b" * 40


def contract():
    detail = {
      "id": EXPECTED_RULESET_ID, "name": EXPECTED_NAME,
      "target": "branch", "source_type": "Repository", "source": REPO,
      "enforcement": "active", "bypass_actors": [],
      "current_user_can_bypass": "never",
      "conditions": {"ref_name": {"include": ["refs/heads/main"], "exclude": []}},
      "rules": [
        {"type": "deletion"}, {"type": "non_fast_forward"},
        {"type": "pull_request", "parameters": {
           "required_approving_review_count": 0,
           "dismiss_stale_reviews_on_push": True,
           "required_review_thread_resolution": True,
           "allowed_merge_methods": ["merge"],
           "require_code_owner_review": False,
           "require_last_push_approval": False,
           "require_extra_approval_for_unattributed_changes": True}},
        {"type": "required_status_checks", "parameters": {
           "strict_required_status_checks_policy": True,
           "do_not_enforce_on_create": False,
           "required_status_checks": [
             {"context": "linux", "integration_id": 15368},
             {"context": "windows", "integration_id": 15368}]}}
       ]}
    return detail


def pr(draft=False):
    return {"head": {"sha": OID, "ref": "proposal/fsa-r19-readonly",
                     "repo": {"full_name": REPO}},
            "base": {"ref": "main", "sha": BASE},
            "user": {"login": "spoonman136668-ai"},
            "draft": draft, "state": "open",
            "mergeable": True, "mergeable_state": "clean"}


def snapshot():
    return {"Repository": REPO, "PR": {"Number": 273, "HeadSHA": OID}}


def review(qualified=True):
    return {"MergeAuthorized": False, "HeadSHA": OID,
            "SourceQualified": qualified,
            "Reason": ("SOURCE_REVIEW_QUALIFIED_NO_MERGE_AUTHORITY"
                       if qualified else "FULL_OID_INDEPENDENT_REVIEW_MISSING")}


class Read:
    def __init__(self):
        self.values = [pr(), {"commit": {"sha": BASE}}, pr(), {"commit": {"sha": BASE}}]
        self.rulesets = [[{"id": EXPECTED_RULESET_ID, "name": EXPECTED_NAME,
                           "enforcement": "active"}]] * 2
        self.details = [contract(), contract()]
        self.calls = []
        self.pr_count = 0
        self.base_count = 0
        self.detail_count = 0
        self.list_count = 0

    def get(self, key):
        self.calls.append(("GET", key))
        if key == "pulls/273":
            n = self.pr_count
            self.pr_count += 1
            return self.values[n * 2]
        if key == "branches/main":
            n = self.base_count
            self.base_count += 1
            return self.values[n * 2 + 1]
        if key == f"rulesets/{EXPECTED_RULESET_ID}":
            n = self.detail_count
            self.detail_count += 1
            return self.details[n]
        raise AssertionError(key)

    def transport(self, method, url, data):
        self.calls.append((method, url))
        if method != "GET" or not url.endswith("/rulesets?includes_parents=true"):
            raise AssertionError("unsafe transport")
        n = self.list_count
        self.list_count += 1
        return self.rulesets[n], ""


class RulesTest(unittest.TestCase):
    def test_only_frozen_contract_allowed(self):
        rule = contract()
        digest = exact_policy([{"id": EXPECTED_RULESET_ID, "name": EXPECTED_NAME,
                                "enforcement": "active"}], rule)
        self.assertEqual(len(digest), 64)

    def test_reject_authority_drift(self):
        variants = [
          ("bypass", lambda x: x.update(bypass_actors=[{"actor_id": 1}])),
          ("wrong ID", lambda x: x.update(id=123)),
          ("inactive", lambda x: x.update(enforcement="disabled")),
          ("wrong scope", lambda x: x["conditions"]["ref_name"].update(
            include=["refs/heads/*"])),
          ("extra rule", lambda x: x["rules"].append({"type": "creation"})),
          ("non-strict", lambda x: x["rules"][3]["parameters"].update(
            strict_required_status_checks_policy=False)),
          ("different check", lambda x: x["rules"][3]["parameters"][
            "required_status_checks"][0].update(context="optional")),
          ("unresolved threads allowed", lambda x: x["rules"][2]["parameters"].update(
            required_review_thread_resolution=False)),
          ("stale allowed", lambda x: x["rules"][2]["parameters"].update(
            dismiss_stale_reviews_on_push=False)),
        ]
        listed = [{"id": EXPECTED_RULESET_ID, "name": EXPECTED_NAME,
                   "enforcement": "active"}]
        for name, mutate in variants:
            with self.subTest(name=name):
                r = contract()
                mutate(r)
                with self.assertRaises(Denied):
                    exact_policy(listed, r)

    def test_unexpected_ruleset_fails(self):
        with self.assertRaisesRegex(Denied, "UNKNOWN_OR_MULTIPLE"):
            exact_policy([{"id": 123}, {"id": EXPECTED_RULESET_ID}], contract())


class PreflightTest(unittest.TestCase):
    def test_synthetic_positive_is_still_non_authorizing(self):
        fake = Read()
        output = check(273, snapshot(), review(), fake)
        self.assertTrue(output["WouldSatisfyObservedGate"])
        self.assertTrue(output["RulesetVerified"])
        self.assertTrue(output["HeadAndBaseStable"])
        self.assertTrue(output["NativeReviewQualified"])
        self.assertFalse(output["MergeAuthorized"])
        self.assertFalse(output["ScientificAuthority"])
        self.assertTrue(all(method == "GET" for method, _ in fake.calls))

    def test_missing_real_review_denied(self):
        output = check(273, snapshot(), review(False), Read())
        self.assertFalse(output["WouldSatisfyObservedGate"])
        self.assertEqual(output["Reason"], "CURRENT_HEAD_NATIVE_REVIEW_MISSING")
        self.assertFalse(output["MergeAuthorized"])

    def test_draft_denied(self):
        fake = Read()
        fake.values[0]["draft"] = True
        fake.values[2]["draft"] = True
        output = check(273, snapshot(), review(), fake)
        self.assertEqual(output["Reason"], "INELIGIBLE_SOURCE_PR")

    def test_head_drifts(self):
        fake = Read()
        fake.values[2]["head"]["sha"] = "c" * 40
        output = check(273, snapshot(), review(), fake)
        self.assertEqual(output["Reason"], "PR_OR_BASE_MOVED_DURING_READ")

    def test_base_drifts(self):
        fake = Read()
        fake.values[3]["commit"]["sha"] = "c" * 40
        output = check(273, snapshot(), review(), fake)
        self.assertEqual(output["Reason"], "PR_OR_BASE_MOVED_DURING_READ")

    def test_rule_changes(self):
        fake = Read()
        altered = contract()
        altered["rules"][3]["parameters"]["required_status_checks"][0]["context"] = "other"
        fake.details[1] = altered
        output = check(273, snapshot(), review(), fake)
        self.assertEqual(output["Reason"], "STATUS_CONTEXT_DRIFT")

    def test_review_claim_cannot_grant_merge(self):
        r = review()
        r["MergeAuthorized"] = True
        output = check(273, snapshot(), r, Read())
        self.assertEqual(output["Reason"], "UNTRUSTED_SNAPSHOT_OR_REVIEW")
        self.assertFalse(output["MergeAuthorized"])

    def test_dirty_mergeability_denied(self):
        fake = Read()
        fake.values[0]["mergeable_state"] = "blocked"
        output = check(273, snapshot(), review(), fake)
        self.assertEqual(output["Reason"], "GITHUB_MERGEABILITY_NOT_CLEAN")


if __name__ == "__main__":
    unittest.main()
