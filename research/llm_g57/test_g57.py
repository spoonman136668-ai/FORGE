import importlib.util
import unittest
from pathlib import Path
s=importlib.util.spec_from_file_location("g57",Path(__file__).with_name("g57_train.py"))
g=importlib.util.module_from_spec(s);s.loader.exec_module(g)
class TestFrozenTrainingSchedules(unittest.TestCase):
 def test_baseline_all_layers(self):
  self.assertTrue(all(g.layers("baseline",i,1901)==(0,1,2,3) for i in range(g.STEPS)))
 def test_dropout(self):
  self.assertTrue(all(len(g.layers("layerdrop",i,1901))==3 for i in range(96)))
  self.assertTrue(all(len(g.layers("layerdrop",i,1901))==4 for i in range(96,120)))
 def test_progressive(self):
  self.assertTrue(all(len(g.layers("progressive",i,1901))==2 for i in range(54)))
  self.assertTrue(all(len(g.layers("progressive",i,1901))==4 for i in range(54,120)))
 def test_combined(self):
  self.assertTrue(all(len(g.layers("combined",i,1901))==2 for i in range(54)))
  self.assertTrue(all(len(g.layers("combined",i,1901))==3 for i in range(54,96)))
  self.assertTrue(all(len(g.layers("combined",i,1901))==4 for i in range(96,120)))
 def test_invalid(self):
  with self.assertRaises(ValueError):g.layers("invalid",0,1901)
  with self.assertRaises(ValueError):g.layers("baseline",120,1901)
 def test_splits(self):
  self.assertEqual(tuple(len(x) for x in g.split(b"a"*100)),(80,10,10))
 def test_causal_model_gradients(self):
  import torch
  torch.set_num_threads(2);torch.manual_seed(1901);net=g.build()
  x=torch.randint(0,256,(2,g.SEQ));y=torch.randint(0,256,(2,g.SEQ))
  for arm in g.ARMS:
   net.zero_grad(set_to_none=True)
   loss=net(x,y,active=g.layers(arm,0,1901))
   self.assertTrue(torch.isfinite(loss));loss.backward()
   self.assertTrue(torch.isfinite(net.embedding.weight.grad).all())
if __name__=="__main__":unittest.main()
