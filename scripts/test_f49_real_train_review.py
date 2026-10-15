import importlib.util,pathlib,sys,unittest
p=pathlib.Path(__file__).with_name("f49_real_train_review.py")
s=importlib.util.spec_from_file_location("f49_audit",p)
m=importlib.util.module_from_spec(s);sys.modules[s.name]=m;s.loader.exec_module(m)
class Auditor(unittest.TestCase):
 def test_source_identity_per_lane(self):
  self.assertEqual(m.CATALOG["Wingless"]["run_id"],38807569165)
  self.assertEqual(m.CATALOG["Yggdrasil"]["run_id"],38807773617)
  self.assertNotEqual(m.CATALOG["Wingless"]["head"],m.CATALOG["Yggdrasil"]["head"])
 def test_duplicate_and_false_claims_rejected(self):
  with self.assertRaises(m.Blocked):m.no_dup([("source","one"),("source","two")])
  with self.assertRaises(m.Blocked):m.require(False,"FAIL_CLOSED")
if __name__=="__main__":unittest.main()
