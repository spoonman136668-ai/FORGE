"""F124-Y frozen readout, original unchanged checksum and source isolation."""
import math, unittest
from collections import Counter
import f124y_frozen_models as y
import f124y_development_evidence as report
import f124w_hop_trace_indexed as w
import f124q_fresh_source as source


class F124YTests(unittest.TestCase):
    def test_authentic_frozen_parent_and_readout(self):
        freeze=y.frozen()
        self.assertEqual(w.blob(y.FREEZE),y.FREEZE_BLOB)
        self.assertEqual(freeze["lineage"]["parent_run"],39085922140)
        self.assertEqual(freeze["Wingless"]["checksum"],[1,3,4,2])
        self.assertTrue(all(value is False for value in freeze["authority"].values()))
        self.assertEqual(len(y.BIAS)*len(y.SLOPE),45)

    def test_new_fit_source_and_no_previous_data(self):
        for lane in ("Wingless","Yggdrasil"):
            self.assertTrue(set(y.COHORTS[lane]["FIT"]).isdisjoint(
                            y.COHORTS[lane]["DEV"]))
            self.assertTrue(set(y.COHORTS[lane]["FIT"]).isdisjoint(
                            y.x.COHORTS[lane]["FIT"]))
            self.assertTrue(set(y.COHORTS[lane]["DEV"]).isdisjoint(
                            y.w.COHORTS[lane]["DEV"]))
            counts=Counter()
            for _,_,p,n in y.pairs(lane,"FIT"):
                self.assertTrue(source.paired_admit(p,n))
                counts[len(p["roles"])]+=1
            self.assertEqual(counts,Counter({7:16,8:16,9:16}))
            with self.assertRaises(source.Quarantined):
                y.build(lane,1080000,(2,1,1),"FIT")

    def test_exact_selected_checksum_cached_vs_uncached(self):
        base=[.5,.7,.9,.6,1.,.14,-.5]
        delta=[.1,-.03,.03,-.02]
        for _,_,p,n in y.pairs("Wingless","FIT")[:4]:
            for graph in (p,n):
                cached,work=w.indexed_wingless(graph,base,delta,y.CHECKSUM)
                uncached,_=y.checksum_uncached(graph,base,delta)
                self.assertEqual(cached,uncached)
                self.assertTrue(math.isfinite(cached))
                self.assertEqual(work["compression_levels"],5)
                self.assertEqual(work["compression_channels"],4)
                self.assertLessEqual(work["max_active"],192)

    def test_fit_only_deterministic_selection(self):
        base=[.5,.7,.9,.6,1.,.14,-.5]
        delta=[1.1,.3]
        selection,all_choices=y.select_fit_bias(
            y.pairs("Yggdrasil","FIT"),base,delta)
        self.assertEqual(len(all_choices),45)
        self.assertEqual(selection["paired"],max(x["paired"] for x in all_choices))
        self.assertIn(selection["bias"],y.BIAS)
        self.assertIn(selection["slope"],y.SLOPE)
        import inspect
        self.assertNotIn('"DEV"',inspect.getsource(y.select_fit_bias))

    def test_only_readout_changes_and_original_control(self):
        base=[.5,.7,.9,.6,1.,.14,-.5]
        delta=[1.1,.3]
        _,_,p,_=y.pairs("Yggdrasil","FIT")[0]
        raw,work,trace=y.x.frozen_yggdrasil_score(p,base,delta,"V_centered")
        shifted=y.calibrated_logit(raw,len(p["roles"]),.5,-.5)
        self.assertEqual(shifted,raw+.5-.5*(len(p["roles"])-8))
        self.assertLessEqual(work["max_active"],7)
        self.assertLessEqual(work["max_retained"],9)
        self.assertEqual(len(trace),len(p["roles"]))
        self.assertEqual(report.WING_ARMS,(
            "selected_indexed","same_checksum_uncached","strong_fixed"))


if __name__=="__main__":
    unittest.main()
