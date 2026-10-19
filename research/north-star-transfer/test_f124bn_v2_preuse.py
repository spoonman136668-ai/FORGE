"""F124-BN v2 nonconsuming regression: authentic frozen source identities and
robust public-data-only learner. No registered FIT or heldout task issued.
"""
from __future__ import annotations

import hashlib,importlib.util,random
from pathlib import Path
import unittest
HERE=Path(__file__).resolve().parent


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,HERE/path)
    m=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


learn=load("bn_learner_unit","f124bn_v2_learner.py")
mix=load("bn_mix_unit","f124bn_v2_triangular_source.py")
word=load("bn_word_unit","f124bn_v2_coupled_source.py")
dev=load("bn_eval_unit","f124bn_v2_dev_eval.py")


class LearnedGF2Mechanism(unittest.TestCase):
    def test_learn_invertible_nonpermutation_coupling_with_six_public_bit_errors(self):
        rng=random.Random(814732)
        edges=[(rng.randrange(16),rng.randrange(16)) for _ in range(10)]
        edges=[(a,b) for a,b in edges if a!=b]
        self.assertGreaterEqual(len(edges),6)
        bias=0x5ca3
        def truth(x):
            for a,b in edges:
                x^=((x>>a)&1)<<b
            return x^bias
        xs=rng.sample(range(65536),48)
        public=[(x,truth(x)^(1 if i in (1,6,12,18,23,27) else 0))
                for i,x in enumerate(xs)]
        model,stats=learn.fit(public[:40],public[40:])
        self.assertEqual(stats["parameter_bits"],272)
        self.assertEqual(stats["check_bit_errors"],0)
        self.assertTrue(stats["training_FIT_only"])
        for x in range(0,65536,257):
            self.assertEqual(learn.forward(x,model),truth(x))
            self.assertEqual(learn.inverse(truth(x),model),x)

    def test_not_hardcoded_source_family_or_registered_ids(self):
        self.assertEqual(len(set(mix.FIT)&set(word.FIT)),0)
        self.assertEqual(len(set(mix.FIT)&set(mix.HOLDOUT)),0)
        self.assertEqual(len(set(word.FIT)&set(word.HOLDOUT)),0)
        for generator in (mix,word):
            for case in (900000,914000,915000,918100,919100,918227,919227,
                         902000,903000,-940,-939):
                with self.assertRaises(ValueError):
                    generator.make(case)
        for case in (900000,914000,915000,918100,919100,902000,903000):
            with self.assertRaises(RuntimeError):
                dev.identity(case)

    def test_causal_false_edge_with_identical_bit_inventory(self):
        model={"rows":tuple(1<<i for i in range(16)),"bias":0}
        roles=["rel_task_abc123def456:r"+str(j) for j in range(7)]
        chain=[{"from":str(j),"to":str(j+1),"role":roles[j],
                "src_bits":learn._value.__globals__.get("_unused", None)}
               for j in []]
        carry=[j*777 for j in range(8)]
        path=[{"from":str(j),"to":str(j+1),"role":roles[j],
               "src_bits":[(carry[j]>>k)&1 for k in range(16)],
               "dst_bits":[(carry[j+1]>>k)&1 for k in range(16)]}
              for j in range(7)]
        extra={"from":"detached","to":"dead","role":roles[3],
               "src_bits":[((12345)>>k)&1 for k in range(16)],
               "dst_bits":[((41923)>>k)&1 for k in range(16)]}
        graph={"start":"0","target":"7","roles":roles,
               "edges":path+[extra],"demos":[]}
        good,n=learn.causal_path(graph,model)
        self.assertTrue(good)
        self.assertEqual(n,7)
        import copy
        bad=copy.deepcopy(graph)
        bad["edges"][3]["src_bits"],bad["edges"][7]["src_bits"]=(
            bad["edges"][7]["src_bits"],bad["edges"][3]["src_bits"])
        accepted,_=learn.causal_path(bad,model)
        self.assertFalse(accepted)

    def test_unknown_unidentifiable_no_oracle_fallback(self):
        fit=[(0,0) for _ in range(40)]
        check=[(0,0) for _ in range(8)]
        with self.assertRaises(ValueError):
            learn.fit(fit,check)


if __name__=="__main__":
    unittest.main()
