import importlib.util,pathlib,sys,unittest
path=pathlib.Path(__file__).with_name("f54_parallel_train_review.py")
spec=importlib.util.spec_from_file_location("f54_parallel",path)
m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
class F54EvidenceNegatives(unittest.TestCase):
 def test_pin_distinct_authentic_runs(self):
  self.assertEqual(m.SOURCES["Wingless"]["run"],38819060318)
  self.assertEqual(m.SOURCES["Yggdrasil"]["run"],38820489117)
  self.assertNotEqual(m.SOURCES["Wingless"]["head"],m.SOURCES["Yggdrasil"]["head"])
 def test_fail_closed_input(self):
  with self.assertRaises(m.InvalidEvidence):m.strict_pairs([("a",0),("a",1)])
  with self.assertRaises(m.InvalidEvidence):m.require(False,"UNTRUSTED")
 def test_reversible_public_witness_composition(self):
  record={"from_node":2,"to_node":4,"steps":[[0,1],[1,1]]}
  q={"start":2,"answer":4,"chain":[[0,1],[1,1]]}
  self.assertEqual(m.evaluate([record],q),1)
  q["chain"]=[[1,-1],[0,-1]];q["start"]=4;q["answer"]=2
  self.assertEqual(m.evaluate([record],q),1)
if __name__=="__main__":unittest.main()
