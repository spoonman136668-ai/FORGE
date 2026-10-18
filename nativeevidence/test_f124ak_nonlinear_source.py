"""F124-AK frozen prospective nonlinear source and single-state test."""
import inspect,unittest,math
from collections import Counter
import f124ak_frozen_source as src
import f124ak_nonlinear_learner as learner
import f124ak_one_packed_contrast as packed
import f124ae_scoring_transfer as old

class FrozenAK(unittest.TestCase):
    def test_source_protocol(self):
        p=src.frozen()
        self.assertEqual(src.witness.blob(src.FREEZE),src.FREEZE_BLOB)
        self.assertEqual(p["lineage"]["parent_qualified_run"],39112892476)
        self.assertEqual(p["Yggdrasil"]["support_grid"],list(learner.SUPPORT))
        self.assertEqual(p["Wingless"]["beta_grid"],list(learner.BETAS))
        self.assertTrue(all(v is False for v in p["authority"].values()))
        self.assertTrue(set(src.OPERATORS["TRAIN"]).isdisjoint(
                        src.OPERATORS["HOLDOUT"]))
        for lane in ("Wingless","Yggdrasil"):
            self.assertTrue(set(src.COHORTS[lane]["TRAIN"]).isdisjoint(
                            src.COHORTS[lane]["HOLDOUT"]))
            x=src.pairs(lane,"TRAIN")
            self.assertEqual(len(x),48)
            self.assertEqual(Counter(v[2] for v in x),
                             Counter({f:12 for f in src.FAMILIES}))
            for seed,vector,f,op,tag,p,n in x:
                self.assertEqual(p["demos"],n["demos"])
                self.assertEqual(len(p["demos"]),24)
                relaxed=f=="rotate4_tolerant"
                self.assertEqual(src.parent.original.parent.prior.parent.routes15(
                    src.plain(p,op,tag),relaxed=relaxed),1)
                self.assertEqual(src.parent.original.parent.prior.parent.routes15(
                    src.plain(n,op,tag),relaxed=relaxed),0)

    def test_true_nonlinear_and_carry_not_bit_permutation(self):
        x=src.bits(0x69A5)
        for op in src.OPERATORS["TRAIN"]+src.OPERATORS["HOLDOUT"]:
            self.assertEqual(src.relation(src.relation(x,op),op,True),x)
            self.assertNotEqual(src.relation(x,op),x)

    def test_example_only_hypothesis_without_source_oracle(self):
        for seed,vec,fam,op,tag,pos,neg in src.pairs("Yggdrasil","TRAIN")[:12]:
            restored,meta=learner.normalize(pos,24)
            self.assertTrue(meta["learn"]["unique"])
            self.assertEqual(restored,src.plain(pos,op,tag))
        m=inspect.getsource(learner)
        for illegal in ("import f124ak_frozen_source",
                        "truth_mapping(","source.relation(","plain(",
                        "routes15(","oracle(", '"HOLDOUT"'):
            self.assertNotIn(illegal,m)
        selection,grid=learner.fit_support(
            src.pairs("Yggdrasil","TRAIN"),
            [.4,.9,.65,.75,.8,.2,-.5],[1.3,.2])
        self.assertEqual(len(grid),5)
        self.assertEqual(selection["correct"],max(i["correct"] for i in grid))

    def test_ygg7_9_and_original_one_state_beta_zero(self):
        ybase=[.4,.9,.65,.75,.8,.2,-.5];ydelta=[1.3,.2]
        for *_,p,n in src.pairs("Yggdrasil","TRAIN")[:6]:
            for g in (p,n):
                score,w,meta=learner.ygg(g,ybase,ydelta,24)
                self.assertIsNotNone(w)
                self.assertLessEqual(w["max_active"],7)
                self.assertLessEqual(w["max_retained"],9)
        base=[.6,.7,.9,.5,.85,.15,-.55];delta=[.05,-.03,.02,-.04]
        for *_,p,n in src.pairs("Wingless","TRAIN")[:8]:
            for g in (p,n):
                normalized,meta=learner.normalize(g,24)
                self.assertIsNotNone(normalized)
                oldscore,oldwork=old.frozen_packed(normalized,base,delta)
                zero,work=packed.wing_competitive(normalized,base,delta,0.)
                self.assertEqual(zero,oldscore)
                self.assertEqual(work,oldwork)
                self.assertEqual(work["max_states_per_node"],1)
                self.assertEqual(work["max_packed_bits_per_state"],12)
                for beta in learner.BETAS:
                    scored,w=packed.wing_competitive(
                        normalized,base,delta,beta)
                    self.assertTrue(math.isfinite(scored))
                    self.assertEqual(w["max_states_per_node"],1)
        pick,grid=learner.fit_wing_beta(src.pairs("Wingless","TRAIN"),
                 base,delta,24)
        self.assertEqual(len(grid),5)
        self.assertEqual(pick["correct"],max(x["correct"] for x in grid))

if __name__=="__main__":unittest.main()
