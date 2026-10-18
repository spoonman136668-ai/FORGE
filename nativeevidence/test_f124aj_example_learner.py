"""F124-AJ source and genuine example-only rule induction; no holdout test use."""
import inspect,unittest
from collections import Counter
import f124aj_frozen_source as source
import f124aj_example_operator_learner as learner

class FrozenAJ(unittest.TestCase):
    def test_first_freeze_and_train_holdout_independence(self):
        p=source.frozen()
        self.assertEqual(source.witness.blob(source.FREEZE),source.FREEZE_BLOB)
        self.assertEqual(p["lineage"]["qualified_run"],39111523196)
        self.assertEqual(p["Yggdrasil"]["train_hyperparameter_grid_demo_count"],
                         list(learner.COUNTS))
        self.assertTrue(all(v is False for v in p["authority"].values()))
        self.assertTrue(set(source.OPERATOR_NAMES["TRAIN"]).isdisjoint(
                        source.OPERATOR_NAMES["HOLDOUT"]))
        for lane in ("Wingless","Yggdrasil"):
            self.assertTrue(set(source.COHORTS[lane]["TRAIN"]).isdisjoint(
                            source.COHORTS[lane]["HOLDOUT"]))
            cases=source.pairs(lane,"TRAIN")
            self.assertEqual(len(cases),48)
            self.assertEqual(Counter(c[2] for c in cases),
                             Counter({f:12 for f in source.FAMILIES}))
            for seed,vector,family,operator,nonce,pos,neg in cases:
                self.assertEqual(pos["demos"],neg["demos"])
                self.assertEqual(len(pos["demos"]),24)
                self.assertEqual(source.original.parent.prior.parent.routes15(
                   source.plain_for_oracle(pos,operator,nonce),
                   relaxed=family=="rotate4_tolerant"),1)

    def test_actual_train_example_mapping_not_hardcoded(self):
        for lane in ("Wingless","Yggdrasil"):
            for seed,vector,family,operator,nonce,pos,neg in (
                    source.pairs(lane,"TRAIN")[:8]):
                decoded,obs=learner.normalize(pos,24)
                self.assertTrue(obs["learning"]["unique_bijective_mapping"])
                actual=source.plain_for_oracle(pos,operator,nonce)
                self.assertEqual(decoded,actual)
                self.assertEqual(obs["learning"]["semantic_operator_names_consumed"],
                                 False)

    def test_ygg_and_wing_original_hard_budgets(self):
        for seed,vector,family,operator,nonce,p,n in (
                source.pairs("Yggdrasil","TRAIN")[:8]):
            for g in (p,n):
                score,work,obs=learner.ygg(
                    g,[.4,.9,.65,.75,.8,.2,-.5],[1.3,.2],24)
                self.assertLessEqual(work["max_active"],7)
                self.assertLessEqual(work["max_retained"],9)
        for seed,vector,family,operator,nonce,p,n in (
                source.pairs("Wingless","TRAIN")[:8]):
            for g in (p,n):
                score,work,obs=learner.wing(
                    g,[.6,.7,.9,.5,.85,.15,-.55],[.05,-.03,.02,-.04],24)
                self.assertEqual(work["max_states_per_node"],1)
                self.assertEqual(work["max_packed_bits_per_state"],12)
                self.assertLessEqual(work["max_active"],64)

    def test_fit_only_grid_and_no_oracle_import(self):
        p=source.pairs("Yggdrasil","TRAIN")
        selection,grid=learner.fit_demo_count(
            p,[.4,.9,.65,.75,.8,.2,-.5],[1.3,.2])
        self.assertEqual(len(grid),4)
        self.assertEqual(selection["paired"],max(r["paired"] for r in grid))
        self.assertEqual(selection["demos"],
                         min(x["demos"] for x in grid
                             if x["paired"]==selection["paired"]))
        body=inspect.getsource(learner)
        for bad in ("import f124aj_frozen_source",
                    "truth_mapping(","plain_for_oracle(",
                    "source.oracle(","restore_public(", '"HOLDOUT"'):
            self.assertNotIn(bad,body)

if __name__=="__main__":unittest.main()
