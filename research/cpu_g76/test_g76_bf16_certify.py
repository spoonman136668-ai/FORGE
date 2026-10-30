"""G76 independent pre-execution source-only admission without downloading original model."""
import importlib.util
import math
from pathlib import Path
import unittest

P=Path(__file__).with_name("g76_bf16_certify.py")
s=importlib.util.spec_from_file_location("cpu_llm_g76",P)
g=importlib.util.module_from_spec(s)
s.loader.exec_module(g)

class G76FrozenTests(unittest.TestCase):
    def test_original_preregistration_frozen(self):
        g.contract()
        self.assertEqual(g.PREREG_COMMIT,"c5d854eeed8e0b7ebbc9448454dd652f72edf2e2")
        self.assertEqual((g.OFFSET,g.CASES,g.TOKENS,g.PAIRS),(72,12,8,5))
        self.assertEqual(g.CPU_BUDGET,3)
        self.assertEqual(g.SEED,b"G68-GPT2-HELDOUT-20261030:")
    def test_immutable_original_data(self):
        self.assertEqual(g.WEIGHTS_SHA,"248dfc3911869ec493c76e65bf2fcf7f615828b0254c12b473182f0f81d3a707")
        self.assertEqual(g.DATA_SHA,"3730d312f6e3440559ace48831e51066acaca737f6eabec99bccb9e4b3c39d14")
        self.assertEqual(g.DATA_BYTES,749738)
    def test_holdout_only_new_original_rows(self):
        rows=[{"instruction":"independently authored sample "+str(i),"category":"math"} for i in range(100)]
        ranked=g.rank_human(rows,84)
        self.assertEqual(len(ranked),84)
        self.assertEqual(len(set(x["source_row"] for x in ranked)),84)
        self.assertEqual(len(set(x["instruction_sha256"] for x in ranked[72:84])),12)
        self.assertTrue(set(x["source_row"] for x in ranked[72:84]).isdisjoint(
                        set(x["source_row"] for x in ranked[:72])))
    def test_fail_closed_on_duplicate_rows(self):
        rows=[{"instruction":"identical original problem","category":"math"} for _ in range(96)]
        with self.assertRaisesRegex(RuntimeError,"G76_MISSING_ORIGINAL_HUMAN_INPUTS"):
            g.rank_human(rows,84)
    def test_bf16_numeric_margin(self):
        self.assertEqual(g.NUMERICAL_MARGIN,.01)
        self.assertGreater(g.GAMMA,0)
        self.assertLess(g.GAMMA,.001)
        self.assertEqual(g.LIMITS,{"median_head_speedup":1.20,"amortized_speedup":1.10,
            "certified_fraction":0.80,"min_pair_ratio":0.80,"rss_ratio":1.15})
    def test_algorithm_has_original_reference_only_for_repair(self):
        code=P.read_text(encoding="utf-8")
        self.assertIn("return int(F.linear(h,W).argmax().item()),False,True,uncertain",code)
        self.assertIn("upper[k]=-float(\"inf\")",code)
        self.assertIn("torch.bfloat16",code)
        self.assertIn("torch.dot(h,W[k])",code)
        self.assertIn('scientific_acceptance":"NOT_GRANTED"',code)
        self.assertIn('"promotion_allowed":False',code)
        self.assertNotIn("model.train(",code)
        self.assertNotIn("cuda(",code)
        self.assertNotIn(".to('cuda')",code)
    def test_source_transparency(self):
        code=P.read_text(encoding="utf-8")
        self.assertIn("G76_REAL_GPT2_TOKEN_PARITY_FAILURE_",code)
        self.assertIn("G76_ORIGINAL_RANK_SPLIT_IDENTITY_MISMATCH",code)
        self.assertIn('"performance"]="GO" if (',code)
        self.assertIn('else "NO_GO"',code)
        self.assertIn('sample_count',code)

if __name__=="__main__":
    unittest.main()
