import importlib.util
import unittest
from pathlib import Path
import torch
spec=importlib.util.spec_from_file_location("g58",Path(__file__).with_name("g58_partial_backward.py"))
g=importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)
class TestG58FrozenContract(unittest.TestCase):
 def test_four_frozen_schedules(self):
  expected={"baseline":(0,480),"top2_half":(240,240),
            "top2_two_thirds":(320,160),"top3_two_thirds":(320,160)}
  for arm,(partial,full) in expected.items():
   actual=sum(g.strategy(arm,s)[0] for s in range(g.STEPS))
   self.assertEqual((actual,g.STEPS-actual),(partial,full))
 def test_exact_prefix_cut(self):
  self.assertEqual(g.strategy("top2_half",1),(True,2))
  self.assertEqual(g.strategy("top3_two_thirds",1),(True,1))
  self.assertEqual(g.strategy("baseline",3),(False,0))
 def test_invalid_schedule_rejected(self):
  with self.assertRaises(ValueError):g.strategy("untested",0)
  with self.assertRaises(ValueError):g.strategy("baseline",-1)
  with self.assertRaises(ValueError):g.strategy("baseline",480)
 def test_seed_orders_are_permutations(self):
  self.assertEqual(set(g.ORDER),set(g.SEEDS))
  for order in g.ORDER.values():self.assertEqual(set(order),set(g.ARMS))
 def test_source_rejects_wrong_bytes(self):
  self.assertNotEqual(g.gitblob(b"tampered"),g.GIT_BLOB)
  self.assertEqual(g.gitblob(b"123"),"d800886d9c86731ae5c4a62b0b77c437015e00d2")
 def test_model_hash_pinned(self):
  self.assertEqual(g.gitblob(Path(g.original.__file__).read_bytes()),g.G57_BLOB)
 def test_gradients_truly_truncated_but_forward_matches(self):
  torch.set_num_threads(2);torch.manual_seed(2701);net=g.original.build()
  x=torch.randint(0,256,(2,48));y=torch.randint(0,256,(2,48))
  baseline=net(x,y)
  for cut in (1,2):
   net.zero_grad(set_to_none=True)
   truncated=g.partial_loss(net,x,y,cut)
   self.assertTrue(torch.allclose(baseline,truncated,atol=1e-6,rtol=1e-6))
   truncated.backward()
   self.assertIsNone(net.embedding.weight.grad)
   for i,block in enumerate(net.blocks):
    grad=next(block.parameters()).grad
    if i<cut:self.assertIsNone(grad,(cut,i))
    else:self.assertIsNotNone(grad,(cut,i))
   self.assertIsNotNone(net.head.weight.grad)
  net.zero_grad(set_to_none=True)
  baseline.backward()
  self.assertIsNotNone(net.embedding.weight.grad)
  self.assertIsNotNone(next(net.blocks[0].parameters()).grad)
 def test_sealed_split(self):
  train,val,sealed=g.original.split(b"x"*1000)
  self.assertEqual(tuple(map(len,(train,val,sealed))),(800,100,100))
if __name__=="__main__":unittest.main()
