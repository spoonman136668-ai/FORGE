import importlib.util
import inspect
import unittest
from pathlib import Path
p=Path(__file__).with_name("g63_equal_resources.py")
s=importlib.util.spec_from_file_location("g63",p)
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class Frozen(unittest.TestCase):
    def test_pure(self):m.check_contract()
    def test_prereg(self):self.assertEqual(m.PREREG,"1ab8bf1648dff11907a9b63494ab6a17cbf19920")
    def test_model_revision(self):
        self.assertEqual(m.MODEL_REV,"607a30d783dfa663caf39e06633721c8d4cfcd7e")
        self.assertEqual(m.MODEL_SHA,"248dfc3911869ec493c76e65bf2fcf7f615828b0254c12b473182f0f81d3a707")
    def test_cpu_budgets(self):self.assertEqual(m.BUDGETS,(2,3))
    def test_controls(self):self.assertEqual(len(m.ARMS),3)
    def test_original_cohorts(self):self.assertEqual(set(m.STREAMS),{"high_locality","unique_only","thrash"})
    def test_cache_limit(self):self.assertEqual((m.ENTRY_CAP,m.KV_CAP),(2,42_000_000))
    def test_frozen_thresholds(self):
        self.assertEqual(m.THRESHOLDS,{"b3_high_over_no_cache":1.05,"b3_high_over_serial":1.05,
                                      "b2_high_over_no_cache":1.0,"b3_unique_over_no_cache":0.95})
    def test_overlap(self):
        self.assertEqual(m.overlap(1,2,2,4),0)
        self.assertEqual(m.overlap(1,3,2,4),1)
    def test_worker_accounting(self):
        source=inspect.getsource(m.main)
        self.assertIn("decoder_threads+producer_threads!=budget",source)
        self.assertIn("process.cpu_affinity(full_affinity[:cpu_budget])",source)
    def test_no_promotion(self):
        source=inspect.getsource(m.main)
        self.assertIn('"promotion_allowed":False',source)
        self.assertIn('"scientific_acceptance":"NOT_GRANTED"',source)
if __name__=="__main__":unittest.main()
