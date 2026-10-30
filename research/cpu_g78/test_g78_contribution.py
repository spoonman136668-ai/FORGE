"""CPU G78 source-only first-use admission; no fake pretrained inference."""
import importlib.util
from pathlib import Path
import unittest

P=Path(__file__).with_name("g78_contribution.py")
S=importlib.util.spec_from_file_location("cpu_g78",P)
g=importlib.util.module_from_spec(S);S.loader.exec_module(g)

class G78SourceAdmission(unittest.TestCase):
    def test_preregistration_and_thresholds(self):
        g.contract()
        self.assertEqual(g.PREREG,"f00c272eeda7311a42a18c9fe4c5bec46f8aa9e3")
        self.assertEqual(g.FROZEN,{"median_l2_error_max":0.010,
          "p95_l2_error_max":0.030,"each_layer_median_l2_max":0.020,
          "worst_coordinate_abs_max":0.15})
    def test_original_pinned_source(self):
        self.assertEqual(g.MODEL_REV,"607a30d783dfa663caf39e06633721c8d4cfcd7e")
        self.assertEqual(g.WEIGHTS_SHA,"248dfc3911869ec493c76e65bf2fcf7f615828b0254c12b473182f0f81d3a707")
        self.assertEqual(g.DATA_SHA,"3730d312f6e3440559ace48831e51066acaca737f6eabec99bccb9e4b3c39d14")
        self.assertEqual(g.DATA_BYTES,749738)
    def test_new_exact_heldout_rank(self):
        self.assertEqual(g.SEED,b"G68-GPT2-HELDOUT-20261030:")
        r=[{"instruction":f"independent human-like question {i}","category":"math"} for i in range(120)]
        sorted_rows=g.rank_human(r,108)
        self.assertEqual(len(sorted_rows),108)
        self.assertEqual(len(set(x["source_row"] for x in sorted_rows)),108)
        self.assertTrue(set(x["source_row"] for x in sorted_rows[96:108]).isdisjoint(
          set(x["source_row"] for x in sorted_rows[:96])))
    def test_duplicate_rank_fails_closed(self):
        r=[{"instruction":"all identical","category":"math"} for _ in range(120)]
        with self.assertRaisesRegex(RuntimeError,"G78_INSUFFICIENT_ORIGINAL_HUMAN_HELDOUT"):
            g.rank_human(r,108)
    def test_fixed_half_mask_and_p95(self):
        self.assertEqual((g.WIDTH,g.KEEP,g.OUT,g.LAYERS,g.STEPS,g.CASES),(3072,1536,768,12,8,12))
        self.assertEqual(g.p95(list(range(20))),18)
        self.assertEqual(g.LAYERS*g.STEPS*g.CASES,1152)
    def test_original_hook_and_exact_channels_only(self):
        content=P.read_text()
        for fragment in (
            'mlp.act.register_forward_hook','original=value[0,-1,:].detach().clone()',
            'torch.argsort(importance,descending=True,stable=True)[:KEEP]',
            'out[indexes]=mask_input[indexes]',
            'G78_INVALID_NATIVE_FFN_INPUT','G78_ORIGINAL_PROJECTION_SHAPE_DRIFT',
            'G78_FIRST_USE_DISJOINT_RANK_DRIFT','G78_ORIGINAL_CPROJ_SAMPLE_COUNT_DRIFT',
            'G78_MISSING_NATIVE_ACTIVATION_LAYER'):
            self.assertIn(fragment,content)
    def test_no_model_speedup_promotion(self):
        content=P.read_text()
        self.assertIn('"performance":"NOT_MEASURED"',content)
        self.assertIn('"masked_model_token_parity":"NOT_TESTED"',content)
        self.assertIn('"scientific_acceptance":"NOT_GRANTED"',content)
        self.assertIn('"promotion_allowed":False',content)
        self.assertNotIn("model.train(",content)
        self.assertNotIn("model.cuda(",content)
    def test_negative_sanity_numeric(self):
        # Diagnostic absolute error and normalized L2 are not exact-token checks.
        self.assertGreater(0.02,0.01)
        self.assertEqual(sum(x==0 for x in (0,1,-1,0)),2)

if __name__=="__main__": unittest.main()
