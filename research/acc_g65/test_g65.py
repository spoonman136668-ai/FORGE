"""ACC G65 offline source integrity + numerical-classification falsification tests."""
import importlib.util
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location("g65",Path(__file__).with_name("g65_logit_path.py"))
g=importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)

class G65FrozenContract(unittest.TestCase):
 def test_source_helper_identity(self):
  result=g.identity()
  self.assertEqual(result["g64_source_git_blob"],g.G64_GIT_BLOB)
  self.assertEqual(result["g63_original_git_blob"],"33cdfa236ae79c3eed0c1968cb5d839d4af4b3d7")
 def test_original_g64_exact_failing_input(self):
  self.assertEqual(g.G64_PROMPT_HASH,"19a85c78f14d5470d79d51c83a25d69a9b54953eb0024d223e82e34376529c59")
  self.assertEqual((g.POSITION,g.SHARED_TOKENS,g.REPEATS),(48,48,3))
 def test_original_token_ids_and_hashes(self):
  self.assertEqual((g.BASELINE_ID,g.CANDIDATE_ID),(7866,29871))
  self.assertEqual(g.BASELINE_SHA,"50a1ab137948f57c8c4f06e92ca3900770b0abd01b0e0a531df560315f746d88")
  self.assertEqual(g.CANDIDATE_SHA,"d4e72f3fbdf4b267bf167cce321fd61d4066423ab088ae406f8d20bccf49d01e")
 def test_three_frozen_modes_only(self):
  self.assertEqual(g.MODES,("cached_one_by_one","cached_chunk_48","full_no_cache"))
 def test_sha_uses_original_json_list_canonicalization(self):
  self.assertEqual(g.token_sha([1,2,3]),"a36b1f2c3f84522dd100c004a9e09f1ce8ee00b4ad1d87fba43c82f009f47c49")
 def test_full_source_refuses_to_change_g63_final(self):
  src=Path(__file__).with_name("g65_logit_path.py").read_text(encoding="utf-8")
  self.assertIn('"original_g63_final":"FAIL_NO_GO_UNCHANGED"',src)
  self.assertIn('"novel_acceleration":False',src)
  self.assertIn('"causal_root_cause_conclusively_proven":False',src)
 def test_classify_true_split(self):
  fake={
   "cached_one_by_one":[{"top1_id":g.BASELINE_ID} for _ in range(3)],
   "cached_chunk_48":[{"top1_id":g.CANDIDATE_ID} for _ in range(3)],
   "full_no_cache":[{"top1_id":g.CANDIDATE_ID} for _ in range(3)]
  }
  d=g.classify(fake)
  self.assertTrue(d["cached_full_argmax_split_reproduced"])
  self.assertEqual(d["classification"],"REPRODUCED_CACHED_FULL_ARGMAX_SPLIT")
 def test_classify_refuses_incomplete_repeats(self):
  with self.assertRaises(ValueError):g.classify({x:[] for x in g.MODES})
 def test_classify_detects_numerical_drift(self):
  fake={x:[{"top1_id":g.CANDIDATE_ID} for _ in range(3)] for x in g.MODES}
  self.assertEqual(g.classify(fake)["classification"],"G64_NUMERICAL_PATH_OBSERVATION_DRIFT")
 def test_zero_tuning_and_three_same_context_modes(self):
  src=Path(__file__).with_name("g65_logit_path.py").read_text(encoding="utf-8")
  self.assertIn('torch.backends.cuda.matmul.allow_tf32=False',src)
  self.assertIn('attention_mask=attention,use_cache=True',src)
  self.assertIn('use_cache=False).logits[0,-1,:]',src)
if __name__=="__main__":unittest.main()
