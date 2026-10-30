"""G68 fixed provenance, stage completeness, negative controls (source-only)."""
import importlib.util
from pathlib import Path
import unittest

SRC = Path(__file__).with_name("g68_hidden_attribution.py")
spec = importlib.util.spec_from_file_location("g68", SRC)
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)

def sample():
    import torch
    rows = {}
    for dtype in g.PRECISIONS:
        rows[dtype] = {}
        for m in g.MODES:
            argmax = 7866 if dtype == "float16" and m == "cached_one_by_one" else 29871
            tie = 2 if dtype == "float16" and m == "cached_one_by_one" else 1
            vals = {}
            for stage in g.STAGES:
                vals[stage] = torch.ones(4, dtype=torch.float32)
            rows[dtype][m] = [
                {"logits":{"greedy_argmax_id":argmax,"exact_max_tie_count":tie,
                           "candidate_minus_baseline_logit":.01,
                           "head_fp32_projected_margin":.02},
                 "vectors":dict(vals)}
                for _ in range(g.REPEATS)]
    return rows

class Frozen(unittest.TestCase):
    def test_immutable_original(self):
        x=g.frozen_identity()
        self.assertEqual(x["g67_executable_blob"],g.G67_SOURCE_BLOB)
        self.assertEqual(x["g67_final_blob"],g.G67_FINAL_BLOB)
    def test_frozen_model_and_sources(self):
        self.assertEqual(g.g63.WEIGHT_SHA,
             "6e6001da2106d4757498752a021df6c2bdc332c650aae4bae6b0c004dcf14933")
        self.assertEqual(g.g64.G63_CORPUS_SHA256,
             "d790b833ef8cf03a90db7bf1271b7520b83c45ce07ba3c1a9699df81e239eca0")
        self.assertEqual(g.original.G64_PROMPT_HASH,
             "19a85c78f14d5470d79d51c83a25d69a9b54953eb0024d223e82e34376529c59")
    def test_18_traces_23_hooks(self):
        self.assertEqual(len(g.STAGES),23)
        self.assertEqual(g.STAGES[0],"layer_00")
        self.assertEqual(g.STAGES[-1],"final_norm")
        self.assertEqual(g.REPEATS*len(g.PRECISIONS)*len(g.MODES),18)
    def test_complete_is_diagnostic_only(self):
        x=g.adjudicate(sample())
        self.assertEqual(x["screen"],"COMPLETE_NUMERICAL_ATTRIBUTION_SCREEN")
        self.assertEqual(x["scientific_acceptance"],"NOT_GRANTED")
        self.assertEqual(x["g67_original_engineering"],"NO_GO_ENGINEERING")
        self.assertEqual(x["g63_original_generalization"],"FAIL_NO_GO_UNCHANGED")
    def test_wrong_original_argmax_blocks(self):
        x=sample()
        x["float32"]["cached_one_by_one"][0]["logits"]["greedy_argmax_id"]=7866
        with self.assertRaises(ValueError):g.adjudicate(x)
    def test_wrong_original_tie_blocks(self):
        x=sample()
        for item in x["float16"]["cached_one_by_one"]:
            item["logits"]["exact_max_tie_count"]=1
        with self.assertRaises(ValueError):g.adjudicate(x)
    def test_missing_stage_blocks(self):
        x=sample()
        del x["float16"]["cached_chunk_48"][0]["vectors"]["final_norm"]
        with self.assertRaises(ValueError):g.adjudicate(x)
    def test_missing_repeat_blocks(self):
        x=sample()
        x["float32"]["full_no_cache"].pop()
        with self.assertRaises(ValueError):g.adjudicate(x)
    def test_nondeterministic_margin_blocks(self):
        x=sample()
        x["float16"]["cached_chunk_48"][2]["logits"]["head_fp32_projected_margin"]=.07
        with self.assertRaises(ValueError):g.adjudicate(x)
    def test_vector_equal_metrics(self):
        import torch
        v=torch.tensor([1.0,2.0,3.0])
        x=g.vector_difference(v,v)
        self.assertTrue(x["equal_exact"])
        self.assertEqual(x["max_absolute"],0)
    def test_first_differing_stage(self):
        import torch
        samples={m:{s:torch.tensor([1.,2.]) for s in g.STAGES} for m in g.MODES}
        samples["cached_one_by_one"]["layer_07"]=torch.tensor([1.,3.])
        pairs=g.pair_summary(samples)
        self.assertEqual(pairs["full_no_cache"]["first_bitwise_different_stage"],"layer_07")
        self.assertFalse(pairs["cached_chunk_48"]["all_23_exact"])
    def test_output_no_promotion(self):
        txt=SRC.read_text(encoding="utf-8")
        self.assertIn('"scientific_acceptance":"NOT_GRANTED"',txt)
        self.assertIn('"g67_original_engineering":"NO_GO_ENGINEERING"',txt)
        self.assertIn("torch.backends.cuda.matmul.allow_tf32 = False",txt)

if __name__=="__main__":
    unittest.main()
