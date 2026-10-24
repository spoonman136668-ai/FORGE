"""K5F frozen source-only external moving-obstacle causal falsification guards."""
import unittest
from k5f_dynamic_obstacles import METHODS,CONDS,SEEDS,SCHEMA,score
def fake():
 data=[]
 for family,_ in CONDS:
  for method in METHODS:
   for seed in SEEDS["DEV"]:
    data.append({"kind":family,"method":method,"seed":seed,"genuine_goal_success":False,
      "genuine_moving_obstacle_collision":method=="native_R3_unchanged",
      "real_action_steps":3,"total_original_rewards":-1. if method=="native_R3_unchanged" else 0.,
      "policy_selection_wall_seconds":.1,"policy_online_update_wall_seconds":.01})
 return data

class FrozenMovingObstacles(unittest.TestCase):
 def test_fresh_conditions_and_methods(self):
  from k5f_dynamic_obstacles import frozen
  p=frozen()
  self.assertEqual([x["n_obstacles"] for x in p["task"]["conditions"]],[2,4])
  self.assertEqual(SEEDS["DEV"][0],46200)
  self.assertEqual(p["source"]["dynamic_blob"],"68436cecc35116c23c2f196c22fa3a19c6410b95")
 def test_collisions_without_goals_cannot_pass(self):
  val=score(fake())
  self.assertEqual(val["result"],"NO_QUALIFIED_NONSTATIONARY_R3_SAFETY_ADVANCEMENT")
  self.assertFalse(val["native_architecture_superiority_established"])
  self.assertFalse(val["scientific_accepted"])
 def test_heldout_method_parity_required(self):
  a=fake();a.pop()
  with self.assertRaises(ValueError):score(a)
 def test_safety_does_not_imply_native_novelty(self):
  x=fake()
  for r in x:
   if r["method"]=="native_R3_current_front_safety_veto":
    r["genuine_goal_success"]=True
  v=score(x)
  self.assertEqual(v["result"],"BOUNDED_EXTERNAL_SENSOR_SAFETY_MITIGATION")
  self.assertFalse(v["source_native_algorithm_changed"])
  self.assertFalse(v["native_architecture_superiority_established"])
 def test_strong_comparators_exist(self):
  self.assertIn("conventional_online_optimistic_sensor_veto",METHODS)
  self.assertIn("privileged_full_grid_dynamic_replanner",METHODS)
  self.assertEqual(SCHEMA,"mass.lcrm01.k5f.original-dynamic-obstacles-public-sensor.v1")
if __name__=="__main__":unittest.main()
