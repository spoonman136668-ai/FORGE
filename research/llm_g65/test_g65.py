"""Pure controls. Trained-model execution is isolated to authenticated hosted run."""
import importlib.util
import inspect
from pathlib import Path
import threading
import unittest
p=Path(__file__).with_name("g65_shared_pool.py")
spec=importlib.util.spec_from_file_location("g65_source",p)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Frozen(unittest.TestCase):
    def test_contract(self):m.test_contract()
    def test_prereg(self):self.assertEqual(m.PREREG_SHA,"c5c9ad2b8f08b561bd7d077366707554b9e436a1")
    def test_model_weights(self):
        self.assertEqual(m.REV,"607a30d783dfa663caf39e06633721c8d4cfcd7e")
        self.assertEqual(m.WEIGHTS_SHA,"248dfc3911869ec493c76e65bf2fcf7f615828b0254c12b473182f0f81d3a707")
    def test_negative_no_route(self):
        for name in ("unique_only","thrash"):
            for b in m.BUDGETS:
                self.assertEqual(m.expected_routes(m.STREAMS[name],b),m.EXPECTED[name][b])
                self.assertFalse(any(m.EXPECTED[name][b]))
    def test_positive_causes(self):
        self.assertEqual(m.expected_routes(m.STREAMS["high_locality"],2),(False,True,False))
        self.assertEqual(m.expected_routes(m.STREAMS["high_locality"],3),(False,True))
        self.assertFalse(m.route_at_wave((0,),(0,)))
        self.assertTrue(m.route_at_wave((0,0),(0,)))
    def test_frozen_cpu_budgets(self):self.assertEqual(m.BUDGETS,(2,3))
    def test_frozen_resource_caps(self):self.assertEqual((m.ENTRY_CAP,m.KV_BYTES_CAP),(2,42_000_000))
    def test_worker_math(self):
        s=inspect.getsource(m.main)
        self.assertIn("decoder_workers+producer_workers!=budget",s)
        self.assertIn("proc.cpu_affinity(allowed[:budget])",s)
        self.assertIn("tracker.maximum>budget",s)
    def test_producer_before_dependent_decode(self):
        s=inspect.getsource(m.main)
        self.assertIn("decode_pool.submit(prefill,family,req,tracker)",s)
        self.assertIn("decode_pool.submit(decode,first,future,plen,family,req,arrived,tracker)",s)
    def test_tracker(self):
        t=m.TaskTracker()
        a=t.start("decoder",0)
        b=t.start("prefill",1)
        t.end("decoder",0,a);t.end("prefill",1,b)
        self.assertEqual((t.running,t.maximum,len(t.events)),(0,2,2))
    def test_pair_matrix(self):
        self.assertEqual(m.REPEATS,2)
        self.assertEqual(m.TOKENS,16)
        self.assertEqual(len(m.ARMS),4)
    def test_frozen_thresholds(self):
        self.assertEqual(m.THRESHOLDS,{"high_b3_vs_no_cache":1.05,
            "high_b3_vs_fixed_reserved":1.05,"high_b2_vs_no_cache":0.98,
            "unique_b3_vs_no_cache":0.98,"thrash_b3_vs_no_cache":0.98})
    def test_no_auto_promotion(self):
        s=inspect.getsource(m.main)
        self.assertIn('"scientific_acceptance":"NOT_GRANTED"',s)
        self.assertIn('"promotion_allowed":False',s)
    def test_true_overlap_intervals(self):
        self.assertAlmostEqual(m.overlap(1,3,2,4),1.)
        self.assertEqual(m.overlap(1,2,3,4),0.)
if __name__=="__main__":
    unittest.main()
