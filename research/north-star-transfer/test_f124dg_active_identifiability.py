"""F124-DG source-free active causal identifiability and fairness tests.

New 201-204 synthetic causes, not consumed source-born scientific cases or
F124-DF 101-104. This validates equations and matching query budgets, not
a prospective discovery or a protected scientific first-use.
"""
import ast
import copy
from pathlib import Path
import sys
import unittest

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import f124dg_new_sourcefree_oracle as world
import f124dg_meta_rank_learner as learner
import f124dg_independent_active_control as control
import f124dg_budgeted_active_trial as trial

class CausalNullspaceAndBudget(unittest.TestCase):
    def test_fixed_sourcefree_and_exact_163_monomial_basis(self):
        self.assertEqual(world.SEEDS,(201,202,203,204))
        self.assertEqual(len(world.MONOMIALS),163)
        self.assertEqual(learner.WIDTH,163)
        self.assertEqual(control.W,163)
        for family in world.FAMILIES:
            for seed in world.SEEDS:
                data=world.born(family,seed)
                self.assertEqual((len(data["FIT"]),len(data["CHECK"]),
                                  len(data["HELDOUT"])),(24,8,8))
                self.assertEqual(data,world.born(family,seed))
                for episode in data.values():
                    for item in episode:learner.check_ep(item)
                self.assertEqual(world.response(family,seed,0),
                                 world.response(family,seed,0))
    def test_independent_learner_has_exact_same_features(self):
        for pair in range(256):
            self.assertEqual(learner.feature(pair),control.input_row(pair))
        for family in world.FAMILIES:
            data=world.born(family,201)
            fit=learner.supervised_rows(data["FIT"])
            rows=learner.basis(fit)
            self.assertLessEqual(len(rows),163)
            fitted=learner.solve(rows)
            self.assertTrue(all(learner.reconstruct(fitted,x)==y for x,y in fit))
    def test_explicit_unidentifiable_counterfactual(self):
        data=world.born(world.FAMILIES[0],201)
        rows=learner.supervised_rows(data["FIT"])
        null_basis=learner.basis([(x,0) for x,_ in rows])
        point=next((x for x in range(256)
                   if learner.independent(null_basis,x)),None)
        self.assertIsNotNone(point)
        # Two equally plausible zero- and null-polynomials agree on ALL
        # training inputs yet disagree on the new causal counterfactual.
        witness=learner.solve(learner.basis([(x,0) for x,_ in rows]+[(point,1)]))
        self.assertTrue(all(learner.reconstruct(witness,x)==0 for x,_ in rows))
        self.assertEqual(learner.reconstruct(witness,point),1)
    def test_equal_oracle_count_meta_and_independent_strong_peer(self):
        for family in world.FAMILIES:
            d=[trial.sourcefree_case(family,201,arm,16) for arm in trial.ARMS]
            for receipt in d:
                self.assertEqual(receipt["new_oracle_queries_consumed"],16)
                self.assertEqual(receipt["FIT_episodes"],24)
                self.assertEqual(receipt["CHECK_veto_episodes"],8)
                self.assertEqual(receipt["HELDOUT_positive_episodes"],8)
                self.assertFalse(receipt["science_accepted"])
                self.assertTrue(receipt["queries_distinct"])
                self.assertGreaterEqual(receipt["rank_gain_from_extra_information"],0)
                self.assertLessEqual(receipt["final_rank"],163)
            self.assertEqual(len({x["FIT_hash"] for x in d}),1)
            self.assertEqual(len({x["same_public_meta_score_sha256"] for x in d}),1)
            self.assertEqual(d[0]["final_rank"],d[1]["final_rank"])
            self.assertEqual(d[0]["diagnostic_HELDOUT_exact_positives_of_8"],
                             d[1]["diagnostic_HELDOUT_exact_positives_of_8"])
    def test_no_teacher_forcing_of_CHECK_or_HELDOUT_labels(self):
        d=world.born(world.FAMILIES[0],202)
        rows=learner.supervised_rows(d["FIT"])
        model={"weights":learner.solve(learner.basis(rows))}
        ep=copy.deepcopy(d["HELDOUT"][0]);perturbed=copy.deepcopy(ep)
        for e in perturbed["events"]:e["observed"]^=15
        self.assertEqual(learner.trajectory(model,ep),
                         learner.trajectory(model,perturbed))
    def test_learner_and_independent_peer_do_not_import_source_law(self):
        for name in ("f124dg_meta_rank_learner.py",
                     "f124dg_independent_active_control.py"):
            tree=ast.parse((HERE/name).read_text())
            imports=[]
            for node in ast.walk(tree):
                if isinstance(node,ast.Import):
                    imports.extend(x.name for x in node.names)
                elif isinstance(node,ast.ImportFrom):
                    imports.append(node.module or "")
            self.assertNotIn("f124dg_new_sourcefree_oracle",imports)
            self.assertFalse(any(v.startswith(("f124df_","f124cu_","f124cr_"))
                                 for v in imports))

if __name__=="__main__":unittest.main()
