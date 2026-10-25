"""Original-source F8 intervention test falsifiers; synthetic only."""
import unittest
from k4t_f8_paired_actions import contract,LearnedLoggedValues,original_prefix,execute_real_arm,ACTIONS,DEV,ANCHORS
import k4t_f7_delayed_value as f7
def state(x):
 return {"X":x,"Y":4,"GoalX":6,"GoalY":4,"Direction":0,"FrontBlocked":False}
def e(seed,action,b,a,term=True,reward=.7):
 return {"family":"empty","seed":seed,"action":action,"before":b,
  "after":a,"reward":reward,"terminal":term}
class F8SourceOnly(unittest.TestCase):
 def test_source_first_new_world_and_no_native_claim(self):
  p=contract()
  self.assertEqual((DEV[0],DEV[-1]),(101400,101411))
  self.assertEqual(ANCHORS,(0,4,8,12))
  self.assertFalse(p["governance"]["scientificAccepted"])
  self.assertFalse(p["governance"]["policyActivation"])
  self.assertTrue(set(ACTIONS)=={0,1,2})
  self.assertFalse(set(DEV)&set(range(83400,83408)))
 def test_selected_action_label_model_has_no_offpolicy_rewards(self):
  stream=[]
  for seed in range(91400,91424):
   for action in ACTIONS:
    stream.append(e(seed,action,state(4),state(5)))
  learner=LearnedLoggedValues(stream)
  v=learner.values("empty",state(4))
  self.assertEqual(len(v),3)
  self.assertEqual({z["action"] for z in v},{0,1,2})
  self.assertTrue(all(z["FIT_context_count"]==24 for z in v))
 def test_six_public_fields_only(self):
  stream=[e(91400,action,state(4),state(5)) for action in ACTIONS]
  v=LearnedLoggedValues(stream)
  with self.assertRaises(ValueError):v.values("empty",{**state(4),"hiddenCausalGraph":0})
 def test_action_trials_replay_public_state_fail_closed(self):
  # No live source is used here. Assert invalid source world IDs/criteria.
  p=contract()
  self.assertEqual(p["realEpisodes"]["prefixPolicy"].split(",")[0],
    "original public BFS teacher")
  self.assertTrue(p["realEpisodes"]["testAllThreeLegalActions"])
if __name__=="__main__":unittest.main()
