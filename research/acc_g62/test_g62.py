import importlib.util
import tempfile
from pathlib import Path
import unittest
s=importlib.util.spec_from_file_location("g62",Path(__file__).with_name("g62_prompt_lookup.py"))
g=importlib.util.module_from_spec(s);s.loader.exec_module(g)
class FrozenG62Tests(unittest.TestCase):
 def test_checkpoint_identity(self):
  self.assertEqual(g.REV,"c13e4efb205d7a8e5d13c088aa10a9dabac9b96a")
  self.assertEqual(g.WEIGHT_SHA,"6e6001da2106d4757498752a021df6c2bdc332c650aae4bae6b0c004dcf14933")
  self.assertEqual(g.WEIGHT_BYTES,2200119864)
 def test_frozen_workloads(self):
  self.assertEqual(g.FAMILIES,("structured","grounded","freeform"))
  self.assertEqual(g.CONTEXTS,(512,1536))
  self.assertEqual((g.NEW_TOKENS,g.TRIALS,g.WARMUPS),(64,5,2))
 def test_alternating_pairs(self):
  self.assertEqual([g.order(i) for i in range(5)],
   [("baseline","candidate"),("candidate","baseline"),("baseline","candidate"),
    ("candidate","baseline"),("baseline","candidate")])
 def test_prompt_family_all_distinct(self):
  self.assertEqual(len({g.prompt(x) for x in g.FAMILIES}),3)
  with self.assertRaises(ValueError):g.prompt("invented")
 def test_median(self):
  self.assertEqual(g.median([1.,9.,2.,4.,3.]),3.)
 def test_stop_on_nonstructured_regression(self):
  rows=[{"family":f,"ratio_baseline_over_candidate":r,"all_token_ids_identical":True,
     "baseline_peak_allocated_mib":100,"candidate_peak_allocated_mib":100}
     for f,r in (("structured",1.2),("structured",1.2),("grounded",.4),
                 ("grounded",.4),("freeform",.4),("freeform",.4))]
  self.assertEqual(g.decision(rows)[0],"NO_GO")
 def test_narrow_positive_not_original_novelty(self):
  rows=[{"family":f,"ratio_baseline_over_candidate":1.2,"all_token_ids_identical":True,
    "baseline_peak_allocated_mib":100,"candidate_peak_allocated_mib":100}
    for f in ("structured","structured","grounded","grounded","freeform","freeform")]
  self.assertEqual(g.decision(rows)[0],"GO_NARROW_ENGINEERING")
  body=Path(__file__).with_name("g62_prompt_lookup.py").read_text(encoding="utf-8")
  self.assertIn('"novel_acceleration":False',body)
  self.assertIn("GREEDY_SEQUENCE_MISMATCH",body)
  self.assertIn("ACTUAL_OPTIMIZED_SDPA_OPERATOR_NOT_OBSERVED",body)
 def test_speculative_length_overrun_charged_not_discarded(self):
  frozen=list(range(g.NEW_TOKENS))
  tokens,raw_len=g.audited_continuation(frozen+[65],"candidate")
  self.assertEqual((tokens,raw_len),(frozen,g.NEW_TOKENS+1))
  self.assertEqual(g.audited_continuation(frozen,"baseline")[1],g.NEW_TOKENS)
  with self.assertRaises(RuntimeError):g.audited_continuation(frozen+[65],"baseline")
  with self.assertRaises(RuntimeError):g.audited_continuation(frozen+[65]*6,"candidate")
  with self.assertRaises(RuntimeError):g.audited_continuation(frozen[:-1],"candidate")
 def test_sha_helper(self):
  with tempfile.TemporaryDirectory() as path:
   p=Path(path)/"x";p.write_bytes(b"abc")
   self.assertEqual(g.sha256(p),"ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad")
if __name__=="__main__":unittest.main()
