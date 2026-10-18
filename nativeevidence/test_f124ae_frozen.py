"""F124-AE source and unchanged model parity across old/extended domains."""
import math,unittest,inspect
from collections import Counter
import f124ae_frozen_source as s
import f124ae_scoring_transfer as m
import f124aa_packed_transfer as aa
import f124ab_soft_hamming_pareto as ab

class F124AEFrozen(unittest.TestCase):
    def test_preimplementation_freeze_and_11_ancestor_identity(self):
        plan=s.frozen()
        self.assertEqual(s.guard.blob(s.FREEZE),s.FREEZE_BLOB)
        self.assertEqual(plan["lineage"]["engineering_pass_run"],39093408320)
        self.assertEqual(plan["Yggdrasil"]["frozen_anchor"],10)
        self.assertEqual(plan["Wingless"]["bias_grid"],list(s.BIAS))
        self.assertTrue(all(v is False for v in plan["authority"].values()))

    def test_new_exact_admission_and_four_families(self):
        for lane in ("Wingless","Yggdrasil"):
            self.assertTrue(set(s.COHORTS[lane]["FIT"]).isdisjoint(
                            s.COHORTS[lane]["DEV"]))
            for phase in ("FIT","DEV"):
                cases=s.pairs(lane,phase)
                self.assertEqual(len(cases),48)
                self.assertEqual(Counter(c[2] for c in cases),
                                 Counter({fam:12 for fam in s.FAMILIES}))
                for _,_,family,p,n in cases:
                    self.assertEqual(s.routes15(p,relaxed=
                                     family=="one_bit_relaxed_keys"),1)
                    self.assertEqual(s.routes15(n,relaxed=
                                     family=="one_bit_relaxed_keys"),0)
                    self.assertEqual(len(p["roles"]),len(n["roles"]))
                for family in ("extended_13_15","long_dense_13_15"):
                    depths=Counter(len(p["roles"]) for _,_,fam,p,n in cases
                                   if fam==family)
                    self.assertEqual(depths,Counter({13:4,14:4,15:4}))

    def test_original_inference_unchanged_at_7_to_9(self):
        base=[.4,.9,.65,.75,.8,.2,-.5]
        delta=[1.3,.2]
        for _,_,fam,p,n in s.pairs("Yggdrasil","FIT"):
            if len(p["roles"])>9:continue
            for g in (p,n):
                original,ratio,work=ab.soft_continuity(g,base,delta,.25)
                scoped,rr,ww=m.frozen_ab_soft(g,base,delta)
                self.assertEqual((original,ratio,work),(scoped,rr,ww))
                raw,raw_work=aa.ygg_original(g,base,delta)
                same,sw=m.frozen_t(g,base,delta)
                self.assertEqual((raw,raw_work),(same,sw))
        for _,_,fam,p,n in s.pairs("Wingless","FIT"):
            if len(p["roles"])>9:continue
            for g in (p,n):
                original,work=aa.packed_one_state(g,
                       [.6,.7,.9,.5,.85,.15,-.55],[.05,-.03,.02,-.04])
                scoped,ww=m.frozen_packed(g,
                       [.6,.7,.9,.5,.85,.15,-.55],[.05,-.03,.02,-.04])
                self.assertEqual((original,work),(scoped,ww))

    def test_new_long_domain_has_no_state_growth_or_nan(self):
        base=[.4,.9,.65,.75,.8,.2,-.5]
        delta=[1.3,.2]
        for _,_,fam,p,n in s.pairs("Yggdrasil","FIT"):
            if len(p["roles"])<=12:continue
            for g in (p,n):
                score,raw,ratio,work=m.anchored_score(g,base,delta,10)
                self.assertTrue(math.isfinite(score))
                self.assertLessEqual(work["max_active"],7)
                self.assertLessEqual(work["max_retained"],9)
        base=[.6,.7,.9,.5,.85,.15,-.55]
        delta=[.05,-.03,.02,-.04]
        for _,_,fam,p,n in s.pairs("Wingless","FIT"):
            if len(p["roles"])<=12:continue
            for g in (p,n):
                score,raw,work=m.wing_threshold(g,base,delta,0)
                self.assertEqual(score,raw)
                self.assertLessEqual(work["max_active"],64)
                self.assertEqual(work["max_states_per_node"],1)

    def test_fit_only_and_no_model_oracle(self):
        winner,grid=m.fit_threshold(
            s.pairs("Wingless","FIT"),
            [.6,.7,.9,.5,.85,.15,-.55],[.05,-.03,.02,-.04])
        self.assertEqual(len(grid),7)
        self.assertEqual(winner["paired"],max(x["paired"] for x in grid))
        self.assertIn(winner["bias"],s.BIAS)
        for fn in (m.frozen_ab_soft,m.frozen_packed,m.anchored_score,
                   m.wing_threshold):
            code=inspect.getsource(fn)
            for bad in ("routes15(","positive_route(","witness(",
                        '"DEV"',"protected(","paired_admit("):
                self.assertNotIn(bad,code)

if __name__=="__main__":
    unittest.main()
