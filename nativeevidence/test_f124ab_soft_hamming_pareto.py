"""F124-AB original-model preservation, four-family source and FIT-only control."""
import math, unittest
from collections import Counter
import f124ab_frozen_source as s
import f124ab_soft_hamming_pareto as a
import f124aa_packed_transfer as old
import f124z_sparse_continuity as z


class FrozenAB(unittest.TestCase):
    def test_preimplementation_and_source_identity(self):
        p=s.frozen()
        self.assertEqual(s.guard.blob(s.FREEZE),s.FREEZE_BLOB)
        self.assertEqual(p["lineage"]["parent_run"],39088963241)
        self.assertEqual(p["Yggdrasil"]["gamma_grid"],list(a.GAMMAS))
        self.assertEqual(p["Wingless"]["capacities"],list(a.CAPACITIES))
        self.assertTrue(all(x is False for x in p["authority"].values()))

    def test_new_four_families_and_original_disjoint(self):
        for lane in ("Wingless","Yggdrasil"):
            self.assertTrue(set(s.COHORTS[lane]["FIT"]).isdisjoint(
                            s.COHORTS[lane]["DEV"]))
            self.assertTrue(set(s.COHORTS[lane]["FIT"]).isdisjoint(
                            s.parent.COHORTS[lane]["FIT"]))
            cases=s.pairs(lane,"FIT")
            self.assertEqual(len(cases),48)
            self.assertEqual(Counter(x[2] for x in cases),
                             Counter({family:12 for family in s.FAMILIES}))
            for _,_,family,pos,neg in cases:
                self.assertEqual(s.parent.routes(pos,relaxed=family==
                                      "one_bit_relaxed_keys"),1)
                self.assertEqual(s.parent.routes(neg,relaxed=family==
                                      "one_bit_relaxed_keys"),0)

    def test_existing_rank_and_frozen_Z_exact_hamming(self):
        base=[.4,.9,.65,.75,.8,.2,-.5]
        delta=[1.3,.2]
        for _,_,family,pos,neg in s.pairs("Yggdrasil","FIT")[:8]:
            for graph in (pos,neg):
                raw,ratio,work=a.soft_continuity(graph,base,delta,1.)
                original,oldwork=old.ygg_original(graph,base,delta)
                self.assertEqual(raw,original)
                self.assertTrue(all(work[k]==oldwork[k] for k in oldwork))
                zscore,zratio,zraw,zwork=old.ygg_continuity(graph,base,delta)
                self.assertEqual(raw,zraw)
                self.assertEqual(ratio,zratio)
                self.assertEqual(a.logit(raw,ratio,.5),zscore)
                self.assertLessEqual(work["max_active"],7)
                self.assertLessEqual(work["max_retained"],9)

    def test_new_FIT_learning_only_two_allowed_families(self):
        base=[.4,.9,.65,.75,.8,.2,-.5]
        delta=[1.3,.2]
        selected,grid=a.learn_fit(s.pairs("Yggdrasil","FIT"),base,delta)
        self.assertEqual(len(grid),25)
        self.assertEqual(selected["paired"],max(x["paired"] for x in grid))
        self.assertIn(selected["gamma"],a.GAMMAS)
        self.assertIn(selected["penalty"],a.PENALTIES)
        import inspect
        body=inspect.getsource(a.learn_fit)
        self.assertNotIn('"DEV"',body)
        self.assertNotIn("routes(",inspect.getsource(a.soft_continuity))

    def test_packed_capacity_one_matches_AA_and_three_matches_Z(self):
        base=[.6,.7,.9,.5,.85,.15,-.55]
        delta=[.05,-.03,.02,-.04]
        for _,_,_,pos,neg in s.pairs("Wingless","FIT")[:8]:
            for graph in (pos,neg):
                first,w1=a.packed_frontier(graph,base,delta,1)
                existing,wold=old.packed_one_state(graph,base,delta)
                self.assertEqual(first,existing)
                self.assertLessEqual(w1["max_active"],64)
                second,w2=a.packed_frontier(graph,base,delta,2)
                self.assertTrue(math.isfinite(second))
                self.assertLessEqual(w2["max_active"],128)
                third,w3=a.packed_frontier(graph,base,delta,3)
                self.assertTrue(math.isfinite(third))
                self.assertLessEqual(w3["max_active"],192)
                self.assertEqual(w3["max_packed_bits_per_state"],12)


if __name__=="__main__":
    unittest.main()
