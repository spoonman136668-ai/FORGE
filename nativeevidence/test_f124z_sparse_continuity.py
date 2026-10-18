"""F124-Z frozen new FIT source, equal predictions, original cells and policy."""
import math,unittest
from collections import Counter

import f124z_sparse_continuity as z
import f124y_frozen_models as old
import f124q_independent_binding as q
import f124w_hop_trace_indexed as wing
import f124q_fresh_source as source


class F124ZFrozenTests(unittest.TestCase):
    def test_preregistration_before_implementation(self):
        p=z.frozen()
        self.assertEqual(wing.blob(z.FREEZE),z.FREEZE_BLOB)
        self.assertEqual(p["lineage"]["parent_actions_run"],39086773832)
        self.assertEqual(z.CHECKSUM,(1,3,4,2))
        self.assertEqual(z.PENALTIES,(0.,.5,1.,2.,4.,8.))
        self.assertTrue(all(v is False for v in p["authority"].values()))

    def test_public_fresh_fit_coverage_and_identity(self):
        for lane in ("Wingless","Yggdrasil"):
            for phase in ("FIT","DEV"):
                self.assertEqual(len(z.COHORTS[lane][phase]),24)
                self.assertTrue(set(z.COHORTS[lane][phase]).isdisjoint(
                    old.COHORTS[lane][phase]))
            counts=Counter()
            cases=z.pairs(lane,"FIT")
            self.assertEqual(len(cases),48)
            for _,_,p,n in cases:
                self.assertTrue(source.paired_admit(p,n))
                counts[len(p["roles"])]+=1
            self.assertEqual(counts,Counter({7:16,8:16,9:16}))
            with self.assertRaises(source.Quarantined):
                z.build(lane,1180000,(2,1,1),"FIT")

    def test_streaming_sparse_checksum_bitwise_same_as_original(self):
        base=[.6,.7,.9,.5,.85,.15,-.55]
        delta=[.05,-.03,.02,-.04]
        for _,_,p,n in z.pairs("Wingless","FIT")[:5]:
            for g in (p,n):
                score,work=z.sparse_wingless(g,base,delta)
                uncached,_=old.checksum_uncached(g,base,delta)
                indexed,_=wing.indexed_wingless(g,base,delta,z.CHECKSUM)
                self.assertEqual(score,indexed)
                self.assertEqual(score,uncached)
                self.assertEqual(work["max_encoded_cache_entries"],0)
                self.assertEqual(work["max_future_cache_entries"],0)
                self.assertLessEqual(work["max_active"],192)

    def test_ygg_same_original_logit_and_original_work_counts(self):
        base=[.4,.9,.65,.75,.8,.2,-.5]
        delta=[1.3,.2]
        for _,_,p,n in z.pairs("Yggdrasil","FIT")[:4]:
            for graph in (p,n):
                original,old_work=q.forward("Yggdrasil",graph,base,delta)
                same,feature,new_work=z.continuity_head(graph,base,delta)
                self.assertEqual(same,original)
                self.assertTrue(all(new_work[k]==old_work[k] for k in old_work))
                self.assertGreaterEqual(feature,0)
                self.assertLessEqual(feature,1)
                self.assertLessEqual(new_work["continuity_counter_slots_max"],16)
                self.assertEqual(z.corrected_logit(same,feature,0.),same)

    def test_fit_penalty_no_dev(self):
        base=[.4,.9,.65,.75,.8,.2,-.5]
        delta=[1.3,.2]
        selected,grid=z.choose_fit_penalty(z.pairs("Yggdrasil","FIT"),base,delta)
        self.assertEqual(len(grid),6)
        self.assertEqual(selected["paired"],max(row["paired"] for row in grid))
        import inspect
        code=inspect.getsource(z.continuity_head)+inspect.getsource(z.choose_fit_penalty)
        for prohibited in ("public_routes(","protected(","oracle_label","correct_path"):
            self.assertNotIn(prohibited,code)


if __name__=="__main__":
    unittest.main()
