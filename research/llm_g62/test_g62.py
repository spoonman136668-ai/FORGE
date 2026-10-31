"""Source-only frozen G62 tests; network/model execution is qualified separately."""
import importlib.util
from pathlib import Path
import unittest
p=Path(__file__).with_name("g62_singleflight.py")
s=importlib.util.spec_from_file_location("g62_singleflight",p)
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class FrozenG62(unittest.TestCase):
    def test_contract(self):m.self_test()
    def test_prereg(self):self.assertEqual(m.PREREG,"d4103586279946381b91d6636100c508591adb1b")
    def test_authentic_weights(self):
        self.assertEqual(m.REV,"607a30d783dfa663caf39e06633721c8d4cfcd7e")
        self.assertEqual(m.WEIGHTS_SHA,"248dfc3911869ec493c76e65bf2fcf7f615828b0254c12b473182f0f81d3a707")
    def test_controls(self):
        self.assertEqual(m.ARMS,("no_cache","serialized_prefill","overlapped_singleflight"))
        self.assertEqual(len(m.STREAMS),3)
    def test_frozen_negatives(self):
        self.assertEqual(m.STREAMS["unique_only"],(0,1,2,3,4,5))
        self.assertEqual(m.STREAMS["thrash"],(0,1,2,0,1,2))
    def test_overlap_math(self):
        self.assertEqual(m.intervals_overlap(1,2,2,3),0)
        self.assertAlmostEqual(m.intervals_overlap(1,3,2,4),1)
    def test_strict_memory(self):
        self.assertEqual((m.CAP_ENTRIES,m.CAP_BYTES),(2,42000000))
    def test_candidate_has_extra_worker(self):
        self.assertEqual((m.DECODE_WORKERS,m.PREFILL_WORKERS),(2,1))
    def test_frozen_thresholds(self):
        self.assertEqual(m.THRESHOLDS,{"overlap_over_serial":1.05,"overlap_over_no_cache":1.0,"unique_over_no_cache":0.95})
    def test_no_promotion(self):
        import inspect
        source=inspect.getsource(m.main)
        self.assertIn('"promotion_allowed":False',source)
        self.assertIn('"scientific_acceptance":"NOT_GRANTED"',source)
if __name__=="__main__":unittest.main()
