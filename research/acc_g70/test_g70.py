"""G70 preregistered source/negative diagnostic contracts."""
import importlib.util
from pathlib import Path
import unittest

SOURCE=Path(__file__).with_name("g70_qproj_shapes.py")
spec=importlib.util.spec_from_file_location("g70",SOURCE)
g=importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)

def fixture():
    import torch
    result={}
    for dtype in g.PRECISIONS:
        result[dtype]={}
        for mode in g.MODES:
            log={"greedy_argmax_id":(7866 if dtype=="float16" and mode=="cached_one_by_one" else 29871),
                 "exact_max_tie_count":(2 if dtype=="float16" and mode=="cached_one_by_one" else 1),
                 "candidate_minus_baseline_logit":0.0}
            base=torch.ones(4)
            val=base*(2.0 if dtype=="float16" and mode!="cached_one_by_one" else 1.0)
            result[dtype][mode]=[{
                "logits":dict(log),"hooked":val.clone(),"direct":val.clone(),
                "input_norm_matches":True,"direct_matches_hook":True,
                "reference_delta":{"equal_exact":True,"l2":0.0,
                                   "relative_l2":0.0,"max_absolute":0.0}}
                for _ in range(3)]
    return result

class G70(unittest.TestCase):
    def test_exact_source_custody(self):
        x=g.source_identity()
        self.assertEqual(x["g69_script_git_blob"],g.G69_SCRIPT_BLOB)
        self.assertEqual(x["g69_final_git_blob"],g.G69_FINAL_BLOB)
    def test_original_source_hashes(self):
        self.assertEqual(g.g63.WEIGHT_SHA,"6e6001da2106d4757498752a021df6c2bdc332c650aae4bae6b0c004dcf14933")
        self.assertEqual(g.g64.G63_CORPUS_SHA256,"d790b833ef8cf03a90db7bf1271b7520b83c45ce07ba3c1a9699df81e239eca0")
        self.assertEqual(g.original.G64_PROMPT_HASH,"19a85c78f14d5470d79d51c83a25d69a9b54953eb0024d223e82e34376529c59")
    def test_frozen_modes(self):
        self.assertEqual(g.MODE_TO_ROWS,{"cached_one_by_one":1,"cached_chunk_48":48,"full_no_cache":1584})
        self.assertEqual(g.REPEATS,3)
        self.assertEqual(len(g.MODES)*len(g.PRECISIONS)*g.REPEATS,18)
    def test_all_matched_is_only_diagnostic(self):
        x=g.assess(fixture())
        self.assertEqual(x["diagnostic"],"DIRECT_QPROJECTION_SHAPE_REPRODUCED")
        self.assertEqual(x["scientific_acceptance"],"NOT_GRANTED")
        self.assertEqual(x["g63_original_generalization"],"FAIL_NO_GO_UNCHANGED")
        self.assertEqual(x["g67_original_engineering"],"NO_GO_ENGINEERING")
    def test_mismatch_not_proof(self):
        a=fixture()
        a["float16"]["cached_chunk_48"][0]["hooked"][0]+=1
        a["float16"]["cached_chunk_48"][0]["direct_matches_hook"]=False
        x=g.assess(a)
        self.assertEqual(x["diagnostic"],"SHAPE_ISOLATION_INCONCLUSIVE")
    def test_no_fp16_shape_effect_no_proof(self):
        a=fixture()
        for row in a["float16"]["cached_chunk_48"]:
            row["direct"]=row["hooked"]=row["direct"]/2
        self.assertEqual(g.assess(a)["diagnostic"],"SHAPE_ISOLATION_INCONCLUSIVE")
    def test_nonmatching_input_blocks(self):
        a=fixture()
        a["float16"]["full_no_cache"][0]["input_norm_matches"]=False
        with self.assertRaises(ValueError):g.assess(a)
    def test_missing_repeat_blocks(self):
        a=fixture()
        a["float32"]["cached_one_by_one"].pop()
        with self.assertRaises(ValueError):g.assess(a)
    def test_wrong_modes_blocks(self):
        a=fixture()
        a["float32"].pop("full_no_cache")
        with self.assertRaises(ValueError):g.assess(a)
    def test_nondeterministic_logits_blocks(self):
        a=fixture()
        a["float16"]["cached_chunk_48"][2]["logits"]["greedy_argmax_id"]=9
        with self.assertRaises(ValueError):g.assess(a)
    def test_nondeterministic_q_blocks(self):
        a=fixture()
        a["float16"]["cached_one_by_one"][1]["direct"][0]=12
        with self.assertRaises(ValueError):g.assess(a)
    def test_source_not_production(self):
        t=SOURCE.read_text(encoding="utf-8")
        self.assertIn('"scientific_acceptance":"NOT_GRANTED"',t)
        self.assertIn("torch.backends.cuda.matmul.allow_tf32=False",t)
        self.assertIn("original.validate_orig_outputs",t)
    def test_original_shape_unknown_rejected(self):
        class Fake:
            shape=(1,1584,7)
        with self.assertRaises(ValueError):g.direct_output(None,Fake(),"foo")

if __name__=="__main__":
    unittest.main()
