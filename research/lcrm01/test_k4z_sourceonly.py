"""K4Z source-only original scientific and action-availability guards."""
import unittest
from k4z_episodic_navigation import SEEDS,METHODS,frozen,qualify,OnlinePlanner,SCHEMA,FAMILIES
def fake():
 out=[]
 for f in FAMILIES:
  for seed in SEEDS["DEV"]:
   for m in METHODS:
    out.append({"family":f,"seed":seed,"method":m,
      "real_success":m=="learned_dynamics_bfs_fit",
      "real_reward":1. if m=="learned_dynamics_bfs_fit" else 0.,
      "steps":1,
      "complete_public_action_trace":[{"a":2,"b":[2,2,0,1]}]})
 return out

class K4ZScienceGuards(unittest.TestCase):
 def test_frozen_preexisting_negative_and_disjoint_cohorts(self):
  p=frozen()
  self.assertEqual(p["K4Y_PR"],885)
  self.assertEqual(SEEDS["FIT"][0],17400)
  self.assertEqual(SEEDS["CHECK"][0],18400)
  self.assertEqual(SEEDS["DEV"][0],19400)
  self.assertTrue(p["governance"]["all_original_negatives_preserved"])
  self.assertFalse(p["governance"]["scientific_accepted"])
 def test_bad_source_lacks_sufficient_success(self):
  v=qualify(fake())
  self.assertEqual(v["result"],"NO_QUALIFIED_NATIVE_EPISODIC_PLANNING_TRANSFER")
  self.assertFalse(v["scientific_accepted"])
  self.assertTrue(v["frozen_scientific_tests"]["original_conventional_planner_qualified"])
 def test_independent_online_planner_public_only(self):
  class G:
   x=3;y=4;goal_x=6;goal_y=4;direction=0
  p=OnlinePlanner({"0":[1,0],"1":[0,1],"2":[-1,0],"3":[0,-1]})
  p.reset(8,8)
  self.assertEqual(p.choose(G),2)
  a=type("X",(),{"x":3,"y":4,"direction":0})()
  p.observe(a,2,a)
  self.assertIn((3,4,0),p.blocked)
  self.assertNotEqual(p.choose(G),2)
 def test_real_fourrooms_attribution_cannot_be_approximated_from_bfs(self):
  q=fake()
  self.assertEqual(qualify(q)["original_DEVELOPMENT_family_results"]["fourrooms"]["ygg_R3_episodic"]["actual_goals"],0)
  q.pop()
  with self.assertRaises(ValueError):qualify(q)
 def test_preserve_native_and_online_matched_controls(self):
  for m in ("ygg_R2_static","ygg_R3_episodic","online_optimistic_planner","learned_dynamics_bfs_fit"):
   self.assertIn(m,METHODS)
  self.assertEqual(SCHEMA,"mass.lcrm01.k4z.original-online-causal-navigation-v1")
if __name__=="__main__":unittest.main()
