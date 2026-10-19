"""Synthetic-only pre-source tests for frozen nonlinear confidence learner."""
from __future__ import annotations
import importlib.util
import random
from pathlib import Path
import unittest

PATH=Path(__file__).resolve().parent/"f124bo_nonlinear_learner.py"
spec=importlib.util.spec_from_file_location("bo_new_model",PATH)
model=importlib.util.module_from_spec(spec)
spec.loader.exec_module(model)


def bits(x):
    return [(x>>i)&1 for i in range(16)]


class NewLearningBeforeAnySource(unittest.TestCase):
    def test_fixed_budget_and_invertible_composition(self):
        self.assertEqual(model.BEAM,64)
        self.assertEqual(model.EXTENSION_BUDGET,8192)
        for params in ((1,0,0),(7,0x1234,0x0345),(413,0xc041,0xab12)):
            for x in range(0,65536,997):
                self.assertEqual(model.inverse(model.forward(x,params),params),x)

    def test_public_fit_synthetic_nonlinear_and_confidence(self):
        rng=random.Random(401941)
        truth=(5,3,2)
        xs=rng.sample(range(65536),48)
        pairs=[(x,model.forward(x,truth)^(1 if i in (2,6,13,18,29,37) else 0))
               for i,x in enumerate(xs)]
        fitted,receipt,plausible=model.learn(pairs[:40],pairs[40:])
        self.assertEqual(receipt["parameter_bits"],48)
        self.assertLessEqual(receipt["search_extensions"],8192)
        self.assertFalse(receipt["oracle_used"])
        # Reject is admissible, as no validation result can add evidence.
        if fitted is not None:
            self.assertIn(fitted,plausible)
            self.assertLessEqual(receipt["CHECK_errors"],2)

    def test_selective_abstention_on_ambiguous_sources(self):
        original={"start":"n0","target":"n2","roles":["r0","r1"],
                  "edges":[
                    {"from":"n0","to":"n1","role":"r0",
                     "src_bits":bits(9),"dst_bits":bits(14)},
                    {"from":"n1","to":"n2","role":"r1",
                     "src_bits":bits(14),"dst_bits":bits(19)}],
                  "demos":[]}
        params=(1,0,0)
        ok,receipt=model.selective_causal_path(original,params,(params,))
        self.assertTrue(ok)
        self.assertEqual(receipt["hops"],2)
        false={"start":"n0","target":"n2","roles":["r0","r1"],
               "edges":[dict(x) for x in original["edges"]],"demos":[]}
        false["edges"][1]["src_bits"]=bits(15)
        yes,_=model.selective_causal_path(false,params,(params,))
        self.assertFalse(yes)
        _,uncertain=model.selective_causal_path(original,params,
                                                (params,(1,0,1)))
        self.assertEqual(uncertain["decision"],"ABSTAIN_NONLINEAR_CONFIDENCE")

    def test_bad_or_insufficient_public_support_never_oracle_fallback(self):
        with self.assertRaises(ValueError):
            model.learn([(0,0)]*39,[(0,0)]*8)
        with self.assertRaises(ValueError):
            model.selective_causal_path({"start":"x"},None,())


if __name__=="__main__":
    unittest.main()
