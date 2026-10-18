"""F124-AH source-rule inversion and untouched original-inference tests."""
import inspect,unittest
from collections import Counter
import f124ah_frozen_source as s
import f124ah_original_model_challenge as model

class FrozenAH(unittest.TestCase):
    def test_frozen_original_parent_and_new_sources(self):
        p=s.frozen()
        self.assertEqual(s.witness.blob(s.FREEZE),s.FREEZE_BLOB)
        self.assertEqual(p["lineage"]["parent_run"],39109432945)
        self.assertEqual(p["Yggdrasil"]["test"][:6],"FROZEN")
        self.assertTrue(all(x is False for x in p["authority"].values()))
        for lane in ("Wingless","Yggdrasil"):
            self.assertTrue(set(s.COHORTS[lane]["FIT"]).isdisjoint(
                            s.COHORTS[lane]["DEV"]))
            for phase in ("FIT","DEV"):
                cases=s.pairs(lane,phase)
                self.assertEqual(len(cases),48)
                self.assertEqual(Counter(c[2] for c in cases),
                                 Counter({f:12 for f in s.FAMILIES}))
                for _,_,f,pos,neg in cases:
                    self.assertEqual(s.routes(pos,f),1)
                    self.assertEqual(s.routes(neg,f),0)
                    self.assertEqual(s.parent.prior.parent.routes15(
                        pos,relaxed=True),0)
                    self.assertEqual(s.parent.prior.parent.routes15(
                        neg,relaxed=True),0)
                    self.assertEqual(len(pos["roles"]),len(neg["roles"]))
                    self.assertEqual(s.restore(pos,f)["roles"],
                                     s.restore(neg,f)["roles"])

    def test_ygg_original_hard_budget_with_non_identity_rules(self):
        base=[.4,.9,.65,.75,.8,.2,-.5]
        delta=[1.3,.2]
        for _,_,fam,p,n in s.pairs("Yggdrasil","FIT")[:8]:
            for g in (p,n):
                for arm in ("AG_eta_0_1","AG_eta_0","AD_anchor10",
                            "AB_anchor16","T_original"):
                    score,work=model.ygg(g,base,delta,arm)
                    self.assertTrue(isinstance(score,float))
                    self.assertLessEqual(work["max_active"],7)
                    self.assertLessEqual(work["max_retained"],9)

    def test_wing_exact_original_one_state_and_posthoc_reference(self):
        base=[.6,.7,.9,.5,.85,.15,-.55]
        delta=[.05,-.03,.02,-.04]
        for _,_,fam,p,n in s.pairs("Wingless","FIT")[:8]:
            for g in (p,n):
                score,work=model.wing(g,base,delta,"AA_original_one")
                observer,record,trace=model.wing_source_blind_trace(
                    g,base,delta)
                self.assertEqual((score,work),(observer,record))
                self.assertEqual(len(trace),len(g["roles"]))
                self.assertEqual(record["max_states_per_node"],1)
            post=model.report_wing_positive(p,fam,trace)
            self.assertTrue(post["no_raw_key_path_survival_claim"])
            self.assertEqual(len(post["per_hop_proxy"]),len(p["roles"]))

    def test_no_truth_leak_to_predictors(self):
        for fn in (model.ygg,model.wing,model.wing_source_blind_trace):
            code=inspect.getsource(fn)
            for forbidden in ("posthoc_public_path(","routes(", "paired_admit(",
                              '"DEV"', "positive_route(", "public_reference("):
                self.assertNotIn(forbidden,code)
if __name__=="__main__":
    unittest.main()
