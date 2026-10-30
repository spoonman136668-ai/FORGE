"""G71 source-only deterministic contract tests: never load pretrained weights."""
import importlib.util
from pathlib import Path
import unittest

SOURCE=Path(__file__).with_name("g71_onnx_http.py")
spec=importlib.util.spec_from_file_location("g71_onnx_http",SOURCE)
g71=importlib.util.module_from_spec(spec)
spec.loader.exec_module(g71)

class G71FrozenContract(unittest.TestCase):
    def test_frozen_invariants(self):
        g71.contract()
        self.assertEqual(g71.PREREG,"4c0242afe2eee1c23c0cf2704c2ddfb29fe4e57c")
        self.assertEqual(g71.ARMS,("baseline_incremental","hf_generate","shared_prefix","onnx_http"))
        self.assertEqual(g71.COHORTS,("unique_system","repeated_system"))
        self.assertEqual((g71.SELECT_OFFSET,g71.CASES,g71.REPEATS,g71.TOKENS),(24,12,3,8))
    def test_expected_timed_http_requests(self):
        self.assertEqual(len(g71.COHORTS)*len(g71.ARMS)*g71.REPEATS*g71.CASES,288)
    def test_heldout_ranking_does_not_use_answers(self):
        data=[{"instruction":f"Unique authored question {i}?", "category":"math_word_problem"} for i in range(55)]
        chosen=g71.select_heldout(data)
        self.assertEqual(len(chosen),12)
        self.assertEqual(len(set(x["source_row"] for x in chosen)),12)
        ranks=sorted(data,key=lambda x:g71.hashlib.sha256(g71.SEED+x["instruction"].encode("utf-8")).hexdigest())
        self.assertEqual({x["instruction"] for x in chosen},{x["instruction"] for x in ranks[24:36]})
        self.assertFalse({x["instruction"] for x in chosen} & {x["instruction"] for x in ranks[:24]})
    def test_no_duplicate_heldout(self):
        data=[{"instruction":"duplicate", "category":"math_word_problem"} for _ in range(55)]
        with self.assertRaisesRegex(RuntimeError,"INSUFFICIENT_DISTINCT"):
            g71.select_heldout(data)
    def test_prefix_admission_never_first_use(self):
        seen=set()
        self.assertFalse(g71.observe_cache(seen,(1,2,3)))
        self.assertTrue(g71.observe_cache(seen,(1,2,3)))
        other=set()
        for i in range(12):
            self.assertFalse(g71.observe_cache(other,(i,)))
    def test_p95_sample_observation(self):
        self.assertEqual(g71.p95(list(range(12))),11)
    def test_identical_source_identity(self):
        self.assertEqual(g71.WEIGHTS_SHA,"248dfc3911869ec493c76e65bf2fcf7f615828b0254c12b473182f0f81d3a707")
        self.assertEqual(g71.DATA_SHA,"3730d312f6e3440559ace48831e51066acaca737f6eabec99bccb9e4b3c39d14")
    def test_relative_optimization_gate_direction(self):
        thresholds=g71.THRESHOLDS
        self.assertGreater(thresholds["min_cohort_ratio"],1.0)
        self.assertLess(thresholds["min_paired_ratio"],1.0)
        self.assertLessEqual(thresholds["max_sampled_rss_ratio"],1.10)
        self.assertLessEqual(thresholds["max_p95_ratio"],1.20)
    def test_no_acceptance_in_implementation(self):
        source=SOURCE.read_text()
        self.assertIn('"scientific_acceptance":"NOT_GRANTED"',source)
        self.assertIn('"promotion_allowed":False',source)
        self.assertIn('ort.generate(',source)
        self.assertIn('cpu_affinity(initial_affinity[:CPU_BUDGET])',source)
if __name__=="__main__":
    unittest.main()
