"""Synthetic safety checks only; source world science requires hosted original run."""
import unittest
from k4t_f11_hard_public_memory import (
 FIT,DEV,ACTIONS,CATEGORIES,contract,category,choose_exploration,
 memory_features,history_key,FullyTrained,choose
)

def state(x=5,blocked=False,direction=0):
 return {"X":x,"Y":5,"GoalX":10,"GoalY":10,
         "Direction":direction,"FrontBlocked":blocked}
def event(a=2,b=None,n=None):
 b=b or state()
 n=n or state(6)
 return {"action":a,"physically_moved":(b["X"],b["Y"])!=(n["X"],n["Y"]),
         "front_blocked_before":b["FrontBlocked"],
         "public_before":b,"public_after":n}
def sample(i):
 s=state(i%3+5)
 hist=[event(1,s,s),event(2,s,state(s["X"]+1))]
 return {"six_public_before":s,
   "witnessed_action_consequence_history":hist,
   "public_history_counts":{"unique_observed_cells":4,
    "reentered_departed_cells":1,"failed_forward_actions":0,
    "ticks_since_last_physical_move":0},
   "true_source_three_arm_interventions":{
      str(a):{"intervened_action":a,
      "actual_public_action_consequence_trace":[{"action":a}],
      "discounted_true_source_return":float(a==1)} for a in ACTIONS}}
class SourceOnlyF11(unittest.TestCase):
 def test_seeds_and_source_policy_frozen(self):
  p=contract()
  self.assertEqual((len(FIT),len(DEV)),(48,16))
  self.assertFalse(set(FIT)&set(DEV))
  self.assertFalse(set(DEV)&set(range(141400,141412)))
  self.assertFalse(p["constraints"]["scientificAccepted"])
  self.assertEqual(CATEGORIES,("front_blocked","physical_revisit","forward_stall","goal_misaligned"))
  self.assertEqual([choose_exploration(i) for i in range(7)],[1,2,0,2,1,0,2])
 def test_real_public_difficulty_proven_by_actions(self):
  p=state(blocked=True)
  self.assertEqual(category(p,4,[],set()),"front_blocked")
  p=state()
  self.assertEqual(category(p,4,[],{(p["X"],p["Y"])}),"physical_revisit")
  still=event(2,p,p)
  self.assertEqual(category(p,5,[still,still],set()),"forward_stall")
  self.assertEqual(category(state(direction=2),4,[],set()),"goal_misaligned")
  self.assertIsNone(category(state(direction=0),1,[],set()))
 def test_only_witnessed_public_history(self):
  x=sample(0)
  assert len(memory_features(x,2))>21
  self.assertNotEqual(history_key(x,2),history_key({**x,
    "witnessed_action_consequence_history":[]},2))
  x["witnessed_action_consequence_history"][0]["hidden_map"]="private"
  with self.assertRaises(ValueError):memory_features(x,1)
 def test_false_motion_rejected(self):
  x=sample(0)
  x["witnessed_action_consequence_history"][0]["physically_moved"]=True
  with self.assertRaises(ValueError):memory_features(x,0)
 def test_all_competitors_receive_same_real_action_labels(self):
  rows=[sample(i) for i in range(115)]
  learner=FullyTrained(rows)
  self.assertEqual(learner.n,3*len(rows))
  self.assertEqual(len(learner.current_sha),64)
  self.assertEqual(len(learner.memory_sha),64)
  for model in ("current_ridge","memory_ridge","history_empirical","action_prior"):
   self.assertIn(choose(learner.score(rows[0]),model),ACTIONS)
  rows[0]["true_source_three_arm_interventions"]["0"][
    "actual_public_action_consequence_trace"][0]["action"]=1
  with self.assertRaises(ValueError):FullyTrained(rows)
if __name__=="__main__":unittest.main()
