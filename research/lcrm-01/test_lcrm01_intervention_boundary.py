"""Analytic mock-custody tests, not real independently authenticated science."""
import copy
import unittest

import lcrm01_intervention_boundary as q
from lcrm01_public_feasibility import observed_episode


class SourceOnlyInterventionGate(unittest.TestCase):
    def setUp(self):
        self.obs = observed_episode((0,1,0,1,1,0,0,1), "direct_chain")
        self.row, self.pin = q.analytic_fixture("direct_chain")

    def result(self, row=None, pin=None):
        return q.assess(self.row if row is None else row,
                        trusted_pin=self.pin if pin is None else pin,
                        observations=self.obs)

    def test_legacy_source_is_not_a_do_receipt(self):
        v=q.qualify_observation_only({"target":"alpha","source":"beta","event":1,"observed":1})
        self.assertEqual(v["status"],"NO_AUTHENTICATED_DO_IN_HISTORICAL_EVENT")

    def test_missing_public_do_denied(self):
        self.assertEqual(q.assess(None, trusted_pin=None, observations=self.obs)["status"],"NO_PUBLIC_DO_RECEIPT")

    def test_self_certification_rejected(self):
        a=copy.deepcopy(self.row);a["certified_do"] = True
        self.assertEqual(self.result(row=a)["status"],"INVALID_OR_SELF_ASSERTED_DO_SCHEMA")

    def test_missing_independent_pin_rejected(self):
        self.assertEqual(q.assess(self.row, trusted_pin=None, observations=self.obs)["status"],"NO_INDEPENDENT_TRUST_PIN")

    def test_fabricated_trust_pin_rejected(self):
        p=copy.deepcopy(self.pin);p["causal_assignment_witness"]="SOURCE_SELF_ATTESTED"
        self.assertEqual(self.result(pin=p)["status"],"CAUSAL_ASSIGNMENT_NOT_INDEPENDENTLY_VERIFIED")

    def test_label_changed_after_digest_rejected(self):
        a=copy.deepcopy(self.row);a["observed_xyz"]=[1,0,0]
        self.assertEqual(self.result(row=a)["status"],"UNPINNED_OR_TAMPERED_PUBLIC_RECEIPT")

    def test_protected_split_not_public_fit(self):
        a=copy.deepcopy(self.row);a["public_split"]="HELDOUT"
        self.assertEqual(self.result(row=a)["status"],"INELIGIBLE_SOURCE_IDENTITY_OR_SPLIT")

    def test_no_change_in_do_does_not_prove_effect(self):
        a=copy.deepcopy(self.row);a["do_value"]=0;a["observed_xyz"]=[0,0,0]
        p=copy.deepcopy(self.pin);p["receipt_sha256"]=q.digest(a)
        self.assertEqual(self.result(row=a,pin=p)["status"],"NON_DISCRIMINATING_DO_EQUALS_BASELINE")

    def test_invalid_baseline_denied(self):
        a=copy.deepcopy(self.row);a["baseline_xyz"]=[0,1,0]
        self.assertEqual(self.result(row=a)["status"],"INVALID_BASELINE_OR_OBSERVED_VALUES")

    def test_changed_pin_provenance_denied(self):
        p=copy.deepcopy(self.pin);p["source_commit"]="2"*40
        self.assertEqual(self.result(pin=p)["status"],"UNPINNED_OR_TAMPERED_PUBLIC_RECEIPT")

    def test_toy_direct_chain_conditionally_identified(self):
        v=self.result()
        self.assertEqual(v["status"],"TWO_SCM_CONDITIONAL_DISCRIMINATION")
        self.assertEqual(v["models"],["direct_chain"])
        self.assertFalse(v["science_admitted"])
        self.assertFalse(v["counterfactual_acceptance"])

    def test_toy_common_cause_conditionally_identified(self):
        row,pin=q.analytic_fixture("common_cause")
        v=self.result(row,pin)
        self.assertEqual(v["models"],["common_cause"])
        self.assertFalse(v["science_admitted"])

    def test_impossible_toy_outcome_denied(self):
        a=copy.deepcopy(self.row);a["observed_xyz"]=[1,1,0]
        p=copy.deepcopy(self.pin);p["receipt_sha256"]=q.digest(a)
        self.assertEqual(self.result(row=a,pin=p)["status"],"OUTCOME_CONTRADICTS_WITNESS_VERSION_SPACE")

    def test_bad_do_target_denied(self):
        a=copy.deepcopy(self.row);a["do_target"]="Y"
        self.assertEqual(self.result(row=a)["status"],"INVALID_PUBLIC_INTERVENTION_ASSIGNMENT")

    def test_foreign_source_capture_pin_denied(self):
        a=copy.deepcopy(self.row);a["capture_id"]="DIFFERENT"
        self.assertEqual(self.result(row=a)["status"],"UNPINNED_OR_TAMPERED_PUBLIC_RECEIPT")

    def test_paired_coherence_denies_mismatch(self):
        a=copy.deepcopy(self.row);a["observed_xyz"]=[0,1,1]
        p=copy.deepcopy(self.pin);p["receipt_sha256"]=q.digest(a)
        self.assertEqual(self.result(row=a,pin=p)["status"],"DO_TARGET_MISMATCH")

    def test_public_observation_history_identity_drift_denied(self):
        changed = tuple((1,1,1) for _ in self.obs)
        v=q.assess(self.row, trusted_pin=self.pin, observations=changed)
        self.assertEqual(v["status"],"UNPINNED_OR_TAMPERED_PUBLIC_RECEIPT")

    def test_missing_public_history_digest_denied(self):
        p=copy.deepcopy(self.pin);del p["public_history_sha256"]
        self.assertEqual(self.result(pin=p)["status"],"INCOMPLETE_INDEPENDENT_TRUST_PIN")

    def test_local_fixture_never_new_first_use(self):
        for model in q.MODELS:
            row,pin=q.analytic_fixture(model)
            v=self.result(row,pin)
            self.assertEqual(v["new_first_use"],0)
            self.assertFalse(v["science_admitted"])

if __name__ == '__main__':unittest.main()
