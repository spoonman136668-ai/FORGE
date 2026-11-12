"""Adversarial source-only interface controls: no suite samples or generator."""
import unittest
from dataclasses import replace
import lcrm01h_release_boundary as m

class SourceOnlyPlanTests(unittest.TestCase):
    def test_frozen_public_design_is_only_metadata_preflight(self):
        r=m.screen(m.SourcePlan());self.assertTrue(r["model_interface_screen_pass"])
        self.assertEqual(r["status"],"PUBLIC_MODEL_INTERFACE_ONLY_PROVIDER_UNVERIFIED")
        self.assertFalse(r["real_counterfactual_firstuse_authorized"])
    def test_no_mutated_provenance(self):
        for kw in ({"version":"1.0.0"},{"version":"latest"},
                   {"zenodo_record":"20919553"},{"commit":"0"*40},
                   {"registry_blob":"0"*40},{"repository":"fake/repo"}):
            with self.subTest(kw=kw):self.assertEqual(m.screen(replace(m.SourcePlan(),**kw))["status"],"DENY_VERSION_OR_CODE_PROVENANCE_DRIFT")
    def test_no_non_fit_or_holdout_labels(self):
        for split in ("CHECK","HELDOUT","TEST","UNKNOWN"):
            self.assertEqual(m.screen(replace(m.SourcePlan(),input_split=split))["status"],"DENY_NOT_FIT_PUBLIC_INPUT")
    def test_independent_noise_not_counterfactual(self):
        self.assertEqual(m.screen(replace(m.SourcePlan(),shared_noise_claim=False))["status"],"DENY_INDEPENDENT_NOISE_NOT_EPISODE_COUNTERFACTUAL")
    def test_never_pass_evaluator_outputs_into_model(self):
        for forbidden in m.HIDDEN:
            p=replace(m.SourcePlan(),fields=tuple(sorted(m.ALLOWED | {forbidden})))
            self.assertEqual(m.screen(p)["status"],"DENY_HIDDEN_OR_UNMATCHED_MODEL_INPUT")
    def test_missing_or_extra_model_input_rejected(self):
        p=replace(m.SourcePlan(),fields=tuple(sorted(m.ALLOWED-{"public_query_target"})))
        self.assertEqual(m.screen(p)["status"],"DENY_HIDDEN_OR_UNMATCHED_MODEL_INPUT")
    def test_duplicate_public_input_field_rejected(self):
        p=replace(m.SourcePlan(),fields=m.SourcePlan().fields+("public_query_target",))
        self.assertEqual(m.screen(p)["status"],"DENY_DUPLICATE_MODEL_INPUT_FIELD")
    def test_wrong_time_normalization_rejected(self):
        for encoding in ("index/(T-1)","step","latest"):
            self.assertEqual(m.screen(replace(m.SourcePlan(),query_encoding=encoding))["status"],"DENY_RELEASE_QUERY_TIME_ENCODING_MISMATCH")
    def test_no_post_intervention_observations(self):
        self.assertEqual(m.screen(replace(m.SourcePlan(),prefix_stop=31))["status"],"DENY_FUTURE_OBSERVATION_OR_TIME_DRIFT")
    def test_no_invented_lagged_mediator_effect(self):
        self.assertEqual(m.screen(replace(m.SourcePlan(),query_row=30))["status"],"DENY_MEDIATOR_QUERY_BEFORE_LAGGED_EFFECT")
    def test_no_out_of_range_query(self):
        self.assertEqual(m.screen(replace(m.SourcePlan(),query_row=100))["status"],"DENY_FUTURE_OBSERVATION_OR_TIME_DRIFT")
    def test_bool_time_rejected(self):
        self.assertEqual(m.screen(replace(m.SourcePlan(),query_row=True))["status"],"DENY_NONINTEGER_OR_BOOLEAN_TIME")
    def test_direct_self_query_not_credited(self):
        self.assertEqual(m.screen(replace(m.SourcePlan(),query_kind="in_window_self_query"))["status"],"DENY_SELF_QUERY_OR_UNSUPPORTED_EVALUATION")
    def test_bow_graph_observation_only_counterfactual_abstains(self):
        self.assertEqual(m.screen(replace(m.SourcePlan(),structure="bow_graph"))["status"],"DENY_OBSERVATION_ONLY_NONIDENTIFIED_CAUSAL_CLAIM")
    def test_bow_graph_prediction_without_causal_claim_still_only_metadata(self):
        r=m.screen(replace(m.SourcePlan(),structure="bow_graph",model_counterfactual_claim=False))
        self.assertTrue(r["model_interface_screen_pass"])
        self.assertFalse(r["real_counterfactual_firstuse_authorized"])
    def test_unknown_family_rejected(self):
        self.assertEqual(m.screen(replace(m.SourcePlan(),structure="hidden_oracle"))["status"],"DENY_UNKNOWN_CAUSAL_STRUCTURE")
    def test_fake_all_positive_custody_never_authorizes(self):
        p=replace(m.SourcePlan(),provider_manifest_pinned=True,actual_pairing_raw_verified=True,independent_custody=True,exact_download_sha256="a"*64)
        r=m.screen(p)
        self.assertEqual(r["status"],"CLAIMED_CUSTODY_REQUIRES_EXTERNAL_INDEPENDENT_AUTHORITY")
        self.assertFalse(r["real_counterfactual_firstuse_authorized"])
        self.assertEqual(r["scientific_firstuse_consumed"],0)
    def test_bad_checksum_format_is_not_a_provider_certificate(self):
        p=replace(m.SourcePlan(),exact_download_sha256="g"*64)
        self.assertEqual(m.screen(p)["status"],"DENY_INVALID_DOWNLOAD_DIGEST")

if __name__=="__main__":unittest.main()
