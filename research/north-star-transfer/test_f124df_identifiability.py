"""F124-DF source-free mathematical proof and engineering safety.

Preflight does NOT open fresh 101-104 heldouts or run new trial: synthetic
mathematical 256-pair truth tables and independent example FIT design
establish arity, nullspace/identifiability and solver consistency without
tuning on the original prospective sourcefree evaluation.
"""
from __future__ import annotations
import ast
import random
import sys
from pathlib import Path
import unittest
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import f124df_postfit_diagnostic as diagnosis
import f124df_sourceonly_new_rotation as source
import f124de_sparse_crossbit_learner as learner
import f124de_independent_full_anf as peer

class RotationIdentifiabilityProof(unittest.TestCase):
    def test_complete_two_operand_mathematics_are_representable(self):
        for rotation in (0,1,2):
            def truth(a,b):
                s=(a+b)&15
                return s if rotation==0 else ((s<<rotation)|(s>>(4-rotation)))&15
            q=diagnosis.algebraic_normal_form_of_truth(truth)
            self.assertTrue(q["source_is_representable_with_degree4"],(rotation,q))
            self.assertEqual(q["max_true_algebraic_degree"],4)
            self.assertEqual(len(q["exact_unrestricted_256_pair_ANF_degrees"]),4)
    def test_163_polynomial_features_and_independent_equal_peer(self):
        self.assertEqual(learner.WIDTH,163)
        self.assertEqual(peer.COLS,163)
        self.assertEqual(learner.MONOMIALS,tuple(peer.MONO))
        for raw in (0,1,2,3,17,85,127,255):
            self.assertEqual(learner.features(raw),peer.encoded_anf(raw))
    def test_explicit_nonuniqueness_witness_matches_all_training_inputs(self):
        rng=random.Random(34912)
        rows=[]
        for i in range(192):
            inputs=tuple(rng.randrange(16) for _ in range(5))
            output=(inputs[0]+inputs[2])&15
            rows.append((inputs,output))
        pair=(0,2)
        q=diagnosis.explicit_nullspace_witness(rows,pair)
        self.assertLess(q["rank"],163)
        self.assertGreater(q["nullity"],0)
        self.assertTrue(q["witness_exists"])
        self.assertTrue(q["unobserved_witness_proves_nonidentification"])
        polynomial=int(q["nullspace_polynomial_bitmask_hex"],16)
        observed={row[0][0]+(row[0][2]<<4) for row in rows}
        self.assertNotIn(q["different_unobserved_input"],observed)
        for x,_ in rows:
            self.assertEqual(learner.eval_coeff(polynomial,x[0]+(x[2]<<4)),0)
        self.assertEqual(learner.eval_coeff(polynomial,q["different_unobserved_input"]),1)
    def test_independent_mathematical_original_true_pair_solver_fits(self):
        data=[]
        for a in range(16):
            for b in range(16):
                s=(a+b)&15
                v=((s<<1)|(s>>3))&15
                raw=a+(b<<4)
                data.append((learner.features(raw),v))
        for bit in range(4):
            fitted,rank=learner.eliminate(data,bit)
            separate,independent_rank=peer.solve(data,bit)
            self.assertIsNotNone(fitted,(bit,rank))
            self.assertIsNotNone(separate,(bit,independent_rank))
            self.assertEqual(rank,163)
            self.assertEqual(independent_rank,163)
            self.assertTrue(all(learner.eval_coeff(fitted,a+(b<<4))
                      ==((((((a+b)&15)<<1)|(((a+b)&15)>>3))&15)>>bit&1)
                      for a in range(16) for b in range(16)))
    def test_only_exact_new_synthetic_roster_and_no_source_import_into_models(self):
        self.assertEqual(source.SEEDS,(101,102,103,104))
        self.assertEqual(len(source.FAMILIES),4)
        for name in ("f124de_sparse_crossbit_learner.py",
                     "f124de_independent_full_anf.py"):
            imports=[]
            for node in ast.walk(ast.parse((HERE/name).read_text())):
                if isinstance(node,ast.Import):
                    imports += [item.name for item in node.names]
                elif isinstance(node,ast.ImportFrom):imports.append(node.module or "")
            self.assertNotIn("f124df_sourceonly_new_rotation",imports)
            self.assertNotIn("f124df_postfit_diagnostic",imports)

if __name__=="__main__":unittest.main()
