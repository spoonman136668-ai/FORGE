"""F124-CW frozen source-free identifiability and optimization invariants.

No authentic scientific source task may be imported, generated, fit or
opened. These are separate known-grammar deterministic engineering fixtures.
"""
from __future__ import annotations
import ast
import json
from pathlib import Path
import unittest
import f124cw_feasibility_audit as f

HERE=Path(__file__).resolve().parent

class FeasibilitySourceFree(unittest.TestCase):
    def test_exact_all_256_version_space_preserves_true_synthetic_key(self):
        for regime in f.REGIMES:
            for seed in f.SEEDS:
                keys,fit,check,heldout=f.fixture(regime,seed)
                hypotheses=f.version_space(fit,regime)
                self.assertIn(keys,hypotheses)
                self.assertLessEqual(len(hypotheses),256)
                self.assertEqual(len(fit),24)
                self.assertEqual(len(check),8)
                self.assertEqual(len(heldout),8)
                self.assertTrue(all(f.compatible(ep,regime,keys)
                                    for ep in fit+check+heldout))
    def test_consistent_hypotheses_only_shrink_as_FIT_episodes_increase(self):
        for regime in f.REGIMES:
            for seed in f.SEEDS:
                counts=[f.evidence(regime,seed,budget)[
                   "consistent_hypotheses_after_sequential_FIT"]
                   for budget in f.BUDGETS]
                self.assertEqual(counts,sorted(counts,reverse=True))
                self.assertGreaterEqual(min(counts),1)
    def test_dense_vs_rare_context_support_is_observed_not_assumed(self):
        for seed in f.SEEDS:
            dense=f.evidence("dense",seed,24)
            sparse=f.evidence("sparse",seed,24)
            self.assertEqual(dense["observed_supervised_events"],192)
            self.assertEqual(sparse["observed_supervised_events"],192)
            self.assertEqual(sparse["known_grammar_hypotheses"],256)
            self.assertTrue(0<=sparse["rare_intervention_observations"]<=192)
            self.assertFalse(sparse["consumed_scientific_source_used"])
    def test_no_source_private_oracle_imports_or_prior_original_science(self):
        tree=ast.parse((HERE/"f124cw_feasibility_audit.py").read_text())
        imported=[]
        for node in ast.walk(tree):
            if isinstance(node,ast.Import):
                imported.extend(x.name for x in node.names)
            elif isinstance(node,ast.ImportFrom):
                imported.append(node.module or "")
        self.assertFalse(any(x.startswith("f124cu_") or x.startswith("f124cr_")
                             or x.startswith("f124cn_") or x.startswith("f124co_")
                             for x in imported))
        self.assertEqual(f.SEEDS,(0,1,2,3))
        self.assertEqual(f.BUDGETS,(2,4,8,12,24))
    def test_privileged_known_grammar_is_not_strong_trained_control(self):
        diagnostic=f.evidence("sparse",0,24)
        self.assertIn("consistent_hypotheses_after_sequential_FIT",diagnostic)
        self.assertNotIn("neural_model_scientific_accepted",diagnostic)
        report=f.interpret([f.evidence(regime,seed,24)
                            for regime in f.REGIMES for seed in f.SEEDS],
            [{"regime":regime,"arm":arm,"full_sequence_training_epochs":45,
              "natural_admission":False} for regime in f.REGIMES
             for arm in ("attentive","gated")])
        self.assertFalse(report["scientific_transfer_proven"])
        self.assertFalse(report["complete_CPU_RSS_nonregression_proven"])
        self.assertEqual(report["prospective_firstuse_cases_consumed"],0)

if __name__=="__main__":
    unittest.main()
