"""Synthetic-only qualification of new compact nonlinear learned composition.

No registered FIT case, prior negative, source family or protected holdout.
"""
from __future__ import annotations

import importlib.util
import random
from pathlib import Path
import unittest

PATH=Path(__file__).resolve().parent/"f124bp_compact_learner.py"
spec=importlib.util.spec_from_file_location("f124bp_small_model",PATH)
model=importlib.util.module_from_spec(spec)
spec.loader.exec_module(model)


def bits(x):
    return [(x>>j)&1 for j in range(16)]


def independent_synthetic(model_true,seed,errors=(1,6,14,19,28,37)):
    r=random.Random(seed)
    xs=r.sample(range(65536),48)
    return [(x,model.forward(x,model_true)^(1 if i in errors else 0))
            for i,x in enumerate(xs)]


class CompactNonlinearCognition(unittest.TestCase):
    def test_four_byte_bounded_learner_six_noisy_observations(self):
        self.assertEqual(model.PARAMETER_BITS,32)
        self.assertEqual(model.PAIR_RESIDUAL_CAP,10240)
        self.assertEqual(model.COMPOSITE_CAP,640)
        for state in ((53,37,41,19),(1,0,1,0),(123,221,77,195)):
            public=independent_synthetic(state,700006+state[0])
            fitted,receipt,plausible=model.learn(public[:40],public[40:])
            self.assertIsNotNone(fitted,receipt)
            self.assertIn(fitted,plausible)
            self.assertEqual(receipt["parameter_bits"],32)
            self.assertTrue(receipt["FIT_ONLY_TRAINING"])
            self.assertFalse(receipt["CHECK_selected_model"])
            self.assertFalse(receipt["private_operator_or_graph_truth_used"])
            self.assertLessEqual(receipt["fit_bit_errors"],6)
            self.assertLessEqual(receipt["check_bit_errors"],2)
            for x in range(0,65536,503):
                self.assertEqual(model.forward(x,fitted),model.forward(x,state))
                self.assertEqual(model.inverse(model.forward(x,state),fitted),x)

    def test_confident_path_true_and_matched_graph_swap_false(self):
        state=(53,37,41,19)
        fit=independent_synthetic(state,970314)
        trained,_,plausible=model.learn(fit[:40],fit[40:])
        self.assertIsNotNone(trained)
        roles=["synthetic_rel_"+str(j) for j in range(7)]
        carries=[100+700*j for j in range(8)]
        steps=[{"from":str(j),"to":str(j+1),"role":roles[j],
                "src_bits":bits(model.forward(carries[j],state)),
                "dst_bits":bits(carries[j+1])} for j in range(7)]
        decoy={"from":"d","to":"e","role":roles[3],
               "src_bits":bits(model.forward(50493,state)),
               "dst_bits":bits(10973)}
        graph={"start":"0","target":"7","roles":roles,
               "edges":steps+[decoy],"demos":[]}
        yes,trace=model.causal_consensus(graph,trained,plausible)
        self.assertTrue(yes,trace)
        self.assertEqual(trace["hops"],7)
        import copy
        counter=copy.deepcopy(graph)
        counter["edges"][3]["src_bits"],counter["edges"][7]["src_bits"]=(
            counter["edges"][7]["src_bits"],counter["edges"][3]["src_bits"])
        no,details=model.causal_consensus(counter,trained,plausible)
        self.assertFalse(no)
        self.assertIn("REJECT",details["decision"])

    def test_unknown_or_uncertain_abstains_without_oracle(self):
        state=(53,37,41,19)
        model_a=(53,37,41,19)
        another=(51,37,41,19)
        role=["rel0","rel1"]
        carry=1777
        graph={"start":"a","target":"c","roles":role,"demos":[],
               "edges":[{"from":"a","to":"b","role":"rel0",
                         "src_bits":bits(model.forward(900,model_a)),
                         "dst_bits":bits(carry)},
                        {"from":"b","to":"c","role":"rel1",
                         "src_bits":bits(model.forward(carry,model_a)),
                         "dst_bits":bits(999)}]}
        accept,trace=model.causal_consensus(graph,state,(model_a,another))
        self.assertFalse(accept)
        self.assertEqual(trace["decision"],"ABSTAIN_NONUNIQUE_INVERSE")
        public=independent_synthetic(state,971414)
        # Introduce a large independent CHECK disturbance after FIT has been fitted.
        check=[(x,y^65535) for x,y in public[40:]]
        result,receipt,plausible=model.learn(public[:40],check)
        self.assertIsNone(result)
        self.assertFalse(receipt["confident"])
        self.assertEqual(plausible,())

    def test_budget_and_domain_fail_closed(self):
        for bad in ((0,0,1,0),(1,0,0,0)):
            with self.assertRaises(ValueError):
                model.forward(5,bad)
        with self.assertRaises(ValueError):
            model.learn([(0,0)]*39,[(0,0)]*8)
        with self.assertRaises(ValueError):
            model.causal_consensus({"start":"s"},None,())


if __name__=="__main__":
    unittest.main()
