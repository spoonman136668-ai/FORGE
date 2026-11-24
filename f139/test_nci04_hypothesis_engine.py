"""Unit, runtime-execution, and negative-control tests for nci04_hypothesis_engine."""
from __future__ import annotations

import base64
import json
import unittest
from unittest.mock import patch

from f139 import test_nci04_fresh_successor_producer as proposal_fixture
from f139.nci04_fresh_curriculum import select_next
from f139.nci04_fresh_worker_protocol import SOURCE, TARGET, TARGET_TREE
from f139.nci04_hypothesis_engine import (
    ESTIMATORS, PREREG_SCHEMA, SCHEMA, SUPPORT_GATES, TARGET_ARCHITECTURES,
    TIE_POLICIES, HypothesisEngineDenied, compose_yggdrasil_method,
    generate_yggdrasil_hypothesis_pool, select_next_hypothesis,
    verify_candidate_ast_safety,
)


class HypothesisEngineTests(unittest.TestCase):
    def setUp(self):
        fixture = proposal_fixture.FreshSourceProposalTests(
            "test_two_distinct_finite_nonreplaying_candidates")
        fixture.setUp()
        self.fixture = fixture
        first = fixture.proposal()
        second = fixture.proposal({first["after_sha256"]})
        self.spent = {first["after_sha256"], second["after_sha256"]}
        self.last_verified = second["after_sha256"]

    def pool(self, *, spent=None):
        with patch("f139.nci04_hypothesis_engine.ACCEPTED_NATIVE_BLOB",
                   self.fixture.blob):
            return generate_yggdrasil_hypothesis_pool(
                before=proposal_fixture.SOURCE_CODE,
                seed_intent=self.fixture.seed,
                consumed_after=self.spent if spent is None else spent,
                last_verified_after=self.last_verified,
            )

    def test_distinct_architectures_preserved(self):
        self.assertEqual(TARGET_ARCHITECTURES, {"Yggdrasil", "Wingless", "TTT-Hybrid"})

    def test_generates_32_unique_preregistered_compositional_hypotheses(self):
        pool = self.pool()
        expected_total = len(ESTIMATORS) * len(SUPPORT_GATES) * len(TIE_POLICIES)
        self.assertEqual(expected_total, 32)
        self.assertEqual(len(pool), 32)
        self.assertEqual(pool, self.pool())
        after_hashes = {item["plan"]["after_sha256"] for item in pool}
        prereg_hashes = {item["preregistration"]["preregistration_sha256"] for item in pool}
        self.assertEqual(len(after_hashes), 32)
        self.assertEqual(len(prereg_hashes), 32)
        for item in pool:
            prereg = item["preregistration"]
            self.assertEqual(prereg["schema"], PREREG_SCHEMA)
            self.assertEqual(prereg["target_architecture"], "Yggdrasil")
            self.assertFalse(prereg["frozen_protocol"]["scientific_first_use"])
            self.assertEqual(prereg["frozen_protocol"]["paid_model_calls"], 0)
            self.assertFalse(prereg["frozen_protocol"]["auto_promote_checkpoint"])
            self.assertEqual(item["plan"]["schema"], SCHEMA)
            self.assertEqual(item["selection"]["cost_units"], 2)

    def test_compatible_with_existing_curriculum_selector(self):
        pool = self.pool()
        history = [{
            "after_sha256": self.last_verified,
            "intent_sha256": "b" * 64,
            "stage": "VERIFIED",
            "terminal_evidence_sha256": "c" * 64,
        }]
        chosen = select_next(
            history=history,
            proposals=[item["selection"] for item in pool],
            source_sha=SOURCE,
            target_tree_sha=TARGET_TREE,
            remaining_cost_units=4,
            spent_after_sha256=frozenset(self.spent),
        )
        self.assertIsNotNone(chosen)
        self.assertIn(chosen["after_sha256"], {i["plan"]["after_sha256"] for i in pool})

    def test_generated_methods_execute_cleanly_and_preserve_counts(self):
        pool = self.pool()
        for item in pool:
            issue = json.loads(item["plan"]["body"])
            raw_intent = base64.b64decode(issue["intent_base64"])
            intent = json.loads(raw_intent)
            source_code = base64.b64decode(intent["after_base64"]).decode("utf-8")
            ns: dict = {}
            exec(compile(source_code, "<candidate>", "exec"), ns, ns)
            cls = ns["PublicCausalCells"]
            cells = cls()
            # Arm 0 wins strongly on cell 0 (8 vs 8 balanced trials)
            cells._counts[0] = [[0, 8], [8, 0]]
            before_counts = [[list(a) for a in c] for c in cells._counts]
            axes = item["preregistration"]["axes"]
            mname = f"choose_hyp_{axes['estimator']}_{axes['support_gate']}_{axes['tie_policy']}"
            choice = getattr(cells, mname)(0)
            self.assertEqual(choice, 0, f"{mname} failed to pick dominant arm 0")
            # Negative control: exact action-null tie on cell 1 (8/8 equal outcomes)
            cells._counts[1] = [[4, 4], [4, 4]]
            null_choice = getattr(cells, mname)(1)
            self.assertIsNone(null_choice, f"{mname} failed action-null tie check")
            # Verify cell counts were never mutated by readout
            self.assertEqual(cells._counts[0], before_counts[0])

    def test_evidence_conditioned_failure_guided_and_ablation_selection(self):
        pool = self.pool()
        failed = [{"estimator": "jeffreys", "support_gate": "min1", "tie_policy": "abstain"}]
        pick = select_next_hypothesis(pool, failed_axes=failed)
        self.assertIsNotNone(pick)
        axes = pick["preregistration"]["axes"]
        self.assertNotEqual(axes["estimator"], "jeffreys")
        self.assertNotEqual(axes["support_gate"], "min1")
        self.assertNotEqual(axes["tie_policy"], "abstain")

        verified = [{"estimator": "asymmetric_loss", "support_gate": "min4", "tie_policy": "abstain"}]
        pick_abl = select_next_hypothesis(pool, verified_axes=verified)
        self.assertIsNotNone(pick_abl)
        a2 = pick_abl["preregistration"]["axes"]
        dist = sum(a2[k] != verified[0][k] for k in ("estimator", "support_gate", "tie_policy"))
        self.assertEqual(dist, 1)

    def test_negative_controls_fail_closed_on_mutation_or_import(self):
        bad_import = (
            "class PublicCausalCells:\n"
            "    def bad_fn(self):\n"
            "        import os\n"
            "        return None\n"
        )
        with self.assertRaisesRegex(HypothesisEngineDenied, "FORBIDDEN_IMPORT"):
            verify_candidate_ast_safety(bad_import, "bad_fn")

        bad_mut = (
            "class PublicCausalCells:\n"
            "    def bad_mut(self):\n"
            "        self._counts[0][0][0] = 1\n"
            "        return 0\n"
        )
        with self.assertRaisesRegex(HypothesisEngineDenied, "CELL_MUTATION_FORBIDDEN"):
            verify_candidate_ast_safety(bad_mut, "bad_mut")

        with self.assertRaisesRegex(HypothesisEngineDenied, "AXIS_VALUE_INVALID"):
            compose_yggdrasil_method("transformer_attention", "min1", "abstain")


if __name__ == "__main__":
    unittest.main()
