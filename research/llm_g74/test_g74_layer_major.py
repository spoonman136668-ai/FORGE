"""G74 frozen source-only guardrails; no original model downloaded."""
import importlib.util
import hashlib
from pathlib import Path
import unittest

PATH=Path(__file__).with_name("g74_layer_major.py")
s=importlib.util.spec_from_file_location("g74_source",PATH)
g=importlib.util.module_from_spec(s)
s.loader.exec_module(g)

class G74FrozenTests(unittest.TestCase):
    def test_frozen_source_contract(self):
        g.contract()
        self.assertEqual(g.PREREG,"000ed3607eaa0b55313f9d0f5387a0f87262bdc1")
        self.assertEqual((g.SELECT_OFFSET,g.CASES,g.WAVE,g.TOKENS,g.REPEATS),(60,12,3,8,3))
    def test_original_external_sha(self):
        self.assertEqual(g.WEIGHTS_SHA,"248dfc3911869ec493c76e65bf2fcf7f615828b0254c12b473182f0f81d3a707")
        self.assertEqual(g.DATA_SHA,"3730d312f6e3440559ace48831e51066acaca737f6eabec99bccb9e4b3c39d14")
    def test_left_padding_positions(self):
        ids,mask,pos=g.left_padded_tokens([[8,9,10],[4],[3,7]],99)
        self.assertEqual(ids,[[8,9,10],[99,99,4],[99,3,7]])
        self.assertEqual(mask,[[1,1,1],[0,0,1],[0,1,1]])
        self.assertEqual(pos,[[0,1,2],[0,0,0],[0,0,1]])
    def test_invalid_empty_prompt_fails(self):
        with self.assertRaisesRegex(ValueError,"G74_EMPTY_PROMPT"):
            g.left_padded_tokens([[3],[]],99)
    def test_exact_rank_partition(self):
        rows=[{"instruction":"Real public hand-authored question "+str(i),"category":"math"} for i in range(85)]
        ranked=g.rank_original_human(rows,72)
        self.assertEqual(len(ranked),72)
        self.assertEqual(len(set(v["source_row"] for v in ranked)),72)
        self.assertEqual(len(set(v["instruction_sha256"] for v in ranked[60:72])),12)
    def test_duplicates_insufficient_fail_closed(self):
        rows=[{"instruction":"duplicate","category":"math"} for _ in range(90)]
        with self.assertRaisesRegex(RuntimeError,"G74_INSUFFICIENT_AUTHENTIC_HUMAN_QUESTIONS"):
            g.rank_original_human(rows,72)
    def test_all_arm_fairness(self):
        self.assertEqual(g.ARMS,("solo_serial","solo_parallel","hf_batched","layer_major"))
        self.assertEqual(len(g.ARMS)*g.CASES*g.REPEATS,144)
        self.assertEqual(g.THRESHOLDS,{"median_speedup":1.15,"min_wave_ratio":0.90,
            "p95_wave_ratio":1.20,"sampled_rss_ratio":1.10})
    def test_no_accepted_science_or_model_mutation(self):
        text=PATH.read_text()
        self.assertIn('"scientific_acceptance":"NOT_GRANTED"',text)
        self.assertIn('"promotion_allowed":False',text)
        self.assertNotIn("model.train(",text)
        self.assertIn("G74_ORIGINAL_GENERATION_PARITY_",text)
        self.assertIn('G74_ORIGINAL_RANK_DISJOINTNESS_VIOLATION',text)
        self.assertIn("HF",text.upper())
    def test_p95_frozen_rank(self):
        self.assertEqual(g.p95(list(range(12))),11)

if __name__=="__main__":unittest.main()
