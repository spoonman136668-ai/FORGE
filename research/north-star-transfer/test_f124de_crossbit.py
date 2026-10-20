"""F124-DE mathematical / sourcefree engineering qualification.

Tests general learned degree<=4 polynomial representation without source
law being imported by candidate or peer. The original synthetic seeds
are fixed, and sourcefree claims must never be mistaken for an external
independently birthed scientific source or a native FLOP equality proof.
"""
from __future__ import annotations
import ast
import copy
from pathlib import Path
import sys
import unittest
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import f124de_sourceonly_crossbit as source
import f124de_sparse_crossbit_learner as learner
import f124de_independent_full_anf as peer
import f124de_original_trial as trial

class GeneralCrossBitLearning(unittest.TestCase):
    def test_frozen_new_source_only_inventory_and_matched_negatives(self):
        self.assertEqual(source.SEEDS,(91,92,93,94))
        self.assertEqual(len(source.FAMILIES),4)
        for family in source.FAMILIES:
            for seed in source.SEEDS:
                public=source.born(family,seed)
                self.assertEqual(public,source.born(family,seed))
                self.assertEqual([len(public[k]) for k in ("FIT","CHECK","HELDOUT")],[24,8,8])
                for ep in public["HELDOUT"]:
                    neg=source.negative(ep)
                    self.assertNotEqual(neg,ep)
                    self.assertEqual(sorted(x["observed"] for x in neg["events"]),
                                     sorted(x["observed"] for x in ep["events"]))
    def test_complete_generic_degree4_eight_bit_boolean_features(self):
        self.assertEqual(learner.WIDTH,peer.COLS==163 and 163)
        self.assertEqual(learner.MONOMIALS,tuple(peer.MONO))
        self.assertEqual(len(learner.PAIR_CANDIDATES),10)
        for v in (0,1,17,85,127,255):
            self.assertEqual(learner.features(v),peer.encoded_anf(v))
    def test_bitparallel_compiler_exact_for_arbitrary_polynomial_coefficients(self):
        params=[1,3,1<<162,0x123456789abcdef,((1<<163)-1)]
        for p in params:
            table=learner.compile_lut((p,p^1,p^7,p))
            for value in range(256):
                bit=learner.eval_coeff(p,value)
                for j,m in enumerate((p,p^1,p^7,p)):
                    self.assertEqual((table[j]>>value)&1,
                                     learner.eval_coeff(m,value),
                                     (p,value,j,bit))
    def test_generic_nonbitwise_mod16_addition_algebra_is_representable(self):
        # Degree<=4 is a non-arithmetic-specific polynomial class. Verify
        # the mathematical operator at all 256 nibble pairs independently
        # of the hidden causal source generator. No FIT/HELDOUT tuning.
        bit_add=[(learner.features(a|(b<<4)),(a+b)&15)
                 for a in range(16) for b in range(16)]
        for bit in range(4):
            theta,rank=learner.eliminate(bit_add,bit)
            self.assertIsNotNone(theta,(bit,rank))
            self.assertEqual(sum(learner.eval_coeff(theta,a|(b<<4))
                              !=(((a+b)>>bit)&1)
                              for a in range(16) for b in range(16)),0)
    def test_training_control_and_candidate_see_same_public_sequences(self):
        d=source.born(source.FAMILIES[0],91)
        a,receipt=learner.fit(d["FIT"])
        b,br=peer.train(d["FIT"])
        self.assertIsNotNone(a,receipt)
        self.assertIsNotNone(b,br)
        self.assertEqual(receipt["FIT_bit_errors"],0)
        self.assertEqual(br["FIT_bit_errors"],0)
        self.assertEqual(len(a["planes"]),4)
        self.assertEqual(len(b["truth_bitplanes"]),4)
        for family in (source.FAMILIES[0],source.FAMILIES[1]):
            for seed in source.SEEDS[:2]:
                e=source.born(family,seed)
                one=trial.evaluate(family,seed,"sparse_crossbit_compact")
                two=trial.evaluate(family,seed,"independent_equal_degree4_ANF")
                for key in ("FIT_public_SHA256","CHECK_public_SHA256",
                            "heldout_public_SHA256"):
                    self.assertEqual(one[key],two[key])
                self.assertEqual(one["new_scientific_firstuse_consumed"],0)
                self.assertEqual(two["new_scientific_firstuse_consumed"],0)
                self.assertEqual(one["FIT_possible_pair_unique_cell_max"]<=192,True)
    def test_predictions_never_teacher_force_heldout_observed_output(self):
        d=source.born(source.FAMILIES[0],91)
        for fit,rollout in ((learner.fit,learner.rollout),(peer.train,peer.rollout)):
            model,_=fit(d["FIT"])
            self.assertIsNotNone(model)
            ep=d["HELDOUT"][0];flipped=copy.deepcopy(ep)
            for row in flipped["events"]:row["observed"]^=15
            self.assertEqual(rollout(model,ep),rollout(model,flipped))
    def test_source_author_not_imported_by_independent_learners(self):
        for name in ("f124de_sparse_crossbit_learner.py",
                     "f124de_independent_full_anf.py"):
            tree=ast.parse((HERE/name).read_text())
            imports=[]
            for n in ast.walk(tree):
                if isinstance(n,ast.Import):imports += [x.name for x in n.names]
                elif isinstance(n,ast.ImportFrom):imports.append(n.module or "")
            self.assertNotIn("f124de_sourceonly_crossbit",imports)
            self.assertNotIn("f124de_sparse_crossbit_learner",
                             imports if name.endswith("independent_full_anf.py") else [])
            self.assertFalse(any(x.startswith(("f124cr_","f124co_","f124cu_"))
                                for x in imports))
    def test_generic_underidentification_without_priors(self):
        # Even at MAX unique two-nibble observed pairs, 192 eight-step
        # public input/label rows do NOT identify all 256 arbitrary table
        # entries. Fitting must acknowledge the inductive bias.
        d=source.born(source.FAMILIES[0],91)
        samples=learner.training_rows(d["FIT"])
        observed={(x[0],x[2]) for x,_ in samples}
        self.assertLessEqual(len(observed),192)
        self.assertGreaterEqual(256-len(observed),64)
if __name__=="__main__":unittest.main()
