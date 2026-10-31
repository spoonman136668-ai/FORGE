import unittest
from g96_admission import AdmissionCache,build_traffic,traffic_digest,OVERFLOW_MARKERS,POLICIES,BYTE_LIMIT

class AdmissionPolicyTests(unittest.TestCase):
 def test_five_policies_and_frozen_limits(self):
  self.assertEqual(len(POLICIES),5)
  for policy in POLICIES:
   kw={"calibration":{"prefix_prefill_ns":10,"clone_ns":1,"expected_reuses":2}} if policy=="cost_aware" else {}
   c=AdmissionCache(policy,**kw)
   for i in range(12):c.request(str(i),BYTE_LIMIT//4,lambda i=i:i)
   self.assertLessEqual(len(c.entries),4)
   self.assertLessEqual(c.resident_bytes(),BYTE_LIMIT)
 def test_strata_determinism(self):
  for s in ("round_robin","bursty","overflow","mixed"):
   a=build_traffic(s);self.assertEqual(len(a),192)
   self.assertEqual(traffic_digest(a),traffic_digest(build_traffic(s)))
  self.assertEqual(len(OVERFLOW_MARKERS),4)
 def test_reject_unfrozen_budget_and_policy(self):
  for kw in ({"policy":"bad"},{"policy":"lru","capacity":5},{"policy":"lru","byte_limit":BYTE_LIMIT+1}):
   with self.assertRaises(ValueError):AdmissionCache(**kw)
 def test_no_cache_never_admits(self):
  c=AdmissionCache("no_cache")
  for _ in range(10):self.assertEqual(c.request("x",100,lambda:1),(None,False,False))
  self.assertEqual((c.admissions,c.hits,c.bypasses),(0,0,10))
 def test_lru_eviction_and_hit(self):
  c=AdmissionCache("lru")
  for k in "abcd":c.request(k,100,lambda k=k:k)
  self.assertEqual(c.request("a",100,lambda:None),("a",True,False))
  c.request("e",100,lambda:"e")
  self.assertEqual(c.keys(),["c","d","a","e"])
  self.assertEqual(c.evictions,1)
 def test_second_use_bypass_then_admit(self):
  c=AdmissionCache("second_use")
  self.assertEqual(c.request("x",100,lambda:1),(None,False,False))
  self.assertEqual(c.request("x",100,lambda:2),(2,False,True))
  self.assertEqual(c.request("x",100,lambda:3),(2,True,False))
 def test_frequency_protects_frequent_key(self):
  c=AdmissionCache("frequency")
  for k in "abcd":c.request(k,100,lambda k=k:k)
  for _ in range(3):c.request("a",100,lambda:"a")
  for k in "bcde":c.request(k,100,lambda k=k:k)
  self.assertIn("a",c.entries)
 def test_cost_requires_calibration(self):
  with self.assertRaises(ValueError):AdmissionCache("cost_aware")
  c=AdmissionCache("cost_aware",calibration={"prefix_prefill_ns":1,"clone_ns":20,"expected_reuses":2})
  for _ in range(3):c.request("x",100,lambda:1)
  self.assertEqual(c.admissions,0)
 def test_oversize_bypass_and_build_failure_atomic(self):
  c=AdmissionCache("lru")
  c.request("a",100,lambda:1)
  c.request("huge",BYTE_LIMIT+1,lambda:2)
  self.assertEqual(c.keys(),["a"])
  def fail():raise RuntimeError("failed build")
  with self.assertRaisesRegex(RuntimeError,"failed build"):c.request("b",100,fail)
  self.assertEqual(c.keys(),["a"])
 def test_byte_pressure_eviction(self):
  c=AdmissionCache("lru")
  c.request("a",BYTE_LIMIT//2,lambda:1)
  c.request("b",BYTE_LIMIT//2,lambda:2)
  c.request("c",BYTE_LIMIT//2,lambda:3)
  self.assertEqual(c.keys(),["b","c"])
  self.assertEqual(c.evictions,1)

if __name__=="__main__":unittest.main()
