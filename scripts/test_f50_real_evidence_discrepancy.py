import importlib.util,pathlib,sys,unittest
path=pathlib.Path(__file__).with_name("f50_real_evidence_discrepancy.py")
spec=importlib.util.spec_from_file_location("f50_audit",path)
a=importlib.util.module_from_spec(spec);sys.modules[spec.name]=a;spec.loader.exec_module(a)
class Checks(unittest.TestCase):
 def test_unregistered_control_known_and_no_promotion(self):
  self.assertNotIn("public_tag_only",a.Y_PREREG_CONTROLS)
  self.assertEqual(a.Y["run"],38809714837)
  self.assertEqual(a.W["run"],38809539896)
 def test_recomposition_and_fail_closed(self):
  r={"public":[[i,0,i] for i in range(4)],
     "chain":[[0,1]],"start":4}
  self.assertEqual(a.compose(r,1),4)
  with self.assertRaises(a.Unsafe):a.require(False,"DENIED")
  with self.assertRaises(a.Unsafe):a.no_dup([("x",1),("x",2)])
if __name__=="__main__":unittest.main()
