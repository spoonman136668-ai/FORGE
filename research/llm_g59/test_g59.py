"""Fast pure-policy tests: no model, network, GPU, controller or runtime."""
import importlib.util
from pathlib import Path
import unittest

p=Path(__file__).with_name("g59_adaptive.py")
spec=importlib.util.spec_from_file_location("g59_adaptive",p)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class PolicyTests(unittest.TestCase):
    def test_frozen_identities(self):
        self.assertEqual(m.MODEL_SHA,"248dfc3911869ec493c76e65bf2fcf7f615828b0254c12b473182f0f81d3a707")
        self.assertEqual(m.PREREG_COMMIT,"a5280ca7a77ca6e3a2d819d08a05e7a67cba7eb7")
        self.assertEqual(m.TRIALS,3)
        self.assertEqual(m.OUTPUT_TOKENS,16)
    def test_all_streams_bounded(self):
        for p,b in m.STREAMS.values():
            self.assertEqual(len(p),8)
            self.assertEqual(len(b),8)
            self.assertLessEqual(max(b),2)
    def test_no_cache_never_retains(self):
        for p,b in m.STREAMS.values():
            r=m.dry_run(p,b,"no_cache")
            self.assertEqual((r.count["hits"],r.count["admissions"]),(0,0))
            self.assertEqual(len(r.cache),0)
    def test_unique_prefix_adaptive_is_empty(self):
        p,b=m.STREAMS["unique_only"]
        for policy in ("second_seen","adaptive"):
            r=m.dry_run(p,b,policy)
            self.assertEqual((r.count["hits"],r.count["admissions"],r.count["evictions"]),(0,0,0))
    def test_high_locality_adaptive_streaks(self):
        p,b=m.STREAMS["high_locality"]
        r=m.dry_run(p,b,"adaptive")
        self.assertEqual([v["action"] for v in r.trace],
                         ["skip","admit","hit","hit","skip","admit","hit","hit"])
    def test_thrash_does_not_cache_sparse_second_visits(self):
        p,b=m.STREAMS["thrash_four"]
        r=m.dry_run(p,b,"adaptive")
        self.assertEqual([v["action"] for v in r.trace],
                         ["skip","skip","skip","skip","skip","skip","skip","admit"])
    def test_alternating_learns_from_third_sighting(self):
        p,b=m.STREAMS["alternating"]
        r=m.dry_run(p,b,"adaptive")
        self.assertEqual([v["action"] for v in r.trace],
                         ["skip","skip","skip","skip","admit","admit","hit","hit"])
    def test_zero_budget_evicts_causally(self):
        p,b=m.STREAMS["pressure_shift"]
        r=m.dry_run(p,b,"adaptive")
        self.assertEqual([v["retained_entries"] for v in r.trace[4:6]],[0,0])
        self.assertTrue(all(v["retained_entries"]<=v["budget"] for v in r.trace))
    def test_future_does_not_change_prefix_decision(self):
        a=m.dry_run((0,1,0,1,0),(2,)*5,"adaptive")
        b=m.dry_run((0,1,0,1,0,7,7),(2,)*7,"adaptive")
        self.assertEqual(a.trace,b.trace[:5])
    def test_invalid_pressure_rejected(self):
        with self.assertRaises(ValueError):
            m.dry_run((0,),(3,),"adaptive")
    def test_unknown_policy_rejected(self):
        with self.assertRaises(ValueError):
            m.dry_run((0,),(1,),"production_write")
    def test_frozen_decision_bounds(self):
        self.assertEqual(m.THRESHOLDS,{"high_locality":1.15,"unique_only":0.98,"thrash_four":0.97})

if __name__=="__main__":
    unittest.main()
