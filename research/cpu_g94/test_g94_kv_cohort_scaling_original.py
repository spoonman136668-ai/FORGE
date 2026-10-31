import importlib.util
from pathlib import Path
import unittest
P=Path(__file__).with_name("g94_kv_cohort_scaling_original.py")
S=importlib.util.spec_from_file_location("g94",P)
g=importlib.util.module_from_spec(S);S.loader.exec_module(g)
class G94Tests(unittest.TestCase):
 def test_frozen(self):
  g.contract()
  self.assertEqual(g.OFFSET,252)
  self.assertEqual(g.COHORT_SIZES,(2,4,6,12))
 def test_identity(self):
  self.assertEqual(g.MODEL_REV,"607a30d783dfa663caf39e06633721c8d4cfcd7e")
  self.assertEqual(g.DATA_REV,"3101c7d5072418e28b9008a6636bde82a006892c")
 def make_arm(self,arm,n,fast):
  rows=[];hashes={}
  for i in range(12):
   row=252+i;h="h"+str(i);hashes[str(row)]=h
   base=arm=="full_prompt_all12"
   rows.append({"source_row":row,"request_wall_ns":100_000_000 if base else (50_000_000 if fast else 110_000_000),
    "prefix_share_ns":0 if base else (5_000_000 if fast else 30_000_000)})
  base=arm=="full_prompt_all12"
  return {"wall_ns":1_200_000_000 if base else (700_000_000 if fast else 1_500_000_000),
   "cpu_ns":1_000_000_000 if base else (900_000_000 if fast else 1_300_000_000),
   "prefix_setup_ns":0 if base else 50_000_000*(12//n),"rows":rows,"responses":12,
   "generated_tokens":96,"max_rss":100_000_000,"hashes":hashes}
 def fixture(self,fast):
  arms=[("full_prompt_all12",12)]+[("shared_prefix_cohort"+str(n),n) for n in g.COHORT_SIZES]
  return [{"rep":i+1,"arms":{a:self.make_arm(a,n,fast) for a,n in arms}} for i in range(g.REPEATS)]
 def test_positive_fixture(self):
  s,d=g.decide(self.fixture(True))
  self.assertEqual(d,"KV_COHORT_SCALE_PASS")
  self.assertEqual(s["timed_authentic_responses"],240)
 def test_negative_fixture(self):
  self.assertEqual(g.decide(self.fixture(False))[1],"KV_COHORT_SCALE_NO_GO")
 def test_incomplete_fails_closed(self):
  x=self.fixture(True);x[0]["arms"]["shared_prefix_cohort4"]["responses"]=11
  with self.assertRaisesRegex(RuntimeError,"G94_INCOMPLETE_COHORT"):g.decide(x)
if __name__=="__main__":unittest.main()
