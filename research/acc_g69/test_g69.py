"""G69 source-provenance and negative controls for original layer0 RTX diagnostic."""
import importlib.util
from pathlib import Path
import unittest

SRC=Path(__file__).with_name("g69_layer0_boundaries.py")
spec=importlib.util.spec_from_file_location("g69",SRC)
g=importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)

def fixture():
    import torch
    data={}
    for dtype in g.DTYPES:
        data[dtype]={}
        for mode in g.MODES:
            argmax=7866 if dtype=="float16" and mode=="cached_one_by_one" else 29871
            tie=2 if dtype=="float16" and mode=="cached_one_by_one" else 1
            data[dtype][mode]=[
                {"logits":{"greedy_argmax_id":argmax,"exact_max_tie_count":tie,
                           "candidate_minus_baseline_logit":.01},
                 "vectors":{s:torch.ones(4,dtype=torch.float32) for s in g.STAGES}}
                for _ in range(3)]
    return data

class Frozen(unittest.TestCase):
    def test_upstream_git_blobs_and_prereg(self):
        z=g.authentic_sources()
        self.assertEqual(z["g68_source_blob"],g.G68_SOURCE_GIT_BLOB)
        self.assertEqual(z["g68_final_blob"],g.G68_FINAL_GIT_BLOB)
    def test_original_model_corpus_prompt(self):
        self.assertEqual(g.g63.WEIGHT_SHA,"6e6001da2106d4757498752a021df6c2bdc332c650aae4bae6b0c004dcf14933")
        self.assertEqual(g.g64.G63_CORPUS_SHA256,"d790b833ef8cf03a90db7bf1271b7520b83c45ce07ba3c1a9699df81e239eca0")
        self.assertEqual(g.original.G64_PROMPT_HASH,"19a85c78f14d5470d79d51c83a25d69a9b54953eb0024d223e82e34376529c59")
    def test_twelve_original_sites_and_18_traces(self):
        self.assertEqual(len(g.STAGES),12)
        self.assertEqual(g.STAGES[0],"layer0_input")
        self.assertEqual(g.STAGES[5],"attention_pre_o_proj")
        self.assertEqual(g.STAGES[-1],"layer0_output")
        self.assertEqual(g.REPEATS*len(g.DTYPES)*len(g.MODES),18)
    def test_positive_diagnostic_not_science(self):
        x=g.adjudicate(fixture())
        self.assertEqual(x["classification"],"COMPLETE_LAYER0_BOUNDARY_DIAGNOSTIC")
        self.assertEqual(x["scientific_acceptance"],"NOT_GRANTED")
        self.assertEqual(x["g63_generalization"],"FAIL_NO_GO_UNCHANGED")
        self.assertEqual(x["g67_engineering"],"NO_GO_ENGINEERING")
    def test_missing_stage_blocks(self):
        r=fixture()
        del r["float16"]["cached_one_by_one"][0]["vectors"]["q_proj"]
        with self.assertRaises(ValueError):g.adjudicate(r)
    def test_wrong_fp16_argmax_blocks(self):
        r=fixture()
        r["float16"]["cached_one_by_one"][0]["logits"]["greedy_argmax_id"]=29871
        with self.assertRaises(ValueError):g.adjudicate(r)
    def test_wrong_fp32_argmax_blocks(self):
        r=fixture()
        for x in r["float32"]["cached_one_by_one"]:
            x["logits"]["greedy_argmax_id"]=7866
        with self.assertRaises(ValueError):g.adjudicate(r)
    def test_original_tie_count_blocks(self):
        r=fixture()
        for x in r["float16"]["cached_one_by_one"]:
            x["logits"]["exact_max_tie_count"]=1
        with self.assertRaises(ValueError):g.adjudicate(r)
    def test_nonfinite_margin_blocks(self):
        r=fixture()
        r["float16"]["cached_chunk_48"][0]["logits"]["candidate_minus_baseline_logit"]=float("nan")
        with self.assertRaises(ValueError):g.adjudicate(r)
    def test_nondeterministic_repeat_blocks(self):
        r=fixture()
        r["float16"]["cached_chunk_48"][2]["logits"]["candidate_minus_baseline_logit"]=.5
        with self.assertRaises(ValueError):g.adjudicate(r)
    def test_earliest_boundary_is_descriptive(self):
        import torch
        v={m:{s:torch.ones(4) for s in g.STAGES} for m in g.MODES}
        v["cached_one_by_one"]["attention_pre_o_proj"]=torch.ones(4)*2
        z=g.compare(v)
        self.assertEqual(z["cached_chunk_48"]["earliest_bitwise_difference"],"attention_pre_o_proj")
        self.assertTrue(z["full_no_cache"]["stage_deltas"]["q_proj"]["equal_exact"])
    def test_mismatched_shape_blocks(self):
        import torch
        v={m:{s:torch.ones(4) for s in g.STAGES} for m in g.MODES}
        v["cached_chunk_48"]["mlp_down"]=torch.ones(3)
        with self.assertRaises(ValueError):g.compare(v)
    def test_source_do_not_mutate_or_promote(self):
        text=SRC.read_text(encoding="utf-8")
        self.assertIn('"scientific_acceptance":"NOT_GRANTED"',text)
        self.assertIn('torch.backends.cuda.matmul.allow_tf32=False',text)
        self.assertIn("attn_implementation=\"sdpa\"",text)
        self.assertIn('torch.cuda.synchronize(device)',text)

if __name__=="__main__":
    unittest.main()
