import importlib.util
import unittest
from pathlib import Path
path=Path(__file__).with_name("g61_profile.py")
spec=importlib.util.spec_from_file_location("g61_profile",path)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class FrozenContract(unittest.TestCase):
    def test_self_contract(self):m.pure_contract()
    def test_prereg(self):
        self.assertEqual(m.PREREG,"cb2974f99345025c3e08b553e1ceda376dbddbb7")
    def test_source(self):
        self.assertEqual(m.REV,"607a30d783dfa663caf39e06633721c8d4cfcd7e")
        self.assertEqual(m.WEIGHTS_SHA,"248dfc3911869ec493c76e65bf2fcf7f615828b0254c12b473182f0f81d3a707")
    def test_serial_and_concurrent(self):
        self.assertEqual(m.CONCURRENCY,(1,2))
    def test_two_pairstreams(self):
        self.assertEqual(len(m.STREAMS),2)
        self.assertEqual(set(m.STREAMS),{"high_locality","unique_only"})
    def test_cost_attribution_not_optimization(self):
        import inspect
        source=inspect.getsource(m.main)
        for term in ("prefill_coordinator_s","sum_deepcopy_s",
                     "sum_first_forward_s","sum_incremental_forward_s",
                     "median_request_latency_s","wave_overlap_s"):
            self.assertIn(term,source)
    def test_bounded_cache(self):
        self.assertEqual((m.CAP_ENTRIES,m.CAP_BYTES),(2,42_000_000))
    def test_not_scientific_promotion(self):
        import inspect
        source=inspect.getsource(m.main)
        self.assertIn('"promotion_allowed":False',source)
        self.assertIn('"scientific_acceptance":"NOT_GRANTED"',source)
if __name__=="__main__":unittest.main()
