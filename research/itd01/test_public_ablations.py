"""ITD-01 R3: public-only learning ablations, no protected first-use."""
import ast
import json
import unittest
from pathlib import Path

from public_dev import PUBLIC_FAMILIES
from run_public_ablations import run, NAME_ORDER


class PublicDevelopmentAblations(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = run(17, 8, 3)

    def test_real_training_compared_to_no_training_on_matching_public_tasks(self):
        d = self.result
        self.assertTrue(d["development_evidence_only"])
        self.assertEqual(d["authority"], "NONE_PUBLIC_DEV_ONLY")
        self.assertFalse(d["scientific_first_use"])
        self.assertFalse(d["source_birth_attested"])
        self.assertFalse(d["independent_transfer_qualified"])
        self.assertFalse(d["protected_h1_h2_accessed"])
        self.assertFalse(d["ckb_plane_accessed"])
        self.assertEqual(d["accepted_ref_mutations"], 0)
        self.assertEqual(d["eval_tasks_per_family"], 3)
        self.assertEqual(d["training_tasks_per_family"], 8)
        self.assertEqual([x["agent"] for x in d["agents"]], list(NAME_ORDER))
        for model in d["agents"]:
            self.assertGreater(model["training_updates"], 0)
            self.assertNotEqual(model["fitted_state_sha256"],
                                model["original_untrained_state_sha256"])
            self.assertGreater(model["retained_learned_state_bytes"], 0)
            for family in PUBLIC_FAMILIES:
                f = model["public_family_outcomes"][family]
                self.assertEqual(f["public_tasks"], 3)
                self.assertEqual(f["paired_trained_wins"] +
                                 f["paired_reset_wins"] +
                                 f["paired_ties"], 3)
                self.assertEqual(f["paired_reward_delta"],
                                 f["paired_trained_wins"] -
                                 f["paired_reset_wins"])
                self.assertEqual(len(f["trained_public_trace_sha256"]), 64)
                self.assertEqual(len(f["reset_public_trace_sha256"]), 64)

    def test_public_outcome_identity_is_deterministic_not_a_new_source_birth(self):
        again = run(17, 8, 3)
        a = self.result
        self.assertEqual(a["shared_training_public_experience_chain_sha256"],
                         again["shared_training_public_experience_chain_sha256"])
        for x, y in zip(a["agents"], again["agents"]):
            self.assertEqual(x["fitted_state_sha256"], y["fitted_state_sha256"])
            self.assertEqual(x["public_family_outcomes"], y["public_family_outcomes"])
        self.assertFalse(again["scientific_first_use"])
        self.assertFalse(again["independent_transfer_qualified"])

    def test_frozen_public_budgets_fail_closed(self):
        for params in [(999, 8, 2), (17, 0, 2), (17, 351, 2),
                       (17, 8, 0), (17, 8, 61)]:
            with self.subTest(params=params), self.assertRaises(ValueError):
                run(*params)

    def test_no_private_or_legacy_research_imports_or_dispatch(self):
        tree = ast.parse(Path(__file__).with_name("run_public_ablations.py")
                         .read_text(encoding="utf-8"))
        allowed = {"__future__", "argparse", "hashlib", "json", "time",
                   "public_dev", "public_baselines", "run_public_baselines"}
        blocked_names = {"dispatch", "Popen", "exec", "eval", "compile",
                         "__import__"}
        for n in ast.walk(tree):
            if isinstance(n, (ast.Import, ast.ImportFrom)):
                names = ([a.name.split(".")[0] for a in n.names]
                         if isinstance(n, ast.Import)
                         else [(n.module or "").split(".")[0]])
                for name in names:
                    self.assertIn(name, allowed)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name):
                self.assertNotIn(n.func.id, blocked_names)
        self.assertNotIn("source_birth_attested=True",
                         Path(__file__).with_name("run_public_ablations.py")
                         .read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
