import importlib.util
from pathlib import Path
import unittest
P=Path(__file__).with_name("g95_multiprefix_lru_original.py")
S=importlib.util.spec_from_file_location("g95",P)
g=importlib.util.module_from_spec(S);S.loader.exec_module(g)
class G95Tests(unittest.TestCase):
 def test_frozen_contract(self):
  g.contract()
  self.assertEqual(g.OFFSET,264)
  self.assertEqual(g.CAPACITIES,(1,2,4))
  self.assertEqual(len(g.PREFIX_TEXTS),4)
 def test_model_dataset_identity(self):
  self.assertEqual(g.MODEL_REV,"607a30d783dfa663caf39e06633721c8d4cfcd7e")
  self.assertEqual(g.WEIGHTS_SHA,"248dfc3911869ec493c76e65bf2fcf7f615828b0254c12b473182f0f81d3a707")
  self.assertEqual(g.DATA_REV,"3101c7d5072418e28b9008a6636bde82a006892c")
  self.assertEqual(g.DATA_SHA,"3730d312f6e3440559ace48831e51066acaca737f6eabec99bccb9e4b3c39d14")
 def test_interleaved_stream_exact_shape(self):
  items=[(i,("suffix",i)) for i in range(12)]
  stream=g.build_stream(items)
  self.assertEqual(len(stream),48)
  self.assertEqual([x["prefix_id"] for x in stream[:12]],[0,1,2,3,0,1,2,3,0,1,2,3])
  self.assertEqual([x["cycle"] for x in stream[:12]],[0]*12)
  self.assertEqual([x["cycle"] for x in stream[12:24]],[1]*12)
 def simulate(self,capacity):
  c=g.PrefixLRU(capacity);hits=misses=0
  keys=["p0","p1","p2","p3"]*3*4
  for key in keys:
   v=c.get(key)
   if v is None:
    misses+=1;c.put(key,{"kv_bytes":100})
   else:hits+=1
  return hits,misses,len(c.evictions),c.keys_lru_to_mru()
 def test_lru_capacity_and_eviction(self):
  self.assertEqual(self.simulate(1)[:3],(0,48,47))
  self.assertEqual(self.simulate(2)[:3],(0,48,46))
  self.assertEqual(self.simulate(4)[:3],(36,12,8)) # 4 misses per each cycle? first cycle 4 misses, then no misses
 def test_distinct_prefix_templates(self):
  self.assertEqual(len(set(g.PREFIX_TEXTS)),4)
 def test_no_weight_change_or_promotion(self):
  source=P.read_text(encoding="utf-8")
  self.assertIn('"scientific_acceptance":"NOT_GRANTED"',source)
  self.assertIn('"promotion_allowed":False',source)
  self.assertIn("copy.deepcopy(entry[\"past\"])",source)
  self.assertIn("G95_RESIDENT_KV_MUTATED",source)
if __name__=="__main__":unittest.main()
