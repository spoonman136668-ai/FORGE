"""F124-AN preregistered three-corruption source and source-blind learner."""
import unittest,inspect,math
from collections import Counter
import f124an_frozen_source as s
import f124an_calibrated_affine as learner
import f124am_example_affine_learner as historical
import f124am_terminal_competition as wing

class FrozenAN(unittest.TestCase):
    def test_source_lineage_and_symmetry(self):
        p=s.frozen()
        self.assertEqual(s.witness.blob(s.FREEZE),s.FREEZE_BLOB)
        self.assertEqual(p["lineage"]["parent_run"],39117302545)
        self.assertEqual(p["Yggdrasil"]["calibration_grid"],[
            {"residual":2,"margin":1},{"residual":3,"margin":1},
            {"residual":3,"margin":2},{"residual":3,"margin":4}])
        self.assertTrue(all(v is False for v in p["authority"].values()))
        for lane in s.COHORTS:
            self.assertTrue(set(s.COHORTS[lane]["TRAIN"]).isdisjoint(
                            s.COHORTS[lane]["DEV"]))
            cases=s.pairs(lane,"TRAIN")
            self.assertEqual(len(cases),48)
            self.assertEqual(Counter(x[2] for x in cases),
                Counter({f:12 for f in s.FAMILIES}))
            for seed,v,fam,op,nonce,pos,neg in cases:
                self.assertEqual(pos["demos"],neg["demos"])
                self.assertEqual(sum(s.relation(d["input_bits"],op)!=
                                     d["output_bits"] for d in pos["demos"]),3)
                if v==tuple(s.VECTORS[0]):
                    self.assertEqual(pos["demos"][0],pos["demos"][10])
                reference=s.am.old.prior.parent.original.parent.prior.parent.routes15
                self.assertEqual(reference(s.plain(pos,op,nonce),
                           relaxed=fam=="rotate4_tolerant"),1)
                self.assertEqual(reference(s.plain(neg,op,nonce),
                           relaxed=fam=="rotate4_tolerant"),0)

    def test_true_source_inverse_and_robust_abstention(self):
        v=s.am.to_bits(0xB59D)
        for op in s.OPERATORS["TRAIN"]+s.OPERATORS["DEV"]:
            self.assertEqual(s.relation(s.relation(v,op),op,True),v)
        for seed,v,f,op,nonce,p,n in s.pairs("Yggdrasil","TRAIN")[:8]:
            normalized,meta=learner.normalize(p,3,2)
            self.assertFalse(meta["learner"]["operator_name_known"])
            if normalized is not None:
                self.assertEqual(set(normalized),
                                 {"start","target","roles","edges"})
                self.assertEqual(len(normalized["roles"]),len(p["roles"]))
            self.assertLessEqual(meta["learner"]["trials"],768)
        code=inspect.getsource(learner)
        for forbidden in ("import f124an_frozen_source","source.plain(",
                          "routes15(","oracle(","relation("):
            self.assertNotIn(forbidden,code)

    def test_unchanged_one_packed_model_with_certified_inputs(self):
        base=[.6,.7,.9,.5,.85,.15,-.55]
        delta=[.05,-.03,.02,-.04]
        for seed,v,f,op,nonce,p,n in s.pairs("Wingless","TRAIN")[:8]:
            for graph in (p,n):
                normalized=s.plain(graph,op,nonce)  # SOURCE-ONLY CONDITIONING
                a,wa=wing.terminal_competitive(normalized,base,delta,0.)
                self.assertTrue(math.isfinite(a))
                self.assertEqual(wa["max_states_per_node"],1)
                self.assertEqual(wa["max_packed_bits_per_state"],12)
                self.assertLessEqual(wa["max_active"],64)
                for gamma in (0.,.1,.25,.5,1.):
                    score,work=wing.terminal_competitive(
                        normalized,base,delta,gamma)
                    self.assertTrue(math.isfinite(score))
                    self.assertEqual(work["max_states_per_node"],1)

if __name__=="__main__":unittest.main()
