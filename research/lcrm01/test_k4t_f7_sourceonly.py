"""Source-only F7 falsifiers: data custody, selected actions, fold segmentation."""
import unittest
from k4t_f7_delayed_value import FIT,contract,features,prior,samples,validate,clip
def pose(x):return {"X":x,"Y":4,"GoalX":6,"GoalY":4,"Direction":0,"FrontBlocked":False}
def event(seed,a,b,n,done=False,reward=0):
 return {"seed":seed,"family":"empty","action":a,"before":b,
         "after":n,"terminal":done,"reward":float(reward)}
class F7SourceOnly(unittest.TestCase):
 def test_frozen_distinct_training_only(self):
  p=contract()
  self.assertEqual(p["freshFitSeeds"],[91400,91423])
  self.assertFalse(p["governance"]["scientificFirstUse"])
  self.assertFalse(p["governance"]["scientificAccepted"])
  self.assertEqual(p["crossValidation"]["folds"],4)
  self.assertFalse(set(FIT)&set(range(83400,83408)))
 def test_episode_future_return_excludes_incomplete(self):
  rows=[event(91400,2,pose(4),pose(5)),
        event(91400,2,pose(5),pose(6),True,.9),
        event(91401,0,pose(1),pose(1))]
  scored,audit=samples(rows)
  self.assertEqual(len(scored),2)
  self.assertEqual(audit["incomplete_actual_public_events_excluded"],1)
  self.assertAlmostEqual(scored[1][1],.89)
  self.assertAlmostEqual(scored[0][1],-.01+.97*.89)
 def test_value_uses_no_unobserved_after_state(self):
  x=event(91400,2,pose(4),pose(5))
  old=features(x)
  x["after"]=pose(1)
  self.assertEqual(features(x),old)
  self.assertEqual(prior(x),("empty",2))
 def test_hidden_map_and_illegal_action_fail_closed(self):
  x=event(91400,2,pose(4),pose(5))
  x["before"]["HiddenMap"]=42
  with self.assertRaises(ValueError):validate(x)
  del x["before"]["HiddenMap"]
  x["action"]=9
  with self.assertRaises(ValueError):validate(x)
 def test_context_clip_pre_frozen(self):
  self.assertEqual(clip(100),2)
  self.assertEqual(clip(-100),-2)
if __name__=="__main__":unittest.main()
