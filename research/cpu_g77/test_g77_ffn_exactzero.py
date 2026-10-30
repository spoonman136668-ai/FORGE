"""G77 independent source-only tests, no model download or original runner required."""
import importlib.util
from pathlib import Path
import unittest

P=Path(__file__).with_name("g77_ffn_exactzero.py")
S=importlib.util.spec_from_file_location("cpu_llm_g77",P)
g=importlib.util.module_from_spec(S);S.loader.exec_module(g)

class OriginalExactZeroAdmission(unittest.TestCase):
    def test_freeze_and_original_source(self):
        g.contract()
        self.assertEqual(g.PREREG,"da9b9dc83be89e0bb274ad36afea73faabaa8901")
        self.assertEqual(g.MODEL_REV,"607a30d783dfa663caf39e06633721c8d4cfcd7e")
        self.assertEqual(g.WEIGHTS_SHA,"248dfc3911869ec493c76e65bf2fcf7f615828b0254c12b473182f0f81d3a707")
        self.assertEqual(g.DATA_SHA,"3730d312f6e3440559ace48831e51066acaca737f6eabec99bccb9e4b3c39d14")
    def test_frozen_unique_original_ranks(self):
        rows=[{"instruction":f"Original independent public question {i}","category":"math"} for i in range(120)]
        chosen=g.rank_human(rows,96)
        self.assertEqual(len(chosen),96)
        self.assertEqual(len({q["source_row"] for q in chosen}),96)
        self.assertTrue({q["source_row"] for q in chosen[84:96]}.isdisjoint(
            {q["source_row"] for q in chosen[:84]}))
    def test_duplicate_rows_fail_closed(self):
        rows=[{"instruction":"duplicate","category":"math"}]*120
        with self.assertRaisesRegex(RuntimeError,"G77_INSUFFICIENT_AUTHENTIC_ORIGINAL_QUESTIONS"):
            g.rank_human(rows,96)
    def test_perlayer_denominators_frozen(self):
        self.assertEqual((g.LAYERS,g.CASES,g.STEPS,g.MLP_WIDTH),(12,12,8,3072))
        self.assertEqual(g.LAYERS*g.CASES*g.STEPS,1152)
        self.assertEqual(g.FREEZE,{"median_exact_zero":0.20,
                      "min_layer_exact_zero":0.05,"max_zero_free_positions":0.10})
    def test_exact_zero_not_near_zero(self):
        # A value below a diagnostic tolerance MUST NOT count as exactly zero.
        samples=[0.0,-0.0,1e-7,-1e-7,1e-3,-1e-3]
        self.assertEqual(sum(v==0.0 for v in samples),2)
        self.assertEqual(sum(abs(v)<1e-6 for v in samples),4)
    def test_original_hook_custody(self):
        src=P.read_text(encoding="utf-8")
        for value in ("mlp.act","register_forward_hook","output[0,-1,:]","G77_INVALID_ORIGINAL_GELU_ACTIVATION",
                     "G77_ORIGINAL_LAYER_HOOK_SET_INCOMPLETE","G77_INCOMPLETE_ORIGINAL_ACTIVATION_COVERAGE",
                     "G77_ORIGINAL_DISJOINT_RANK_DRIFT","zero_counts","exact_zero_fraction"):
            self.assertIn(value,src)
    def test_no_unfounded_speedup_promotion(self):
        src=P.read_text(encoding="utf-8")
        self.assertIn('"performance":"NOT_MEASURED"',src)
        self.assertIn('"scientific_acceptance":"NOT_GRANTED"',src)
        self.assertIn('"promotion_allowed":False',src)
        self.assertIn('"exact_token_correctness":"ORIGINAL_ONLY_NO_SPARSE_COMPARISON"',src)
        self.assertNotIn("model.train(",src)
        self.assertNotIn("model.cuda(",src)
    def test_exact_source_rank_disjointness(self):
        self.assertEqual((g.HELDOUT_START,g.CASES),(84,12))
        self.assertEqual(g.SEED,b"G68-GPT2-HELDOUT-20261030:")

if __name__=="__main__":unittest.main()
