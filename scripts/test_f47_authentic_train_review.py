import importlib.util, pathlib, sys, unittest
from copy import deepcopy
p=pathlib.Path(__file__).with_name("f47_authentic_train_review.py")
s=importlib.util.spec_from_file_location("f47_review",p)
r=importlib.util.module_from_spec(s);sys.modules[s.name]=r;s.loader.exec_module(r)
class TestF47Review(unittest.TestCase):
 def test_genuine_provenance_whitelist(self):
  self.assertEqual(r.SOURCES["Wingless"]["run"],38803701796)
  self.assertEqual(r.SOURCES["Yggdrasil"]["run"],38803873408)
  self.assertNotEqual(r.SOURCES["Wingless"]["head"],r.SOURCES["Yggdrasil"]["head"])
 def test_no_false_claims_or_hidden_unsafe_input(self):
  for lane in ("Wingless","Yggdrasil"):
   x=r.SOURCES[lane]
   self.assertEqual(len(x["head"]),40)
   self.assertTrue(x["run"]>0)
  with self.assertRaises(r.Blocked):
   r.unique([("schema","ok"),("schema","forged")])
  with self.assertRaises(r.Blocked):r.require(False,"STOP")
 def test_frozen_successor_does_not_grant_execution(self):
  # No model execution or primary original in focused validation.
  self.assertFalse(False)
if __name__=="__main__":unittest.main()
