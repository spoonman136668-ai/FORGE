"""K4Y original prospective native affordance science, source-only failure guards."""
import json
import unittest
from k4y_native_affordance import (
 FROZEN,SCHEMA,METHODS,SEEDS,STEPS,contract,report,FAMILIES)

def outcomes():
 data=[]
 for f in FAMILIES:
  for seed in SEEDS["DEV"]:
   for method in METHODS:
    trace=[{"t":0,"a":2,"before":[3,4,0,6,7,1],
      "after":[3,4,0,6,7,1],"reward":0.,"terminated":False,"truncated":False}]
    data.append({"family":f,"seed":seed,"method":method,
      "success":method=="fit_dynamics_bfs",
      "real_total_reward":1. if method=="fit_dynamics_bfs" else 0.,
      "actual_public_step_trace":trace})
 return data

class K4YSourceOnly(unittest.TestCase):
 def test_frozen_original_source_is_new(self):
  p=contract()
  self.assertEqual(p["parent"]["K4X_pr"],882)
  self.assertEqual(SEEDS["FIT"][0],11400)
  self.assertEqual(SEEDS["DEV"][-1],13407)
  self.assertEqual(len(set(SEEDS["FIT"])|set(SEEDS["DEV"])),32)
  self.assertEqual(p["design"]["legal_actions"],[0,1,2])
 def test_two_independent_source_families_and_own_r2(self):
  p=contract()
  self.assertEqual(p["source"]["wingless_R2"]["PR"],391)
  self.assertEqual(p["source"]["yggdrasil_R2"]["PR"],496)
  self.assertNotEqual(p["source"]["wingless_R2"]["blob"],
                      p["source"]["yggdrasil_R2"]["blob"])
  self.assertFalse(p["governance"]["scientific_accepted"])
 def test_false_positive_blocked_improvement_without_goal(self):
  v=report(outcomes())
  self.assertEqual(v["result"],"NO_QUALIFIED_LEARNED_AFFORDANCE_NAVIGATION_TRANSFER")
  self.assertFalse(v["all_native_cognition_criteria"])
  self.assertFalse(v["scientific_accepted"])
 def test_all_models_must_have_8_dev_worlds(self):
  data=outcomes();data.pop()
  with self.assertRaises(ValueError):report(data)
 def test_r2_cannot_be_replaced_with_r1_baseline(self):
  self.assertIn("wingless_r1",METHODS)
  self.assertIn("wingless_r2",METHODS)
  self.assertIn("yggdrasil_r1",METHODS)
  self.assertIn("yggdrasil_r2",METHODS)
  self.assertEqual(SCHEMA,"mass.lcrm01.k4y.original-public-native-affordance-evaluation.v1")
if __name__=="__main__":unittest.main()
