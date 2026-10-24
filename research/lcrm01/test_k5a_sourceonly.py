"""K5A source-only immutable new-family, ablation, and false-positive tests."""
import unittest
from k5a_crossing_transfer import (
 frozen,METHODS,TASKS,PHASES,evaluate,SCHEMA)

def rows():
 data=[]
 for kind,_ in TASKS:
  for seed in PHASES["DEV"]:
   for name in METHODS:
    data.append({"kind":kind,"seed":seed,"policy":name,
      "actual_goal_success":name in ("conventional_fit_model_bfs","public_bfs_upper"),
      "real_reward":1. if name in ("conventional_fit_model_bfs","public_bfs_upper") else 0.,
      "steps":1,"blocked_forward":0,
      "policy_inference_wall_seconds":.1,"policy_online_adaptation_wall_seconds":.1,
      "learned_episode_graph_snapshot_bytes":10})
 return data

class SourceOnlyK5A(unittest.TestCase):
 def test_new_family_and_old_experiments_preserved(self):
  p=frozen()
  self.assertEqual(p["source"]["crossing_blob"],"f8c331e5e0e56b3b2a4a3b44dda8533bdabf4272")
  self.assertEqual({n for n,_ in TASKS},{"crossing_1","crossing_3"})
  self.assertEqual(PHASES["DEV"][0],21500)
  self.assertTrue(p["governance"]["original_K4Z_science_immutable"])
  self.assertFalse(p["protocol"]["scientific_accepted"])
 def test_not_a_native_fully_observable_oracle(self):
  p=frozen()
  self.assertIn("never maps,walls,seed",p["unfamiliar_environment"]["public_source"])
  self.assertEqual(p["unfamiliar_environment"]["action_menu"],[0,1,2])
 def test_conventional_full_map_success_cannot_falsely_qualify_native(self):
  out=evaluate(rows())
  self.assertEqual(out["disposition"],"NO_QUALIFIED_CROSSING_TOPOLOGY_TRANSFER")
  self.assertTrue(out["frozen_primary_tests"]["full_public_planner_qualified_both"])
  self.assertTrue(out["native_unfamiliar_abstract_architecture_novelty_not_established"])
 def test_requires_all_disjoint_new_heldout_seeds(self):
  data=rows();data.pop()
  with self.assertRaises(ValueError):evaluate(data)
 def test_distinct_causal_graph_and_local_ablation(self):
  for name in ("ygg_R3_no_episodic_edges","ygg_R3_no_R2_local","ygg_R2_static",
               "conventional_online_optimistic","ygg_R3_intact"):
   self.assertIn(name,METHODS)
 def test_zero_positive_does_not_count_as_transfer(self):
  v=evaluate(rows())
  self.assertEqual(v["native_vs_online_real_goal_delta"],0)
  self.assertEqual(SCHEMA,"mass.lcrm01.k5a.original-crossing-zero-shot-transfer.v1")

if __name__=="__main__":unittest.main()
