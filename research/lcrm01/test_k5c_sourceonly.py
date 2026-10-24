"""K5C source-only frozen concurrent original MemoryEnv false-positive guards."""
import unittest
from k5c_concurrent_memory_trial import PIN,SCHEMA,METHODS,SIZES,CAPACITIES,COHORTS,frozen,judge

def rows():
 out=[]
 for size in SIZES:
  for cap in CAPACITIES:
   for seed in COHORTS["DEV"]:
    for m in METHODS:
     out.append({"size":size,"capacity":cap,"seed":seed,"policy":m,
       "real_goal_success":m in ("native_R5_slot_memory","conventional_slot_dict","semantic_rule_upper"),
       "original_terminal_reward":1. if m in ("native_R5_slot_memory","conventional_slot_dict","semantic_rule_upper") else 0.,
       "physical_steps":12,"decision_only_wall_seconds":.00001,"retained_concurrent_checkpoint_bytes":300})
 return out

class K5CFrozen(unittest.TestCase):
 def test_different_concurrent_task_and_frozen_seeds(self):
  p=frozen()
  self.assertEqual(p["new_cohorts"]["capacity_levels"],[4,8])
  self.assertEqual(COHORTS["DEV"][0],32000)
  self.assertEqual(COHORTS["CHECK"][0],31000)
  self.assertTrue(p["governance"]["preserve_K5B_and_earlier"])
 def test_equal_dictionary_is_not_new_native_architecture(self):
  v=judge(rows())
  self.assertEqual(v["result"],"BOUNDED_CONCURRENT_EPISODIC_CUE_BINDING")
  self.assertFalse(v["native_architecture_novelty_established"])
  self.assertFalse(v["scientific_accepted"])
 def test_missing_one_slot_fails(self):
  x=rows();x.pop()
  with self.assertRaises(ValueError):judge(x)
 def test_one_slot_method_and_original_r4_required(self):
  for k in ("native_R5_single_slot_ablation","original_R4_one_cue","conventional_slot_dict"):
   self.assertIn(k,METHODS)
  self.assertEqual(SCHEMA,"mass.lcrm01.k5c.original-concurrent-physical-cue-memory-v1")
 def test_no_native_progress_when_all_same_accuracy(self):
  x=rows()
  for o in x:
   if o["policy"]=="native_R5_single_slot_ablation":
    o["real_goal_success"]=True;o["original_terminal_reward"]=1.
  self.assertEqual(judge(x)["result"],"NO_QUALIFIED_CONCURRENT_EPISODIC_RETENTION")
 def test_no_auto_navigation_claim(self):
  self.assertTrue(judge(rows())["autonomous_navigation_not_tested"])
if __name__=="__main__":unittest.main()
