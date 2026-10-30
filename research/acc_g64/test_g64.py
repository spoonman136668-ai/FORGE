"""ACC G64 offline tests; original model, corpus and network not needed."""
import importlib.util
import tempfile
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location("g64",Path(__file__).with_name("g64_token_forensics.py"))
g=importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)

class G64PinnedForensicContract(unittest.TestCase):
 def test_frozen_original_git_blobs(self):
  self.assertEqual(g.pinned_source_assertions()["g63_original_git_blob"],"33cdfa236ae79c3eed0c1968cb5d839d4af4b3d7")
 def test_known_git_blob_sha1(self):
  self.assertEqual(g.git_blob(b"abc"),"f2ba8f84ab5c1bce84a7b441cb1959cfc7093b7f")
 def test_original_failed_case_unchanged(self):
  self.assertEqual((g.ANCHOR,g.TASK,g.CONTEXT,g.NEW_TOKENS,g.PAIRS),(2,"natural_continuation",1536,64,5))
 def test_pair_order_exact(self):
  self.assertEqual([g.paired_order(i) for i in range(g.PAIRS)],
   [("baseline","candidate"),("candidate","baseline"),("baseline","candidate"),("candidate","baseline"),("baseline","candidate")])
 def test_equal_exact_ids(self):
  ids=list(range(64))
  d=g.first_difference(ids,ids)
  self.assertTrue(d["equal"]);self.assertEqual(d["same_prefix_tokens"],64)
  self.assertIsNone(d["first_mismatch_index"])
 def test_first_difference_index_zero_and_fifty(self):
  a=list(range(64))
  b=a.copy();b[50]=100
  self.assertEqual(g.first_difference(a,b)["first_mismatch_index"],50)
  b=a.copy();b[0]=99
  self.assertEqual(g.first_difference(a,b)["first_mismatch_index"],0)
 def test_wrong_length_fails_closed(self):
  with self.assertRaises(ValueError):g.first_difference([1]*63,[1]*64)
 def test_within_arm_nondeterminism_detection(self):
  a=list(range(64));b=a.copy();b[7]=900
  self.assertEqual(g.first_unequal_across_repeats([a,a,b]),7)
  self.assertIsNone(g.first_unequal_across_repeats([a,a,a]))
 def test_original_data_identity_and_no_relaxed_parity(self):
  self.assertEqual(g.G63_CORPUS_SHA256,"d790b833ef8cf03a90db7bf1271b7520b83c45ce07ba3c1a9699df81e239eca0")
  s=Path(__file__).with_name("g64_token_forensics.py").read_text(encoding="utf-8")
  self.assertIn('"original_g63_final":"FAIL_NO_GO_UNCHANGED"',s)
  self.assertIn('"novel_acceleration_claim":False',s)
  self.assertIn('first_difference(result["baseline"]["first_64_token_ids"]',s)
 def test_g62_extra_token_policy_not_altered(self):
  x=list(range(64))
  accepted,total=g.audited_continuation(x+[99],"candidate")
  self.assertEqual((accepted,total),(x,65))
  with self.assertRaises(RuntimeError):
   g.audited_continuation(x+[99],"baseline")

if __name__=="__main__": unittest.main()
