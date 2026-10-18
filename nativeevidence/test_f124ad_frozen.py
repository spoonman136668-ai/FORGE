"""F124-AD cross-platform focused test: source freeze, original parity, hard capacity."""
import unittest,inspect,math
from collections import Counter
import f124ad_frozen_source as f
import f124ad_depth_fingerprint as m
import f124aa_packed_transfer as aa
import f124ab_soft_hamming_pareto as ab

class FrozenAD(unittest.TestCase):
    def test_freeze_parent_and_source_no_contamination(self):
        p=f.frozen()
        self.assertEqual(p["lineage"]["parent_run"],39091857260)
        self.assertEqual(f.witness.blob(f.FREEZE),f.FREEZE_BLOB)
        self.assertEqual(p["Yggdrasil"]["anchor_grid"],list(f.ANCHORS))
        self.assertEqual(p["Wingless"]["alpha_grid"],list(f.ALPHAS))
        self.assertTrue(all(x is False for x in p["authority"].values()))
        for lane in ("Wingless","Yggdrasil"):
            self.assertTrue(set(f.COHORTS[lane]["FIT"]).isdisjoint(
                            f.COHORTS[lane]["DEV"]))
            self.assertTrue(set(f.COHORTS[lane]["FIT"]).isdisjoint(
                            f.previous.COHORTS[lane]["FIT"]))
            self.assertEqual(Counter(x[2] for x in f.pairs(lane,"FIT")),
                             Counter({family:12 for family in f.FAMILIES}))

    def test_original_ygg_hard_7_plus_9_and_anchor16_exact(self):
        base=[.4,.9,.65,.75,.8,.2,-.5]
        delta=[1.3,.2]
        for _,_,_,p,n in f.pairs("Yggdrasil","FIT")[:8]:
            for g in (p,n):
                old,ratio,work=ab.soft_continuity(g,base,delta,.25)
                logit,raw,rr,newwork=m.anchored_readout(g,base,delta,16)
                self.assertEqual(raw,old)
                self.assertEqual(ratio,rr)
                self.assertEqual(logit,ab.logit(old,ratio,.25))
                self.assertEqual(work,newwork)
                self.assertLessEqual(work["max_active"],7)
                self.assertLessEqual(work["max_retained"],9)
                for anchor in f.ANCHORS:
                    self.assertTrue(math.isfinite(m.anchored_readout(
                        g,base,delta,anchor)[0]))
        winner,grid=m.readout_fit(f.pairs("Yggdrasil","FIT"),base,delta)
        self.assertEqual(len(grid),5)
        self.assertEqual(winner["paired"],max(x["paired"] for x in grid))

    def test_wing_alpha_zero_exact_and_one_state_payload(self):
        base=[.6,.7,.9,.5,.85,.15,-.55]
        delta=[.05,-.03,.02,-.04]
        for _,_,_,p,n in f.pairs("Wingless","FIT")[:8]:
            for g in (p,n):
                original,work=aa.packed_one_state(g,base,delta)
                zero,ww=m.packed_with_fingerprint(g,base,delta,0.)
                self.assertEqual(original,zero)
                self.assertTrue(all(work[k]==ww[k] for k in work))
                self.assertEqual(ww["max_fingerprint_bits_per_state"],4)
                self.assertEqual(ww["max_total_key_bits_per_state"],16)
                self.assertLessEqual(ww["max_active"],64)
                for alpha in f.ALPHAS:
                    scored,work2=m.packed_with_fingerprint(g,base,delta,alpha)
                    self.assertTrue(math.isfinite(scored))
                    self.assertEqual(work2["max_states_per_node"],1)
        winner,grid=m.fingerprint_fit(f.pairs("Wingless","FIT"),base,delta)
        self.assertEqual(len(grid),4)
        self.assertEqual(winner["paired"],max(x["paired"] for x in grid))

    def test_public_predictors_no_oracle(self):
        for fn in (m.anchored_readout,m.packed_with_fingerprint):
            body=inspect.getsource(fn)
            for bad in ("public_reference(","routes(","paired_admit(",
                        "protected(","case_label","DEV"):
                self.assertNotIn(bad,body)
        self.assertEqual(m.four_bit_fingerprint([0]*16),0)
        self.assertEqual(m.four_bit_fingerprint([1]+[0]*15),1)

if __name__=="__main__":
    unittest.main()
