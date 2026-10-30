"""G63 source and acceptance tests; no external I/O or GPU."""
import importlib.util
import tempfile
from pathlib import Path
import unittest
spec=importlib.util.spec_from_file_location("g63",Path(__file__).with_name("g63_heldout_wikitext.py"))
g=importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)
class G63FrozenTests(unittest.TestCase):
 def test_independent_original_test_source_identity(self):
  self.assertEqual(g.CORPUS_REV,"acc295dc7b90714f1bf47f06004fc19a7fe235c4")
  self.assertEqual(g.CORPUS_BLOB,"6f3fc88e4cd88456ea892971f9f12243e8428624")
  self.assertEqual(g.CORPUS_SIZE,1256449)
  self.assertTrue(g.CORPUS_URL.endswith("/word_language_model/data/wikitext-2/test.txt"))
 def test_fixed_model_identity(self):
  self.assertEqual(g.REV,"c13e4efb205d7a8e5d13c088aa10a9dabac9b96a")
  self.assertEqual(g.WEIGHT_SHA,"6e6001da2106d4757498752a021df6c2bdc332c650aae4bae6b0c004dcf14933")
  self.assertEqual(g.WEIGHT_SIZE,2200119864)
 def test_12_fixed_cases(self):
  self.assertEqual(g.ANCHORS,(.17,.45,.73))
  self.assertEqual(g.TASKS,("natural_continuation","source_question"))
  self.assertEqual(g.CONTEXTS,(512,1536))
  self.assertEqual(len(g.ANCHORS)*len(g.TASKS)*len(g.CONTEXTS),12)
 def test_generator_configuration_unmodified_from_g62(self):
  self.assertEqual((g.GEN,g.WARMUPS,g.PAIRS),(64,2,5))
  self.assertEqual([g.paired_order(i) for i in range(5)],
   [("baseline","candidate"),("candidate","baseline"),("baseline","candidate"),
    ("candidate","baseline"),("baseline","candidate")])
 def test_git_blob_hash_implemented_correctly(self):
  self.assertEqual(g.git_blob_sha1(b"abc"),"f2ba8f84ab5c1bce84a7b441cb1959cfc7093b7f")
 def test_source_file_tamper_fail_closed(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/"source.txt";p.write_bytes(b"not original")
   with self.assertRaises(RuntimeError):g.frozen_source(p)
 def test_ngram_overlap_exact(self):
  prompt=[1,2,3,4,5,6]
  self.assertEqual(g.trigram_overlap(prompt,[1,2,3,7,8]),1/3)
  self.assertEqual(g.trigram_overlap(prompt,[7,8,9]),0.)
 def test_generalization_rejects_qa_regression(self):
  rows=[]
  for i in range(3):
   for task in g.TASKS:
    for ctx in g.CONTEXTS:
     rows.append({"task":task,"ratio_baseline_over_candidate":1.7 if task=="natural_continuation" else .8,
      "tokens_exact":True,"candidate_peak_allocated_mib":100,"baseline_peak_allocated_mib":100})
  self.assertEqual(g.decision(rows)[0],"NO_GO_GENERALIZATION")
 def test_global_positive_does_not_imply_novelty(self):
  rows=[]
  for i in range(3):
   for task in g.TASKS:
    for ctx in g.CONTEXTS:
     rows.append({"task":task,"ratio_baseline_over_candidate":1.2,
      "tokens_exact":True,"candidate_peak_allocated_mib":100,"baseline_peak_allocated_mib":100})
  self.assertEqual(g.decision(rows)[0],"GO_EXTERNAL_CORPUS_ENGINEERING")
  s=Path(__file__).with_name("g63_heldout_wikitext.py").read_text(encoding="utf-8")
  self.assertIn('"novel_mechanism":False',s)
  self.assertIn("CORPUS_TOKEN_PARITY_FAILED",s)
  self.assertIn("ACTUAL_OPTIMIZED_SDPA_OPERATOR_MISSING",s)
if __name__=="__main__":unittest.main()
