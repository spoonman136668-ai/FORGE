import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_fsa_source_audit import Fake, rules, RULESET
from fsa_policy_anchor_r26 import (observe, NODE, UPDATED_AT, REPO,
                                   STATUS_PARAMETERS, REVIEW_PARAMETERS)

def live_fixture():
    f = Fake()
    p = f.pages[f"/rulesets/{RULESET}"]
    p["node_id"] = NODE
    p["updated_at"] = UPDATED_AT
    return f


class R26PolicyContinuityTests(unittest.TestCase):
    def verify(self, f):
        value = observe(f)
        self.assertFalse(value["MergeAuthorized"])
        self.assertFalse(value["ScientificAuthority"])
        self.assertTrue(all(x.startswith("/") for x in f.calls))
        return value

    def test_full_authenticated_view_stays_non_authorizing(self):
        v = self.verify(live_fixture())
        self.assertTrue(v["FullRulesetAuthenticated"])
        self.assertTrue(v["PinnedSourcePolicyUnchanged"])
        self.assertTrue(v["BypassActorsFreshlyVisible"])
        self.assertTrue(v["CallerBypassFreshlyVisible"])
        self.assertEqual(v["Reason"], "FRESH_POLICY_VISIBLE_READ_ONLY_NO_MERGE_AUTHORITY")

    def test_ephemeral_runner_redacts_both_bypass_fields(self):
        f = live_fixture()
        del f.pages[f"/rulesets/{RULESET}"]["bypass_actors"]
        del f.pages[f"/rulesets/{RULESET}"]["current_user_can_bypass"]
        v = self.verify(f)
        self.assertTrue(v["PinnedSourcePolicyUnchanged"])
        self.assertFalse(v["FullRulesetAuthenticated"])
        self.assertFalse(v["BypassActorsFreshlyVisible"])
        self.assertFalse(v["CallerBypassFreshlyVisible"])
        self.assertEqual(v["Reason"], "PINNED_POLICY_STABLE_REDACTED_ACTORS_NO_AUTHORITY")

    def test_hidden_actors_not_synthetic_authority(self):
        f = live_fixture()
        del f.pages[f"/rulesets/{RULESET}"]["bypass_actors"]
        v = self.verify(f)
        self.assertTrue(v["PinnedSourcePolicyUnchanged"])
        self.assertFalse(v["FullRulesetAuthenticated"])

    def test_actor_added_blocks(self):
        f = live_fixture()
        f.pages[f"/rulesets/{RULESET}"]["bypass_actors"] = [{"actor_id": 8}]
        v = self.verify(f)
        self.assertFalse(v["FullRulesetAuthenticated"])
        self.assertEqual(v["Reason"], "RULESET_BYPASS_ACTORS_CHANGED")

    def test_equivalent_utc_timestamp_is_same_exact_instant(self):
        f = live_fixture()
        f.pages[f"/rulesets/{RULESET}"]["updated_at"] = "2026-10-13T21:08:13.052Z"
        value = self.verify(f)
        self.assertTrue(value["PinnedSourcePolicyUnchanged"])
        self.assertTrue(value["FullRulesetAuthenticated"])

    def test_microsecond_timestamp_drift_is_denied(self):
        f = live_fixture()
        f.pages[f"/rulesets/{RULESET}"]["updated_at"] = "2026-10-13T21:08:13.053Z"
        self.assertEqual(self.verify(f)["Reason"],
                         "RULESET_UPDATED_AFTER_AUTHENTICATED_OBSERVATION")

    def test_hidden_bypass_with_updated_at_drift_denied(self):
        f = live_fixture()
        del f.pages[f"/rulesets/{RULESET}"]["bypass_actors"]
        f.pages[f"/rulesets/{RULESET}"]["updated_at"] = "2026-10-15T08:00:00Z"
        v = self.verify(f)
        self.assertFalse(v["PinnedSourcePolicyUnchanged"])
        self.assertEqual(v["Reason"],
                         "RULESET_UPDATED_AFTER_AUTHENTICATED_OBSERVATION")

    def test_required_linux_context_removed_denied(self):
        f = live_fixture()
        r = f.pages[f"/rulesets/{RULESET}"]["rules"][3]["parameters"]
        r["required_status_checks"] = r["required_status_checks"][:1]
        self.assertEqual(self.verify(f)["Reason"], "RULESET_RULE_PARAMETERS_DRIFT")

    def test_expected_github_app_changed_denied(self):
        f = live_fixture()
        f.pages[f"/rulesets/{RULESET}"]["rules"][3]["parameters"][
            "required_status_checks"][0]["integration_id"] = 999
        self.assertEqual(self.verify(f)["Reason"], "RULESET_RULE_PARAMETERS_DRIFT")

    def test_approval_policy_drift_denied(self):
        f = live_fixture()
        f.pages[f"/rulesets/{RULESET}"]["rules"][2]["parameters"][
            "required_approving_review_count"] = 1
        self.assertEqual(self.verify(f)["Reason"], "RULESET_RULE_PARAMETERS_DRIFT")

    def test_unexpected_additional_rule_denied(self):
        f = live_fixture()
        f.pages[f"/rulesets/{RULESET}"]["rules"].append({"type": "required_signatures"})
        self.assertEqual(self.verify(f)["Reason"], "RULESET_RULES_MALFORMED")

    def test_missing_pinned_node_identity_denied(self):
        f = live_fixture()
        del f.pages[f"/rulesets/{RULESET}"]["node_id"]
        self.assertEqual(self.verify(f)["Reason"], "RULESET_IDENTITY_OR_SCOPE_DRIFT")

    def test_caller_bypass_denied(self):
        f = live_fixture()
        f.pages[f"/rulesets/{RULESET}"]["current_user_can_bypass"] = "always"
        self.assertEqual(self.verify(f)["Reason"], "RULESET_CALLER_BYPASS_CHANGED")

    def test_multiple_rulesets_denied(self):
        f = live_fixture()
        f.pages["/rulesets?includes_parents=true"].append({"id": 888, "enforcement": "active"})
        self.assertEqual(self.verify(f)["Reason"], "RULESET_INVENTORY_OR_ACTIVATION_DRIFT")

    def test_missing_parameter_keys_denied(self):
        f = live_fixture()
        del f.pages[f"/rulesets/{RULESET}"]["rules"][3]["parameters"][
            "do_not_enforce_on_create"]
        self.assertEqual(self.verify(f)["Reason"], "RULESET_RULE_PARAMETERS_DRIFT")

    def test_disabled_ruleset_denied(self):
        f = live_fixture()
        f.pages[f"/rulesets/{RULESET}"]["enforcement"] = "disabled"
        self.assertEqual(self.verify(f)["Reason"], "RULESET_IDENTITY_OR_SCOPE_DRIFT")


if __name__ == "__main__":
    unittest.main()
