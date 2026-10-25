"""F10 source-only falsifiers. Synthetic fixtures are never science."""
import unittest
from k4t_f10_public_history import (frozen,FIT,DEV,ANCHORS,HISTORY,ACTIONS,
                                    hvec,history_key,extended_features,Models,argmax)
def public(x=3):
 return {"X":x,"Y":4,"GoalX":10,"GoalY":10,"Direction":0,"FrontBlocked":False}
def event(a=2,moved=True,blocked=False):
 return {"action":a,"physically_moved":moved,"previous_front_blocked":blocked}
def example(i):
 return {"family":"fourrooms","seed":FIT[0]+i,"anchor_tick":ANCHORS[i%8],
   "six_public_before":public(i%4+3),
   "recent_public_history":[event(0),event(1),event(2)],
   "true_original_interventions":{str(a):{
     "intervened_action":a,"actual_public_action_consequence_trace":[{"action":a}],
     "discounted_true_source_return":float(a==0)} for a in ACTIONS}}
class PublicHistoryUnit(unittest.TestCase):
 def test_source_first_freeze_isolated(self):
  p=frozen()
  self.assertEqual(len(FIT),36)
  self.assertEqual(len(DEV),12)
  self.assertEqual(len(ANCHORS),8)
  self.assertFalse(set(FIT)&set(DEV))
  self.assertFalse(set(DEV)&set(range(121400,121412)))
  self.assertFalse(p["governance"]["protectedFirstUse"])
 def test_history_is_past_selected_public_consequence_only(self):
  hist=[event(0,False,True),event(1,False,False),event(2,True,False)]
  s=example(0)
  s["recent_public_history"]=hist
  self.assertEqual(len(hvec(hist)),HISTORY*6)
  self.assertEqual(len(extended_features(s,2)),39)
  self.assertNotEqual(history_key(s,2),history_key({**s,"recent_public_history":[event(2)]},2))
 def test_nothing_in_history_can_be_private_map(self):
  with self.assertRaises(ValueError):hvec([event(9)])
  bad=example(0)
  bad["six_public_before"]["privileged_world_map"]="secret"
  with self.assertRaises(ValueError):extended_features(bad,2)
 def test_both_learned_models_receive_same_true_arm_labels(self):
  records=[example(i) for i in range(110)]
  learned=Models(records)
  self.assertEqual(learned.n,3*len(records))
  self.assertEqual(len(learned.sha_current),64)
  self.assertEqual(len(learned.sha_history),64)
  scores=learned.scores(example(0))
  self.assertEqual(len(scores),3)
  self.assertIn(argmax(scores,"history_public_ridge"),ACTIONS)
 def test_cannot_admit_unexecuted_action_as_training(self):
  training=[example(i) for i in range(110)]
  training[0]["true_original_interventions"]["1"]["actual_public_action_consequence_trace"][0]["action"]=0
  with self.assertRaises(ValueError):Models(training)
if __name__=="__main__":unittest.main()
