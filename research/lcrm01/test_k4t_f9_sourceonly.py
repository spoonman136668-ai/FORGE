"""F9 synthetic custody falsifiers only, no source-world scientific claims."""
import unittest
from k4t_f9_randomized_value import (frozen,FIT,DEV,ANCHORS,ACTIONS,context,basis,
     IndependentlyFittedEstimators,choose)
def pub(x):
 return {"X":x,"Y":4,"GoalX":6,"GoalY":4,"Direction":0,"FrontBlocked":False}
def row(family,seed,tick,n):
 return {"family":family,"seed":seed,"anchor_tick":tick,
         "six_public_before":pub(n),"original_source_real_arms":{
          str(a):{"intervened_action":a,
           "actual_public_action_consequence_trace":[{"action":a}],
           "discounted_true_source_return":float(a==2)}
           for a in ACTIONS}}
class F9SourceOnly(unittest.TestCase):
 def test_frozen_untouched_families_and_disjoint_seeds(self):
  p=frozen()
  self.assertEqual(len(FIT),24)
  self.assertEqual(len(DEV),12)
  self.assertEqual(ANCHORS,(0,1,2,3))
  self.assertFalse(set(FIT)&set(DEV))
  self.assertFalse(set(DEV)&set(range(101400,101412)))
  self.assertIs(p["governance"]["scientificAccepted"],False)
 def test_trained_models_get_same_three_action_original_returns(self):
  training=[row(family,111400+i,i%4,i%3)
     for family in ("empty","fourrooms") for i in range(70)]
  obj=IndependentlyFittedEstimators(training)
  self.assertEqual(obj.train_actions,len(training)*3)
  prediction=obj.scored("empty",pub(4))
  self.assertEqual(len(prediction),3)
  self.assertEqual(choose(prediction,"paired_empirical_value"),2)
  self.assertEqual(choose(prediction,"fully_trained_action_return"),2)
  self.assertEqual(len(obj.linear_sha256),64)
 def test_privileged_grid_rejected(self):
  s=pub(4);s["private_world_map"]=1
  with self.assertRaises(ValueError):basis("empty",s,2)
  with self.assertRaises(ValueError):context("empty",s,1)
 def test_reject_imputed_unplayed_action(self):
  r=row("empty",111400,0,4)
  r["original_source_real_arms"]["1"]["actual_public_action_consequence_trace"][0]["action"]=2
  with self.assertRaises(ValueError):IndependentlyFittedEstimators(
    [r for _ in range(180)])
if __name__=="__main__":unittest.main()
