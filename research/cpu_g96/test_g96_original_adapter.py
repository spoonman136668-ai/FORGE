import unittest
from unittest.mock import patch
from g96_original_adapter import assert_parity,select_cohort
from g96_admission import AdmissionCache,BYTE_LIMIT

class AdapterContractTests(unittest.TestCase):
 def test_exact_output_parity(self):
  assert_parity({0:[1,2],1:[3]},{0:[1,2],1:[3]})
  with self.assertRaisesRegex(RuntimeError,"G96_EXACT_TOKEN_MISMATCH"):
   assert_parity({0:[1,2]},{0:[1,9]})
  with self.assertRaisesRegex(RuntimeError,"G96_RESPONSE_SET_MISMATCH"):
   assert_parity({0:[1]},{1:[1]})
 def test_cohort_phase_isolation(self):
  with self.assertRaises(ValueError):select_cohort([],"production")
  class Fake:
   @staticmethod
   def rank_original(records,n):
    return [{"instruction_sha256":str(i),"instruction":"q"+str(i),"source_row":i} for i in range(n)]
  with patch("g96_original_adapter._g95",return_value=Fake):
   dev=select_cohort([],"development");held=select_cohort([],"heldout")
   self.assertEqual([x["source_row"] for x in dev],list(range(276,288)))
   self.assertEqual([x["source_row"] for x in held],list(range(288,300)))
   self.assertFalse({x["instruction_sha256"] for x in dev}&{x["instruction_sha256"] for x in held})
 def test_budget_and_calibration_are_fail_closed(self):
  with self.assertRaises(ValueError):AdmissionCache("cost_aware")
  with self.assertRaises(ValueError):AdmissionCache("lru",byte_limit=BYTE_LIMIT+1)

if __name__=="__main__":unittest.main()
