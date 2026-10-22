"""Independent frozen M-R6 challenge tests on developer-smoke ONLY."""
import ast
import copy
import unittest
from pathlib import Path
import mass_r6_information_audit as a
from public_dev import PUBLIC_FAMILIES


class M_R6PublicInformation(unittest.TestCase):
    def test_all_eight_precommitted_trajectories_show_public_effect_but_no_encoder_signal(self):
        for fi, family in enumerate(PUBLIC_FAMILIES):
            for i in range(a.N_PER_FAMILY):
                with self.subTest(family=family,seed=i):
                    evidence=a.one_trajectory(fi,i)
                    s=evidence["summary"]
                    self.assertEqual(s["family"], family)
                    self.assertGreater(s["public_causal_event_count"],0)
                    self.assertEqual(s["r4_semantic_role_feature_active_rows"],0)
                    self.assertEqual(s["r4_causal_event_type_feature_active_rows"],0)
                    self.assertEqual(s["r4_history_key_role_bound_rows"],0)
                    self.assertEqual(len(s["original_public_teacher_trace_sha256"]),64)
                    self.assertGreater(s["training_rows"],0)

    def test_both_public_families_are_truly_shown_to_a_fitted_structured_model(self):
        report=a.audit()
        self.assertEqual(set(report["families"]), set(PUBLIC_FAMILIES))
        self.assertEqual(sum(len(x) for x in report["families"].values()), 8)
        self.assertGreater(report["public_causal_events_seen"],0)
        self.assertEqual(report["baseline_semantic_feature_activations"],0)
        self.assertEqual(report["structured_planner_training_updates"],0)
        self.assertEqual(report["structured_planner_public_event_fit_counts"],0)
        self.assertEqual(report["structured_planner_initial_delay_prior"],
                         report["structured_planner_postfit_delay_prior"])
        self.assertEqual(report["classification"],
                         "UNUSABLE_PUBLIC_EVENT_VOCABULARY_IN_R4_FEATURE_PIPELINE")
        self.assertEqual(report["scientific_disposition"],
                         "INFORMATION_EQUIVALENCE_NOT_ESTABLISHED")
        self.assertFalse(report["original_r6_frozen_DEV_reclassified"])
        self.assertFalse(report["scientific_first_use"])
        self.assertFalse(report["independent_hidden_h1_h2_used"])

    def test_all_sha_and_deterministic_bounded_replay(self):
        x=a.audit()
        y=a.audit()
        self.assertEqual(x,y)
        self.assertEqual(len(x["public_demo_trace_chain_sha256"]),64)
        self.assertEqual(x["candidate_r6_head"],
                         "b0074839fdc347d3ebf12f8d8806edf7bb0e76fa")
        self.assertEqual(x["scope"],
                         "EXACTLY_EIGHT_NONPROTECTED_FIT_SMOKE_DEMONSTRATIONS")

    def test_denies_new_seed_replay_or_nonprospective_fitting(self):
        for fi,i in ((-1,0),(2,0),(0,4),(1,-1)):
            with self.assertRaisesRegex(ValueError,"FROZEN_SMOKE_COHORT"):
                a.one_trajectory(fi,i)

    def test_no_hidden_original_controller_dispatch_or_r6_experiment(self):
        src=Path(a.__file__).read_text(encoding="utf-8")
        tree=ast.parse(src)
        forbidden={"experiment","run","score","dispatch","subprocess",
                   "eval","exec","create_child","download"}
        for node in ast.walk(tree):
            if isinstance(node,ast.Call):
                fn=node.func
                name=(fn.id if isinstance(fn,ast.Name) else
                      fn.attr if isinstance(fn,ast.Attribute) else "?")
                self.assertNotIn(name,forbidden)
        self.assertNotIn("protected_source",src)


if __name__=="__main__":
    unittest.main()
