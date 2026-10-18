"""F124-AD frozen source identity and unchanged 16-cell causal model proof."""
import json,unittest
import f124ad_source as src
import f124ad_intermediate_credit as X
import f124o_native_learners as O
import f124ac_terminal_intervention as prior

class F124ADTests(unittest.TestCase):
    def test_immutable_freeze_original_parent_and_sealed_exclusion(self):
        self.assertEqual(len(src.frozen()),64)
        p=json.loads(src.PROTOCOL.read_text())
        self.assertEqual(p["parent"]["qualified_head"],
                         "8cefd03c798e944ae9aa0510c37066640e6bd0bb")
        self.assertEqual(p["parent"]["run_id"],39107491147)
        self.assertEqual(p["original"]["cell_budget"],
                         {"active":7,"retained":9,"total":16})
        self.assertEqual(tuple(p["hypotheses"]["grid"]),X.GRID)
        self.assertTrue(all(x is False for x in p["safety"].values()))
        with self.assertRaises(src.Quarantined):src.protected()

    def test_complete_fresh_fit_dev_without_label_histogram_leak(self):
        self.assertTrue(set(src.COHORTS["YggdrasilStress"]["FIT"]).isdisjoint(
                        src.COHORTS["YggdrasilStress"]["DEV"]))
        for phase in ("FIT","DEV"):
            count={10:0,11:0,12:0}
            for vector in src.VECTORS:
                for seed in src.COHORTS["YggdrasilStress"][phase]:
                    pos,neg=src.transfer_pair(seed,vector,phase,"long_depth")
                    self.assertTrue(src.paired_admit(pos,neg))
                    count[len(pos["roles"])]+=1
            self.assertEqual(count,{10:16,11:16,12:16})

    def test_original_prediction_identical_and_oracle_after_score(self):
        w={"base":list(O.YGGDRASIL_INIT),"R":[.04,-.08],
           "S":[.02,.06],"U":[.03,-.09]}
        p,n=src.transfer_pair(2290000,[2,1,1],"FIT","long_depth")
        route=X.exact_positive_prefix(p)
        for arm in X.ARMS:
            for graph in (p,n):
                baseline=X.forward(arm,graph,w,gamma=0.,penalty=0.)
                original=prior.forward(arm,graph,w,alpha=0.,beta=0.)
                self.assertEqual(original["logit_hex"],baseline["logit_hex"])
                self.assertLessEqual(baseline["final_active"],7)
                self.assertLessEqual(baseline["final_retained"],9)
                for gamma,penalty in ((.5,0.),(0.,.5),(.5,.5)):
                    new=X.forward(arm,graph,w,gamma=gamma,penalty=penalty)
                    self.assertLessEqual(new["final_active"],7)
                    self.assertLessEqual(new["final_retained"],9)
                    self.assertLessEqual(new["final_active"]+new["final_retained"],16)
            before=X.forward(arm,p,w,gamma=.5,penalty=.5)
            after=X.forward(arm,p,w,gamma=.5,penalty=.5,
                            positive_prefix=route)
            self.assertEqual(before["logit_hex"],after["logit_hex"])

    def test_fit_parameter_family_never_retune_DEV(self):
        self.assertEqual(len(X.params("baseline")),1)
        self.assertEqual(len(X.params("exact_credit")),8)
        self.assertEqual(len(X.params("mismatch_penalty")),8)
        self.assertEqual(len(X.params("combined")),64)
        self.assertEqual(X.params("baseline"),((0.,0.),))
        self.assertEqual(X.FAMILIES,("baseline","exact_credit",
                                  "mismatch_penalty","combined"))

if __name__=="__main__":unittest.main()
