"""CPU G79 frozen original-model experiment first-use and source-only controls."""
import importlib.util
from pathlib import Path
import unittest

P=Path(__file__).with_name("g79_minstate_decode.py")
S=importlib.util.spec_from_file_location("cpu_g79_source",P)
G=importlib.util.module_from_spec(S);S.loader.exec_module(G)

class OriginalG79FrozenAdmission(unittest.TestCase):
    def test_preregistration_before_candidate(self):
        G.contract()
        self.assertEqual(G.PREREG,"5b0ad0551ed0a7027eca9bfba2ceba3cdbb64fb7")
        self.assertEqual(G.FROZEN,{"median_speedup":1.15,
           "minimum_paired_ratio":0.80,"p95_ratio_max":1.10,"rss_ratio_max":1.10})
    def test_original_model_and_dataset(self):
        self.assertEqual(G.MODEL_REV,"607a30d783dfa663caf39e06633721c8d4cfcd7e")
        self.assertEqual(G.WEIGHTS_SHA,"248dfc3911869ec493c76e65bf2fcf7f615828b0254c12b473182f0f81d3a707")
        self.assertEqual(G.DATA_SHA,"3730d312f6e3440559ace48831e51066acaca737f6eabec99bccb9e4b3c39d14")
        self.assertEqual(G.DATA_SIZE,749738)
    def test_new_original_heldout_disjoint(self):
        sample=[{"instruction":f"Independent authentic test problem {i}","category":"math"} for i in range(133)]
        ranks=G.rank_original(sample,120)
        self.assertEqual(len(ranks),120)
        self.assertTrue({v["source_row"] for v in ranks[108:120]}.isdisjoint(
            {v["source_row"] for v in ranks[:108]}))
        self.assertEqual(len({v["instruction_sha256"] for v in ranks}),120)
    def test_duplicate_fail_closed(self):
        sample=[{"instruction":"duplicate","category":"math"} for _ in range(133)]
        with self.assertRaisesRegex(RuntimeError,"G79_INSUFFICIENT_UNSEEN_ORIGINAL_INPUTS"):
            G.rank_original(sample,120)
    def test_frozen_arms_and_authentic_counts(self):
        self.assertEqual(G.ARMS,("explicit_mask","hf_generate","minimal_state"))
        self.assertEqual(G.CASES*G.REPEATS*len(G.ARMS),144)
        self.assertEqual(G.CASES*G.REPEATS*len(G.ARMS)*G.TOKENS,1152)
        self.assertEqual((G.CPU_BUDGET,G.OFFSET),(3,108))
    def test_counterbalanced_order(self):
        self.assertEqual(set(G.order_for(0,0)),set(G.ARMS))
        self.assertEqual(len({G.order_for(0,i) for i in range(4)}),4)
    def test_nearest_rank_p95(self):
        self.assertEqual(G.p95(list(range(20))),18)
        self.assertEqual(G.p95(list(range(48))),45)
    def test_candidate_no_mask_not_future_reference(self):
        txt=P.read_text()
        needle=txt[txt.index("        def minimal_state(full):"):txt.index("        funcs={")]
        self.assertIn("torch.empty((1,TOKENS),dtype=torch.long)",needle)
        self.assertIn("model(input_ids=next_token,past_key_values=past,use_cache=True)",needle)
        self.assertNotIn("attention_mask=",needle)
        self.assertNotIn("model.generate(",needle)
        self.assertIn("response[:,step]=next_token[:,0]",needle)
    def test_explicit_mask_and_strong_library_control(self):
        txt=P.read_text()
        self.assertIn("mask=torch.ones((1,length+step+1),dtype=torch.long)",txt)
        self.assertIn("attention_mask=torch.ones_like(full)",txt)
        self.assertIn('fastest=min(("explicit_mask","hf_generate")',txt)
        self.assertIn('G79_ORIGINAL_HELDOUT_TOKEN_MISMATCH_',txt)
    def test_no_science_or_production_acceptance(self):
        txt=P.read_text()
        self.assertIn('"scientific_acceptance":"NOT_GRANTED"',txt)
        self.assertIn('"promotion_allowed":False',txt)
        self.assertNotIn("model.train(",txt)
        self.assertNotIn("model.cuda(",txt)

if __name__=="__main__":unittest.main()
