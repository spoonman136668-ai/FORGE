"""F139 native third-lane DEV: deterministic, debuggable, non-token, not science.

These are tests of the existing F139 development engine's optional Hybrid
branch, not authorization to schedule or run Hybrid original science.
"""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from f139 import dev_learning as owner_dev
from f139 import hybrid_development as hybrid

SHA = os.environ.get("GITHUB_SHA") or ("a" * 40)


class HybridThirdLaneDevelopmentTests(unittest.TestCase):
    def test_f139_existing_qualification_stays_two_lane_and_hybrid_is_explicit(self):
        self.assertEqual(owner_dev.LANES, ("Wingless", "Yggdrasil"))
        self.assertEqual(owner_dev.HYBRID_DEV_PREVIEW_LANE, "TTT-Hybrid")
        legacy = owner_dev.run("Qualification", 1, SHA)
        self.assertEqual([x["lane"] for x in legacy["lanes"]],
                         ["Wingless", "Yggdrasil"])
        for values in [
            ("TTT-Hybrid", False), ("Qualification", True),
            ("Wingless", True), ("Yggdrasil", True),
        ]:
            with self.subTest(lane=values[0], preview=values[1]):
                with self.assertRaisesRegex(ValueError, "LANE_FORBIDDEN"):
                    owner_dev.run(values[0], 1, SHA,
                                  hybrid_development_only=values[1])

    def test_same_f139_engine_runs_real_bounded_hybrid_dev_but_not_project_science(self):
        a = owner_dev.run("TTT-Hybrid", 1, SHA,
                          hybrid_development_only=True)
        b = owner_dev.run("TTT-Hybrid", 1, SHA,
                          hybrid_development_only=True)
        self.assertEqual(a["lanes"], b["lanes"])
        self.assertEqual(len(a["lanes"]), 1)
        self.assertEqual(a["lanes"][0]["lane"], "TTT-Hybrid")
        self.assertEqual(a["schema"], "forge.f139.private-cognition-development.v1")
        self.assertTrue(a["real_cpu_training_executed"])
        self.assertFalse(a["protected_first_use"])
        self.assertEqual(a["paid_api_calls"], 0)
        self.assertEqual(a["optimizer_policy_mutations"], 0)
        self.assertEqual(a["scientific_originals_dispatched"], 0)
        row = a["lanes"][0]
        evidence = row["hybrid_source_bound_debug_and_negative_evidence"]
        self.assertEqual(evidence["schema"], hybrid.SCHEMA)
        self.assertEqual(evidence["repository"], "spoonman136668-ai/TTT-Hybrid-Lab")
        self.assertEqual(evidence["prior_negative_pr"], 82)
        self.assertEqual(evidence["prior_specialized_superiority"],
                         "FAILED_NOT_RELABELED")
        self.assertFalse(evidence["actual_hybrid_research_training_executed"])
        self.assertFalse(evidence["scientific_first_use"])
        self.assertFalse(evidence["independent_scientific_validation"])
        self.assertFalse(evidence["native_hybrid_model_promoted"])
        self.assertFalse(evidence["matched_total_flops_verified"])
        self.assertTrue(evidence["non_token_cognitive_interface"])
        self.assertTrue(evidence["debuggable_per_action_state_and_causal_effect"])
        self.assertTrue(evidence["deterministic_cold_replay_verified"])
        self.assertEqual(evidence["owner_tickets_dispatched"], 0)
        self.assertEqual(evidence["protected_holdouts_accessed"], 0)
        candidate, control = row["trained_candidate"], row["trained_control"]
        self.assertEqual(candidate["search_evaluations"], 64)
        self.assertEqual(control["search_evaluations"], 64)
        self.assertEqual(candidate["training_cohort_sha256"],
                         control["training_cohort_sha256"])
        self.assertEqual(candidate["transfer_cohort_sha256"],
                         control["transfer_cohort_sha256"])
        self.assertEqual(candidate["training_total"], 96)
        self.assertEqual(control["transfer_total"], 96)
        self.assertTrue(candidate["cold_replay_bit_exact"])
        self.assertTrue(control["cold_replay_bit_exact"])
        self.assertNotEqual(candidate["model_class"], control["model_class"])
        self.assertEqual(row["classification"],
                         ("POSITIVE_DEVELOPMENT"
                          if row["transfer_correct_delta"] > 0
                          else "NEGATIVE_OR_TIE_DEVELOPMENT"))
        self.assertFalse(row["new_architecture_proven"])

    def test_causal_observations_only_and_hidden_evaluator_label_cannot_leak(self):
        rows = hybrid.cohort(1, 2)
        baseline = hybrid.evaluate(rows, [0.5, 0.15], True, full_trace=True)
        tampered = json.loads(json.dumps(rows))
        for row in tampered:
            row["target_context_evaluator_only"] *= -1
        changed = hybrid.evaluate(tampered, [0.5, 0.15], True, full_trace=True)
        self.assertEqual(baseline["decision_trace_sha256"],
                         changed["decision_trace_sha256"])
        self.assertEqual(baseline["debug_examples"], changed["debug_examples"])
        self.assertEqual(baseline["correct"] + changed["correct"], 96)
        for example in baseline["debug_examples"]:
            self.assertGreater(len(example["steps"]), 0)
            for step in example["steps"]:
                self.assertEqual(set(step), {
                    "executed_action", "actual_consequence", "inferred_effect",
                    "state_before", "state_after", "contradiction_reset"})
                self.assertIn(step["executed_action"], (-1, 1))
        self.assertNotIn("target_context_evaluator_only",
                         json.dumps(baseline))

    def test_no_cross_source_or_generation_reuse(self):
        a = hybrid.run(1, SHA)
        b = hybrid.run(1, SHA)
        c = hybrid.run(2, SHA)
        self.assertEqual(a, b)
        self.assertNotEqual(a["trained_candidate"]["training_cohort_sha256"],
                            c["trained_candidate"]["training_cohort_sha256"])
        self.assertNotEqual(a["trained_candidate"]["transfer_cohort_sha256"],
                            c["trained_candidate"]["transfer_cohort_sha256"])
        self.assertEqual(a["prior_negative_candidate_sha"],
                         "5cb633d129c0500dbb857ecafa02cacc122abb09")

    def test_reject_unsafe_history_model_and_unqualified_project_sources(self):
        for history in (
            [], [[1, float("nan")]], [[0, 0.5]],
            [[True, 0.5]], [[1, 0.5, "future"]],
            [{"latent": 1}],
        ):
            with self.subTest(history=history):
                with self.assertRaises(hybrid.HybridDevDenied):
                    hybrid.infer(history, [0.5, 0.15], True)
        for params in ([0.11, 0.15], [0.5, float("nan")],
                       [0.5], ["0.5", 0.15]):
            with self.assertRaises(hybrid.HybridDevDenied):
                hybrid.infer([[1, .5]], params, True)
        for gen in (0, -1, 100001, True, "1"):
            with self.assertRaises(hybrid.HybridDevDenied):
                hybrid.cohort(gen, 1)
        for source in ("0" * 39, "z" * 40, "A" * 40):
            with self.assertRaises(hybrid.HybridDevDenied):
                hybrid.run(1, source)

    def test_source_identity_and_no_live_ticket_or_worker_integration(self):
        with patch.dict(os.environ, {"GITHUB_SHA": "b" * 40}):
            with self.assertRaisesRegex(ValueError, "EXACT_SOURCE_DRIFT"):
                owner_dev.run("TTT-Hybrid", 1, SHA,
                              hybrid_development_only=True)
        root = Path(__file__).resolve().parents[1]
        local = (root / "f139/local_controller.py").read_text("utf-8")
        worker = (root / "f139/verify_ticket.py").read_text("utf-8")
        # Owner admission code now recognizes the third native DEV identity
        # but the original SQLite table and active owner still reject it
        # until an explicit owner-only migration and signed project issue.
        self.assertIn('LANES = {"Wingless", "Yggdrasil", "Qualification", "TTT-Hybrid"}', local)
        self.assertIn('LANES = {"Wingless", "Yggdrasil", "Qualification", "TTT-Hybrid"}', worker)
        self.assertIn("upgrade-hybrid-lane", local)
        self.assertIn("HYBRID_NATIVE_SIGNED_INTENT_REQUIRED", worker)
        self.assertIn("HYBRID_NATIVE_RECEIPT_REQUIRED", worker)

    def test_exclusive_cli_output_with_opt_in_and_no_rewrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            outfile = Path(tmp) / "hybrid-dev.json"
            args = ["dev_learning", "--lane", "TTT-Hybrid",
                    "--hybrid-development-only", "--generation", "1",
                    "--source-sha", SHA, "--output", str(outfile)]
            with patch("sys.argv", args):
                owner_dev.main()
            raw = outfile.read_bytes()
            proof = json.loads(raw)
            self.assertEqual(proof["lanes"][0]["lane"], "TTT-Hybrid")
            with patch("sys.argv", args):
                with self.assertRaisesRegex(ValueError, "EXCLUSIVE_OUTPUT"):
                    owner_dev.main()
            self.assertEqual(outfile.read_bytes(), raw)


if __name__ == "__main__":
    unittest.main()
