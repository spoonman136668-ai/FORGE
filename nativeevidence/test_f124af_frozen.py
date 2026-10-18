"""F124-AF frozen source, original cost/ranking and no oracle in models."""
import inspect,math,unittest
from collections import Counter
import f124af_frozen_source as s
import f124af_contrast_margin as m
import f124ae_scoring_transfer as old

class F124AFFrozen(unittest.TestCase):
    def test_protocol_origin(self):
        p=s.frozen()
        self.assertEqual(s.source_witness.blob(s.FREEZE),s.FREEZE_BLOB)
        self.assertEqual(p["lineage"]["qualified_run"],39107592267)
        self.assertEqual(p["Yggdrasil"]["lambda_grid"],list(s.LAMBDAS))
        self.assertEqual(p["Wingless"]["beta_grid"],list(s.BETAS))
        self.assertTrue(all(v is False for v in p["authority"].values()))
        for lane in ("Wingless","Yggdrasil"):
            self.assertTrue(set(s.COHORTS[lane]["FIT"]).isdisjoint(
                            s.COHORTS[lane]["DEV"]))
            cases=s.pairs(lane,"FIT")
            self.assertEqual(Counter(x[2] for x in cases),
                             Counter({f:12 for f in s.FAMILIES}))
            for _,_,family,p,n in cases:
                self.assertEqual(s.parent.routes15(p,relaxed=
                                 family=="one_bit_relaxed_keys"),1)
                self.assertEqual(s.parent.routes15(n,relaxed=
                                 family=="one_bit_relaxed_keys"),0)

    def test_ygg_original_rank_and_readout_exact(self):
        base=[.4,.9,.65,.75,.8,.2,-.5];delta=[1.3,.2]
        for _,_,_,p,n in s.pairs("Yggdrasil","FIT")[:8]:
            for g in (p,n):
                new,anchor,soft,hard,work,zw=m.ygg_contrast(
                    g,base,delta,0.)
                original,raw,ratio,old_work=old.anchored_score(
                    g,base,delta,10)
                self.assertEqual((new,anchor,soft,work),
                                 (original,original,ratio,old_work))
                self.assertLessEqual(work["max_active"],7)
                self.assertLessEqual(work["max_retained"],9)
                self.assertTrue(0<=hard<=1)
        winner,grid=m.ygg_fit(s.pairs("Yggdrasil","FIT"),base,delta)
        self.assertEqual(len(grid),6)
        self.assertEqual(winner["paired"],max(x["paired"] for x in grid))

    def test_original_one_state_logit_and_cost_bitwise(self):
        base=[.6,.7,.9,.5,.85,.15,-.55];delta=[.05,-.03,.02,-.04]
        for _,_,_,p,n in s.pairs("Wingless","FIT")[:8]:
            for g in (p,n):
                test,raw,contrast,work=m.wing_terminal(g,base,delta,0.)
                prior,ow=old.frozen_packed(g,base,delta)
                self.assertEqual((test,raw),(prior,prior))
                self.assertEqual(work,ow)
                self.assertLessEqual(work["max_active"],64)
                self.assertEqual(work["max_states_per_node"],1)
                self.assertTrue(-1<=contrast<=1)
        win,grid=m.wing_fit(s.pairs("Wingless","FIT"),base,delta)
        self.assertEqual(len(grid),6)
        self.assertEqual(win["paired"],max(x["paired"] for x in grid))

    def test_inference_without_labels_or_oracle(self):
        for fn in (m.ygg_contrast,m.wing_terminal):
            body=inspect.getsource(fn)
            for forbidden in ('"DEV"', "routes15(", "public_reference(",
                              "positive_route(", "paired_admit(", "protected("):
                self.assertNotIn(forbidden,body)

if __name__=="__main__":
    unittest.main()
