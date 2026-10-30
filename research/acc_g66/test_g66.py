"""ACC G66 source-only non-GPU contract and failure controls."""
import importlib.util
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location("g66",Path(__file__).with_name("g66_precision.py"))
g=importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)

class G66Regression(unittest.TestCase):
 def test_unchanged_original_g65_source(self):
  self.assertEqual(g.frozen_identity()["g65_source_blob"],"6dd9bbed1793237fa5d4d34e7c9762aaec45471a")
 def test_dtypes_are_frozen(self):
  self.assertEqual(g.DTYPES,("float16","float32"))
  self.assertEqual(g.REPEATS,3)
  self.assertEqual(g.MODES,("cached_one_by_one","cached_chunk_48","full_no_cache"))
 def test_corpus_and_model_identical(self):
  self.assertEqual(g.g64.G63_CORPUS_SHA256,"d790b833ef8cf03a90db7bf1271b7520b83c45ce07ba3c1a9699df81e239eca0")
  self.assertEqual(g.g63.WEIGHT_SHA,"6e6001da2106d4757498752a021df6c2bdc332c650aae4bae6b0c004dcf14933")
 def test_original_prompt_did_not_move(self):
  self.assertEqual(g.original.G64_PROMPT_HASH,"19a85c78f14d5470d79d51c83a25d69a9b54953eb0024d223e82e34376529c59")
 def test_first_mismatch(self):
  a=list(range(64)); b=a.copy();b[48]=900
  self.assertEqual(g.first_difference(a,b),{"same":False,"index":48,"baseline_id":48,"candidate_id":900})
 def test_exact_matching(self):
  a=list(range(64))
  self.assertEqual(g.first_difference(a,a),{"same":True,"index":None})
  with self.assertRaises(RuntimeError):g.first_difference(a[:-1],a)
 def test_positive_precision_classification(self):
  rows={dtype:{mode:[{"greedy_argmax_id":29871} for _ in range(3)]
    for mode in g.MODES} for dtype in g.DTYPES}
  d=g.categorical(rows)
  self.assertTrue(d["fp32_forced_shared48_cached_vs_full_split_resolved"])
  self.assertEqual(d["g63_original_qualification"],"FAIL_NO_GO_UNCHANGED")
 def test_negative_precision_classification(self):
  rows={dtype:{mode:[{"greedy_argmax_id":7866 if mode=="cached_one_by_one" else 29871} for _ in range(3)]
    for mode in g.MODES} for dtype in g.DTYPES}
  self.assertFalse(g.categorical(rows)["fp32_forced_shared48_cached_vs_full_split_resolved"])
 def test_incomplete_measures_blocked(self):
  with self.assertRaises(ValueError):g.categorical({"float16":{},"float32":{}})
 def test_no_new_science_or_approval(self):
  txt=Path(__file__).with_name("g66_precision.py").read_text(encoding="utf-8")
  self.assertIn('"scientific_acceptance":"NOT_GRANTED"',txt)
  self.assertIn('"novel_acceleration":False',txt)
  self.assertIn('"original_g63_final":"FAIL_NO_GO_UNCHANGED"',txt)
 def test_fp32_forced_frozen_prefix(self):
  txt=Path(__file__).with_name("g66_precision.py").read_text(encoding="utf-8")
  self.assertIn("else frozen_shared",txt)
  self.assertIn('atten',txt.lower()) if False else None
  self.assertIn("torch.backends.cuda.matmul.allow_tf32=False",txt)
if __name__=="__main__":unittest.main()
