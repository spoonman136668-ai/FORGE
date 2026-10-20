"""Adversarial F124/LCRM01-G source metadata screening tests; no download."""
import unittest
from dataclasses import replace
import lcrm01g_temporal_source_screen as q

class ProvenanceAndTemporalCounterfactualScreen(unittest.TestCase):
    def test_all_frozen_versions_have_exact_record_pins(self):
        self.assertEqual(set(q.RELEASES), {"1.0.0", "1.1.0", "1.2.0"})
        self.assertEqual(q.RELEASES["1.2.0"], ("23095083", 12150, "shared_noise"))

    def test_v10_twins_never_pass_even_fake_full_custody(self):
        m=q.candidate("1.0.0", provider_sha256="a"*64,
            independent_source_witness="CLAIM_ONLY", raw_manifest_independently_verified=True,
            observed_pre_do_equal=True)
        self.assertEqual(q.screen(m)["status"],"DENY_INDEPENDENT_NOISE_TWINS_ARE_NOT_EPISODE_COUNTERFACTUALS")

    def test_newer_unfetched_dataset_stays_metadata_only(self):
        for v in ("1.1.0", "1.2.0"):
            self.assertEqual(q.screen(q.candidate(v))["status"], "PUBLIC_METADATA_ONLY_RAW_SOURCE_CUSTODY_NOT_VERIFIED")

    def test_default_latest_or_mutated_version_is_rejected(self):
        for v in ("latest", "1.3.0", "0.0.0"):
            self.assertEqual(q.screen(replace(q.candidate(),version=v))["status"],"DENY_SOURCE_OR_VERSION_PIN_MISMATCH")

    def test_mutated_repository_sha_and_tree_rejected(self):
        original=q.candidate()
        for field in ("repository","commit","tree","bench_blob","dataset"):
            m=replace(original,**{field:"TAMPER"})
            self.assertEqual(q.screen(m)["status"],"DENY_SOURCE_OR_VERSION_PIN_MISMATCH")

    def test_wrong_version_specific_zenodo_record_is_rejected(self):
        self.assertEqual(q.screen(replace(q.candidate(),zenodo_record="20919553"))["status"],"DENY_RELEASE_METADATA_MISMATCH")

    def test_episode_count_and_noise_contract_drift_denied(self):
        for field,value in (("episode_count",10800),("pair_mode","independent_noise")):
            self.assertEqual(q.screen(replace(q.candidate(),**{field:value}))["status"],"DENY_RELEASE_METADATA_MISMATCH")

    def test_graph_or_future_y_leak_denied(self):
        for key in ("model_public_inputs_include_hidden_graph","model_public_inputs_include_future_outcome"):
            self.assertEqual(q.screen(q.candidate(**{key:True}))["status"], "DENY_HIDDEN_SCM_OR_FUTURE_OUTCOME_LEAKAGE")

    def test_pre_do_mismatch_denied(self):
        self.assertEqual(q.screen(q.candidate(observed_pre_do_equal=False))["status"],"DENY_PRE_INTERVENTION_PAIRING_VIOLATION")

    def test_bow_graph_requires_v12(self):
        self.assertEqual(q.screen(q.candidate("1.1.0",source_family="bow_graph"))["status"],"DENY_FAMILY_NOT_RELEASED_IN_VERSION")

    def test_bow_graph_underclaimed_authenticated_source_still_abstains(self):
        m=q.candidate(source_family="bow_graph",provider_sha256="a"*64,
            independent_source_witness="CLAIM_ONLY",raw_manifest_independently_verified=True,
            observed_pre_do_equal=True)
        self.assertEqual(q.screen(m)["status"], "NONIDENTIFIED_BOW_GRAPH_OBSERVATION_ONLY_ABSTENTION_REQUIRED")
        self.assertFalse(q.screen(m)["counterfactual_execution_authorized"])

    def test_known_v12_suite_even_fake_full_provenance_cannot_self_admit(self):
        m=q.candidate(provider_sha256="a"*64,independent_source_witness="CLAIM_ONLY",
             raw_manifest_independently_verified=True,observed_pre_do_equal=True)
        r=q.screen(m)
        self.assertEqual(r["status"],"INDEPENDENT_CUSTODY_AND_FIRSTUSE_REVIEW_REQUIRED")
        self.assertFalse(r["scientific_source_admitted"])

    def test_bad_digest_format_not_accepted(self):
        m=q.candidate(provider_sha256="xyz", independent_source_witness="CLAIM_ONLY",
            raw_manifest_independently_verified=True)
        self.assertEqual(q.screen(m)["status"],"DENY_INVALID_PROVIDER_DIGEST_FORMAT")

    def test_no_source_witness_never_passes(self):
        m=q.candidate(provider_sha256="a"*64,raw_manifest_independently_verified=True)
        self.assertEqual(q.screen(m)["status"],"PUBLIC_METADATA_ONLY_RAW_SOURCE_CUSTODY_NOT_VERIFIED")

    def test_unrecognized_structure_denied(self):
        self.assertEqual(q.screen(q.candidate(source_family="secret_oracle"))["status"],"DENY_UNSUPPORTED_STRUCTURE")

    def test_every_possible_current_example_declines_real_science(self):
        for v in q.RELEASES:
            for family in ("back_door", "bow_graph", "invalid"):
                r=q.screen(q.candidate(v,source_family=family))
                self.assertEqual(r["original_scientific_firstuse_consumed"],0)
                self.assertFalse(r["scientific_source_admitted"])
                self.assertFalse(r["controller_dispatch_authorized"])

    def test_summary_cannot_claim_download_or_transfer(self):
        record=q.source_only_record()
        self.assertFalse(record["public_dataset_downloaded"])
        self.assertFalse(record["actual_provider_bytes_inspected"])
        self.assertFalse(record["scientific_transfer_proven"])

if __name__=="__main__":unittest.main()
