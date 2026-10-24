"""K5G source-only matched front-bit budget and false-positive guards."""
import unittest
from k5g_active_sensing import frozen,SCHEMA,BUDGETS,CONDITIONS,METHODS,SEEDS,aggregate,policy_input

def fake():
 data=[]
 for budget in BUDGETS:
  for kind,_ in CONDITIONS:
   for method in METHODS:
    for seed in SEEDS["DEV"]:
     data.append({"budget":budget,"condition":kind,"policy":method,"seed":seed,
       "true_original_goals":False,"true_original_collision_termination":True,
       "physical_action_count":1,"metered_onebit_queries":budget,
       "policy_decision_wall_seconds":.001,"policy_adaptation_wall_seconds":.001,
       "original_reward_total":-1.})
 return data

class FrozenK5G(unittest.TestCase):
 def test_custody_and_two_budgets(self):
  p=frozen()
  self.assertEqual(p["parent_K5F_head"],"e5dc5a21c889dd7638cf8678a1b834c4793f7da2")
  self.assertEqual(BUDGETS,(6,12))
  self.assertEqual(SEEDS["DEV"][0],48200)
  self.assertFalse(p["governance"]["scientific_accepted"])
 def test_no_unsampled_front_bit(self):
  pose={"X":1,"Y":2,"Direction":0,"FrontBlocked":True}
  self.assertFalse(policy_input(pose,{})["FrontBlocked"])
  self.assertTrue(policy_input(pose,{(1,2,0):(0,True)})["FrontBlocked"])
  self.assertFalse(policy_input(pose,{(1,2,0):(0,False)})["FrontBlocked"])
 def test_no_false_qualification_from_full_sensor(self):
  rows=fake()
  for r in rows:
   if r["policy"]=="native_R3_full_sensor_upper":r["true_original_goals"]=True
  v=aggregate(rows)
  self.assertEqual(v["result"],"NO_QUALIFIED_ACTIVE_CAUSAL_SENSING_ADVANTAGE")
  self.assertFalse(v["native_architecture_novelty_established"])
 def test_bounded_active_never_implies_native_novelty(self):
  rows=fake()
  for r in rows:
   if r["policy"]=="native_R3_active_uncertainty_scan":
    r["true_original_goals"]=True;r["true_original_collision_termination"]=False
  v=aggregate(rows)
  self.assertEqual(v["result"],"BOUNDED_ACTIVE_ONEBIT_SENSING_SAFETY_GAIN")
  self.assertFalse(v["new_native_learning_architecture_demonstrated"])
  self.assertFalse(v["scientific_accepted"])
 def test_all_methods_and_budget_parity(self):
  r=fake();r.pop()
  with self.assertRaises(ValueError):aggregate(r)
  r=fake();r[0]["metered_onebit_queries"]=99
  with self.assertRaises(ValueError):aggregate(r)
 def test_explicit_competent_conventional_controls(self):
  self.assertIn("conventional_online_active_uncertainty_scan",METHODS)
  self.assertIn("conventional_online_periodic_forward_scan",METHODS)
  self.assertEqual(SCHEMA,"mass.lcrm01.k5g.original-limited-active-onebit-scans.v1")
if __name__=="__main__":unittest.main()
