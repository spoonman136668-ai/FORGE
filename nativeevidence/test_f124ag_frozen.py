"""F124-AG preregistration, parent-parity and source-only hop mechanisms."""
import unittest,inspect,math
from collections import Counter
import f124ag_frozen_source as f
import f124ag_transition_models as models
import f124ae_scoring_transfer as previous

class FrozenAG(unittest.TestCase):
    def test_preimplementation_source_and_disjointness(self):
        p=f.frozen()
        self.assertEqual(p["lineage"]["parent_actions_run"],39108391392)
        self.assertEqual(f.guard.blob(f.FREEZE),f.FREEZE_BLOB)
        self.assertEqual(p["Yggdrasil"]["eta_grid"],list(f.ETAS))
        self.assertEqual(p["Wingless"]["eta_grid"],list(f.ETAS))
        self.assertTrue(all(v is False for v in p["authority"].values()))
        for lane in ("Wingless","Yggdrasil"):
            self.assertTrue(set(f.COHORTS[lane]["FIT"]).isdisjoint(
                            f.COHORTS[lane]["DEV"]))
            cases=f.pairs(lane,"FIT")
            self.assertEqual(len(cases),48)
            self.assertEqual(Counter(x[2] for x in cases),
                             Counter({name:12 for name in f.FAMILIES}))
            for _,_,fam,p,n in cases:
                self.assertEqual(f.prior.parent.routes15(
                    p,relaxed=fam=="one_bit_relaxed_keys"),1)
                self.assertEqual(f.prior.parent.routes15(
                    n,relaxed=fam=="one_bit_relaxed_keys"),0)

    def test_ygg_eta0_original_true_bit_parity_7_plus_9(self):
        base=[.4,.9,.65,.75,.8,.2,-.5];delta=[1.3,.2]
        for _,_,_,p,n in f.pairs("Yggdrasil","FIT")[:8]:
            for g in (p,n):
                new,raw,ratio,work=models.ygg_transition(g,base,delta,0.)
                old,oraw,oratio,ow=previous.anchored_score(
                    g,base,delta,10)
                self.assertEqual((new,raw,ratio),(old,oraw,oratio))
                self.assertTrue(all(work[k]==ow[k] for k in ow))
                self.assertEqual(work["transition_penalty_evaluations"],0)
                self.assertLessEqual(work["max_active"],7)
                self.assertLessEqual(work["max_retained"],9)
                for eta in f.ETAS:
                    score,_,_,work=models.ygg_transition(g,base,delta,eta)
                    self.assertTrue(math.isfinite(score))
                    self.assertLessEqual(work["max_active"],7)
                    self.assertLessEqual(work["max_retained"],9)

    def test_wing_eta0_bit_parity_one_packed_state_only(self):
        base=[.6,.7,.9,.5,.85,.15,-.55];delta=[.05,-.03,.02,-.04]
        for _,_,_,p,n in f.pairs("Wingless","FIT")[:8]:
            for g in (p,n):
                score,work=models.wing_transition(g,base,delta,0.)
                old,ow=previous.frozen_packed(g,base,delta)
                self.assertEqual(score,old)
                self.assertTrue(all(work[k]==ow[k] for k in ow))
                self.assertEqual(work["transition_packed_channel_comparisons"],0)
                self.assertLessEqual(work["max_active"],64)
                self.assertEqual(work["max_states_per_node"],1)
                for eta in f.ETAS:
                    new,ww=models.wing_transition(g,base,delta,eta)
                    self.assertTrue(math.isfinite(new))
                    self.assertLessEqual(ww["max_active"],64)

    def test_fit_grid_original_source_only(self):
        for lane in ("Wingless","Yggdrasil"):
            base=([.4,.9,.65,.75,.8,.2,-.5] if lane=="Yggdrasil"
                  else [.6,.7,.9,.5,.85,.15,-.55])
            delta=([1.3,.2] if lane=="Yggdrasil"
                   else [.05,-.03,.02,-.04])
            winner,grid=models.fit(lane,f.pairs(lane,"FIT"),base,delta)
            self.assertEqual(len(grid),6)
            self.assertIn(winner["eta"],f.ETAS)
            self.assertEqual(winner["paired"],max(x["paired"] for x in grid))
        for fn in (models.ygg_transition,models.wing_transition):
            src=inspect.getsource(fn)
            for forbidden in ("routes15(","positive_route(","public_reference(",
                              '"DEV"',"paired_admit(","protected("):
                self.assertNotIn(forbidden,src)

if __name__=="__main__":
    unittest.main()
