"""F124-DA non-scientific learned-operator qualification.

Tests source law novelty (nonaffine two-input truth tables), paired public
information, FIT-only operator discovery, independent full-budget peer,
teacher-label isolation and fail-closed scope. The heldout score is reported
by the original prospective workflow, not used to tune source seeds.
"""
from __future__ import annotations
import ast
import copy
from pathlib import Path
import sys
import unittest

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import f124da_sourcefree_operators as src
import f124da_learned_operator_search as learner
import f124da_independent_operator_peer as peer
import f124da_edge_operator_control as edge
import f124da_operator_trial as trial

class NewOperatorInduction(unittest.TestCase):
    def test_sourcefree_lexicons_not_supplied_or_old_originals(self):
        self.assertEqual(src.REGIMES,("unseen_boolean_operator_lexicon",
                                     "fourbit_carry_outside_lexicon"))
        self.assertEqual(src.SEEDS,(51,52,53,54))
        for regime in src.REGIMES:
            for seed in src.SEEDS:
                public=src.born(regime,seed)
                self.assertEqual(set(public),{"FIT","CHECK","HELDOUT"})
                self.assertEqual([len(public[x]) for x in ("FIT","CHECK","HELDOUT")],
                                 [24,8,8])
                self.assertEqual(public,src.born(regime,seed))
                for ep in public["FIT"]+public["CHECK"]+public["HELDOUT"]:
                    learner.validate(ep)
    def test_hidden_truth_tables_are_genuinely_nonlinear(self):
        import random
        for seed in src.SEEDS:
            rng=random.Random(12451000+seed*991)
            private=src.hidden(rng,src.REGIMES[0])
            self.assertEqual(len(private),4)
            for a,b,z,table in private:
                self.assertLess(a,8)
                self.assertGreaterEqual(b,8);self.assertLess(b,16)
                self.assertGreaterEqual(z,16);self.assertLess(z,20)
                self.assertEqual(src.nonlinear(table),1)
    def test_learned_operator_lexicon_and_independent_peer_fit_without_source(self):
        for seed in (51,52):
            data=src.born(src.REGIMES[0],seed)
            model,receipt=learner.train(data["FIT"])
            other,receipt_other=peer.train(data["FIT"])
            self.assertIsNotNone(model,receipt)
            self.assertIsNotNone(other,receipt_other)
            self.assertEqual(receipt["FIT_bit_errors"],0)
            self.assertEqual(receipt_other["FIT_bit_errors"],0)
            self.assertEqual(receipt["operators_learned"],4)
            self.assertEqual(len(model["learned_operators"]),4)
            self.assertEqual(len(other["operators"]),4)
            self.assertEqual(receipt["per_bit_search_budget"],7600)
            self.assertTrue(receipt_other["same_full_7600_wirings_each_bit"])
    def test_online_inference_never_teacher_forces_ground_truth(self):
        data=src.born(src.REGIMES[0],51)
        for fitter,predict in ((learner.train,learner.rollout),
                               (peer.train,peer.predict)):
            model,_=fitter(data["FIT"])
            ep=data["HELDOUT"][0]
            changed=copy.deepcopy(ep)
            for row in changed["events"]:row["observed"]^=15
            self.assertEqual(predict(model,ep),predict(model,changed))
    def test_independent_edge_learner_trains_six_complete_role_relations(self):
        fit=src.born(src.REGIMES[0],51)["FIT"]
        model,receipt=edge.train(fit)
        self.assertIsNotNone(model,receipt)
        self.assertEqual(receipt["trained_complete_directed_role_pairs"],6)
        self.assertEqual(receipt["FIT_rows"],192)
    def test_equal_public_fits_and_natural_admission_not_science(self):
        results=[trial.eval_case(src.REGIMES[0],51,arm)
                 for arm in ("learned_lexicon","independent_equal_lexicon",
                             "edge_lexicon")]
        for key in ("FIT_public_hash","CHECK_public_hash","HELDOUT_public_hash"):
            self.assertEqual(len({row[key] for row in results}),1)
        for row in results:
            self.assertFalse(row["scientific_success_accepted"])
            self.assertEqual(row["scientific_firstuse_cases"],0)
            self.assertTrue(row["hidden_truth_tables_and_wire_indices_not_passed_to_models"])
    def test_candidate_and_peer_not_importing_source_or_each_other(self):
        for fname in ("f124da_learned_operator_search.py",
                      "f124da_independent_operator_peer.py"):
            tree=ast.parse((HERE/fname).read_text())
            names=[]
            for n in ast.walk(tree):
                if isinstance(n,ast.Import):names += [z.name for z in n.names]
                elif isinstance(n,ast.ImportFrom):names.append(n.module or "")
            self.assertFalse(any(x.startswith(("f124da_sourcefree_operators",
                 "f124cu_","f124cz_outofclass_fixture")) for x in names))
        self.assertNotIn("f124da_independent_operator_peer",
                         (HERE/"f124da_learned_operator_search.py").read_text())

if __name__=="__main__":unittest.main()
