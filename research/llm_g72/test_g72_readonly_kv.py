"""G72 source-only frozen-contract and negative-control admission tests."""
import importlib.util
import hashlib
from pathlib import Path
import unittest
SCRIPT=Path(__file__).with_name("g72_readonly_kv.py")
spec=importlib.util.spec_from_file_location("g72_readonly_kv",SCRIPT)
g72=importlib.util.module_from_spec(spec)
spec.loader.exec_module(g72)
class FrozenG72(unittest.TestCase):
    def test_pre_registered(self):
        g72.contract()
        self.assertEqual(g72.PREREG,"4a5d88c6598cd365167049a0df829db92f0d41c9")
    def test_distinct_gpu_track(self):
        self.assertEqual((g72.SELECT_OFFSET,g72.CASES,g72.REPEATS,g72.TOKENS),(36,12,3,8))
        self.assertEqual(g72.ARMS,("baseline_incremental","hf_generate","shared_prefix_deepcopy","shared_prefix_readonly"))
    def test_full_responses(self):
        self.assertEqual(len(g72.ARMS)*len(g72.COHORTS)*g72.REPEATS*g72.CASES,288)
    def test_deterministic_first_use_rows(self):
        data=[{"instruction":f"Authentic distinct authored example {i}?","category":"math_word_problem"} for i in range(65)]
        all_ranked=g72.all_ranked_heldout(data,48)
        self.assertEqual(g72.select_heldout(data),all_ranked[36:48])
        self.assertEqual(len(set(x["source_row"] for x in all_ranked)),48)
    def test_malformed_missing_input_fails_closed(self):
        data=[{"instruction":"Same", "category":"math_word_problem"} for _ in range(48)]
        with self.assertRaisesRegex(RuntimeError,"INSUFFICIENT_DISTINCT"):
            g72.select_heldout(data)
        with self.assertRaisesRegex(RuntimeError,"INSUFFICIENT_DISTINCT"):
            g72.all_ranked_heldout(data,48)
    def test_no_first_use_cache_admission(self):
        history=set()
        self.assertFalse(g72.observe_cache(history,("new",)))
        self.assertTrue(g72.observe_cache(history,("new",)))
    def test_no_false_distinct_prefix_hits(self):
        history=set()
        for i in range(12):
            self.assertFalse(g72.observe_cache(history,(i,)))
        self.assertEqual(len(history),12)
    def test_strict_frozen_limits(self):
        self.assertEqual(g72.THRESHOLDS,{"repeated_min":1.15,"unique_min":0.98,"max_sample_p95_ratio":1.20,"max_sample_rss_ratio":1.10,"min_paired_ratio":0.95})
    def test_immutable_original_identity(self):
        self.assertEqual(g72.MODEL_REV,"607a30d783dfa663caf39e06633721c8d4cfcd7e")
        self.assertEqual(g72.DATA_SHA,"3730d312f6e3440559ace48831e51066acaca737f6eabec99bccb9e4b3c39d14")
    def test_no_promotion(self):
        s=SCRIPT.read_text()
        self.assertIn('"scientific_acceptance":"NOT_GRANTED"',s)
        self.assertIn('"promotion_allowed":False',s)
        self.assertIn('G72_SHARED_KV_MUTATION_DETECTED',s)
        self.assertIn('G72_NEGATIVE_MUTATION_FIXTURE_NOT_DETECTED',s)
if __name__=="__main__":
    unittest.main()
