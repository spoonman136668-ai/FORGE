import importlib.util,pathlib,sys,unittest
p=pathlib.Path(__file__).with_name("f52_two_lane_review.py")
s=importlib.util.spec_from_file_location("f52_auditor",p)
m=importlib.util.module_from_spec(s);sys.modules[s.name]=m;s.loader.exec_module(m)
class F52(unittest.TestCase):
 def test_authentic_distinct_source(self):
  self.assertEqual(m.PINS["Wingless"]["run"],38815134108)
  self.assertEqual(m.PINS["Yggdrasil"]["run"],38815175032)
  self.assertNotEqual(m.PINS["Wingless"]["head"],m.PINS["Yggdrasil"]["head"])
 def test_no_unsafe_parser_drift(self):
  with self.assertRaises(m.Rejected):m.unique([("policy","allowed"),("policy","injected")])
  with self.assertRaises(m.Rejected):m.demand(False,"STOP")
 def test_public_composition_and_nonoracle_memory(self):
  self.assertEqual(m.traverse([[0,0,1]],[[0,1]],3,1),4)
  events=[[2,0,3,0],[3,1,4,1]]
  self.assertEqual(m.solve(events,[0,1],{"start":2,"chain":[[0,1],[1,1]]}),4)
  self.assertIsNone(m.solve(events,[0],{"start":2,"chain":[[0,1],[1,1]]}))
if __name__=="__main__":unittest.main()
