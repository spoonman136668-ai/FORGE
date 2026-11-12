"""Adversarial source-only checks; never download or execute a scientific case."""
import unittest
from dataclasses import replace
from lcrm01f_public_source_audit import BENCHMARKS, SourceMetadata, inspect, sourcebirth_scope, UPSTREAM_CODE_COMMIT, UPSTREAM_DOWNLOAD_SPEC_BLOB


def public_candidate(key="k562"):
    return SourceMetadata(repository="causalbench/causalbench",
                          code_commit=UPSTREAM_CODE_COMMIT,
                          download_spec_blob=UPSTREAM_DOWNLOAD_SPEC_BLOB,
                          dataset_key=key, download_url=BENCHMARKS[key],
                          producer_perturbation_labels=True)

class PublicSourceReadOnlyTriage(unittest.TestCase):
    def test_both_published_sources_remain_unqualified(self):
        for key in BENCHMARKS:
            with self.subTest(key=key):
                r=inspect(public_candidate(key))
                self.assertEqual(r["level"],"BIBLIOGRAPHIC_ONLY")
                self.assertFalse(r["original_scientific_source_admitted"])
                self.assertEqual(r["scientific_firstuse_consumed"],0)
    def test_wrong_code_commit_fails_closed(self):
        c=replace(public_candidate(),code_commit="a"*40)
        self.assertEqual(inspect(c)["level"],"REJECT")
    def test_wrong_upstream_spec_blob_fails_closed(self):
        c=replace(public_candidate(),download_spec_blob="f"*40)
        self.assertEqual(inspect(c)["level"],"REJECT")
    def test_wrong_download_url_fails_closed(self):
        c=replace(public_candidate(),download_url="https://example.org/fake")
        self.assertEqual(inspect(c)["level"],"REJECT")
    def test_false_intervention_label_fails_closed(self):
        c=replace(public_candidate(),producer_perturbation_labels=False)
        self.assertEqual(inspect(c)["level"],"REJECT")
    def test_unpinned_download_is_not_admitted(self):
        c=replace(public_candidate(),provider_payload_digest="a"*64)
        self.assertEqual(inspect(c)["level"],"BIBLIOGRAPHIC_ONLY")
    def test_independent_identity_claim_does_not_prove_exogeneity(self):
        c=replace(public_candidate(),provider_payload_digest="a"*64,independent_witness_identity="CLAIM_ONLY")
        self.assertEqual(inspect(c)["level"],"DOCUMENTED_PERTURBATION_ONLY")
    def test_perturbational_but_not_sequential_not_accepted(self):
        c=replace(public_candidate(),provider_payload_digest="a"*64,independent_witness_identity="CLAIM",verified_exogenous_assignment=True)
        self.assertEqual(inspect(c)["level"],"NONSEQUENTIAL_INTERVENTION_ONLY")
    def test_sequential_without_paired_counterfactual_not_accepted(self):
        c=replace(public_candidate(),provider_payload_digest="a"*64,independent_witness_identity="CLAIM",verified_exogenous_assignment=True,ordered_entity_intervention_episodes=True)
        self.assertEqual(inspect(c)["level"],"SEQUENCE_BUT_NOT_COUNTERFACTUAL")
    def test_user_supplied_all_positive_fields_do_not_create_authority(self):
        c=replace(public_candidate(),provider_payload_digest="a"*64,independent_witness_identity="CLAIM",verified_exogenous_assignment=True,ordered_entity_intervention_episodes=True,paired_counterfactual_truth=True)
        r=inspect(c)
        self.assertEqual(r["level"],"AUTHORITY_REVIEW_REQUIRED")
        self.assertFalse(r["original_scientific_source_admitted"])
        self.assertFalse(r["counterfactual_claim_authorized"])
        self.assertFalse(r["controller_dispatch_authorized"])
    def test_sourcebirth_signature_does_not_attest_do(self):
        r=sourcebirth_scope()
        self.assertFalse(r["signed_statement_includes_do_assignment_fields"])
        self.assertFalse(r["cryptographic_birthing_implies_intervention_authenticity"])
    def test_sourcebirth_does_not_support_LCRM_lane(self):
        self.assertFalse(sourcebirth_scope()["recognizes_LCRM01_sourcebirth_lane"])

if __name__ == "__main__":unittest.main()
