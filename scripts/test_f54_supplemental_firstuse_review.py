import importlib.util,pathlib,sys,unittest
p=pathlib.Path(__file__).with_name("f54_supplemental_firstuse_review.py")
s=importlib.util.spec_from_file_location("f54_supplement",p)
m=importlib.util.module_from_spec(s);sys.modules[s.name]=m;s.loader.exec_module(m)
class ReadOnlySourceNegative(unittest.TestCase):
 def test_pins_source_isolation(self):
  self.assertEqual(m.SOURCE["Wingless"]["run"],38819060318)
  self.assertEqual(m.SOURCE["Yggdrasil"]["run"],38820489117)
  self.assertNotEqual(m.SOURCE["Wingless"]["head"],m.SOURCE["Yggdrasil"]["head"])
 def test_fail_closed(self):
  with self.assertRaises(m.Blocked):m.check(False,"STOP")
  with self.assertRaises(m.Blocked):m.unique([("x",1),("x",2)])
 def test_decoder_does_not_guess(self):
  memory=[{"from_node":2,"steps":[[0,1]],"to_node":3}]
  self.assertEqual(m.decode(memory,{"start":2,"chain":[[0,1]],"answer":3}),1)
  self.assertEqual(m.decode(memory,{"start":2,"chain":[[1,1]],"answer":3}),0)
if __name__=="__main__":unittest.main()
