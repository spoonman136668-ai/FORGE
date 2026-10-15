import importlib.util,pathlib,sys,unittest
p=pathlib.Path(__file__).with_name("f54_additional_two_lane_review.py")
spec=importlib.util.spec_from_file_location("f54review",p)
a=importlib.util.module_from_spec(spec);sys.modules[spec.name]=a;spec.loader.exec_module(a)
class TestF54Supplement(unittest.TestCase):
 def test_all_duplicate_keys_fail_closed(self):
  with self.assertRaises(a.Rejected):a.unique([("law",1),("law",2)])
  with self.assertRaises(a.Rejected):a.required(False,"STOP")
 def test_undoes_composed_path_orientation_correctly(self):
  rec={"from_node":1,"to_node":4,"steps":[[1,1],[2,-1]]}
  self.assertEqual(a.inverse(rec),(4,((2,1),(1,-1)),1))
 def test_public_observation_priors_are_probability(self):
  p=a.posterior([((0,0,0),0),((0,1,1),1),((1,0,0),0)],.12)
  self.assertAlmostEqual(sum(p),1)
  self.assertEqual(len(p),8)
if __name__=="__main__":unittest.main()
