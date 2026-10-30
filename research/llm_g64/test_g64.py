"""G64 no-model CPU routing and frozen contract tests."""
import importlib.util
import inspect
from pathlib import Path
import unittest
p=Path(__file__).with_name("g64_conditional.py")
s=importlib.util.spec_from_file_location("g64_conditional",p)
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class G64Frozen(unittest.TestCase):
    def test_contract(self):m.self_test()
    def test_prereg(self):self.assertEqual(m.PREREG,"05be378a4db483cb1fc6763369f807d71b93dcad")
    def test_model(self):
        self.assertEqual(m.MODEL_REV,"607a30d783dfa663caf39e06633721c8d4cfcd7e")
        self.assertEqual(m.MODEL_SHA,"248dfc3911869ec493c76e65bf2fcf7f615828b0254c12b473182f0f81d3a707")
    def test_not_future_oracular(self):
        self.assertFalse(m.wave_route([], (0,0)))
        self.assertFalse(m.wave_route((0,), (0,0)))
        self.assertTrue(m.wave_route((0,0),(0,1)))
        self.assertFalse(m.wave_route((0,0),(1,1)))
    def test_expected_high_locality(self):
        self.assertEqual(m.predicted_routes(m.STREAMS["high_locality"],2),(False,True,False))
        self.assertEqual(m.predicted_routes(m.STREAMS["high_locality"],3),(False,True))
    def test_unique_and_thrash_never_route(self):
        for cohort in ("unique_only","thrash"):
            for b in m.BUDGETS:
                self.assertFalse(any(m.predicted_routes(m.STREAMS[cohort],b)))
    def test_four_worker_budget_checks(self):
        src=inspect.getsource(m.main)
        self.assertIn("decode_threads+producer_threads!=budget",src)
        self.assertIn("process.cpu_affinity(all_allowed[:budget])",src)
    def test_actual_kv_limit(self):
        self.assertEqual((m.ENTRY_CAP,m.KV_CAP),(2,42_000_000))
    def test_pair_trials_and_arms(self):
        self.assertEqual((m.REPEATS,m.TOKENS),(2,16))
        self.assertEqual(m.ARMS,("no_cache","serialized_prefill","conditional_router"))
    def test_frozen_thresholds(self):
        self.assertEqual(m.THRESHOLDS,{"b3_high_over_no_cache":1.05,
             "b2_high_over_no_cache":0.98,"b3_unique_over_no_cache":0.98,
             "b3_thrash_over_no_cache":0.98,"b3_high_over_serial":1.0})
    def test_non_promotion(self):
        src=inspect.getsource(m.main)
        self.assertIn('"promotion_allowed":False',src)
        self.assertIn('"scientific_acceptance":"NOT_GRANTED"',src)
if __name__=="__main__":unittest.main()
