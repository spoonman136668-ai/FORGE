"""G73 CPU GPT-2 prereg/source-only exact vocabulary-safety admission."""
import importlib.util
import math
from pathlib import Path
import unittest

P=Path(__file__).with_name("g73_certified_vocab.py")
S=importlib.util.spec_from_file_location("g73_certified_vocab",P)
G=importlib.util.module_from_spec(S)
S.loader.exec_module(G)

class G73FrozenAdmission(unittest.TestCase):
    def test_contract(self):
        G.contract()
        self.assertEqual(G.PREREG_COMMIT,"2ce3ed5a979aeffb2c56e01ad9cfd11b0d1f1063")
        self.assertEqual((G.HELDOUT_START,G.CASES,G.TOKENS,G.PAIRS),(48,12,8,5))
        self.assertEqual(G.SEED,b"G68-GPT2-HELDOUT-20261030:")
    def test_preregistered_model_and_data_sha(self):
        self.assertEqual(G.WEIGHTS_SHA,"248dfc3911869ec493c76e65bf2fcf7f615828b0254c12b473182f0f81d3a707")
        self.assertEqual(G.DATA_SHA,"3730d312f6e3440559ace48831e51066acaca737f6eabec99bccb9e4b3c39d14")
    def test_ranked_first_use_disjoint(self):
        data=[{"instruction":"independently authored item "+str(i),"category":"human"} for i in range(80)]
        ranks=G.ranked_human(data,60)
        self.assertEqual(len(ranks),60)
        self.assertEqual(len(set(z["source_row"] for z in ranks)),60)
        self.assertEqual(len(set(z["instruction_sha256"] for z in ranks[48:60])),12)
    def test_insufficient_unique_fails_closed(self):
        data=[{"instruction":"duplicate","category":"math"} for _ in range(80)]
        with self.assertRaisesRegex(RuntimeError,"G73_INSUFFICIENT_ORIGINAL_HUMAN_ROWS"):
            G.ranked_human(data,60)
    def test_numeric_certifier_rejects_nan_inf_and_negative_bound(self):
        for x in (math.nan,math.inf,-math.inf):
            self.assertFalse(G.safely_excluded(x,0.0,1.0))
            self.assertFalse(G.safely_excluded(0.0,x,1.0))
            self.assertFalse(G.safely_excluded(0.0,0.0,x))
        self.assertFalse(G.safely_excluded(-1.0,-1.0,0.0))
    def test_certified_bounds_cannot_exclude_real_winner(self):
        # Cauchy bound is an actual upper bound on omitted products.
        for partial in (-12.0,-1.0,0.0,1.0,12.0):
            for residual in (-9.0,-.1,0.0,.1,9.0):
                for incumbent in (-10.0,0.0,10.0):
                    if G.safely_excluded(partial,abs(residual),incumbent):
                        self.assertLess(partial+residual,incumbent)
    def test_strict_tie_and_near_tie(self):
        for delta in (0.0,1e-8,1e-6):
            self.assertFalse(G.safely_excluded(2.0-delta,0.0,2.0))
        self.assertTrue(G.safely_excluded(-10.0,1.0,0.0))
    def test_negative_controls_and_no_promotion(self):
        code=P.read_text(encoding="utf-8")
        self.assertIn('promotion_allowed":False',code)
        self.assertIn('scientific_acceptance":"NOT_GRANTED"',code)
        self.assertIn('G73_ORIGINAL_EXACT_NEXT_TOKEN_MISMATCH',code)
        self.assertIn('G73_FROZEN_PRIOR_RANKING_IDENTITY_DRIFT',code)
        self.assertIn('FALLBACK_COUNT',code)
        self.assertNotIn('model.train(',code)
    def test_frozen_performance_gate(self):
        self.assertEqual(G.THRESHOLDS,{"prune_fraction":0.50,"fallback_fraction":0.0,
            "head_speedup":1.20,"amortized_speedup":1.15,"min_pair_ratio":0.80,"rss_ratio":1.10})

if __name__=="__main__":
    unittest.main()
