import importlib.util,pathlib,sys,unittest
p=pathlib.Path(__file__).with_name("f48_real_train_review.py")
s=importlib.util.spec_from_file_location("f48_review",p)
m=importlib.util.module_from_spec(s);sys.modules[s.name]=m;s.loader.exec_module(m)
class Preflight(unittest.TestCase):
 def test_independent_authentic_real_run_pins(self):
  self.assertNotEqual(m.CATALOG["Wingless"]["sha"],m.CATALOG["Yggdrasil"]["sha"])
  self.assertEqual(m.CATALOG["Wingless"]["run"],38805703700)
  self.assertEqual(m.CATALOG["Yggdrasil"]["run"],38805887306)
 def test_duplicated_json_names_never_pass(self):
  with self.assertRaises(m.Rejected):m.strict([("scores",{}),("scores",{"evil":1})])
 def test_precheck_failure_is_closed(self):
  with self.assertRaises(m.Rejected):m.need(False,"UNTRUSTED")
if __name__=="__main__":unittest.main()
