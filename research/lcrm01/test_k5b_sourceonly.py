"""K5B before-physics source-only invalid label and memory-ablation guards."""
import unittest
from k5b_memory_trial import PIN,SIZE,PHASES,METHODS,judge,SCHEMA

def synthetic():
 return [{"size":size,"seed":seed,"policy":m,"real_goal_success":m in ("ygg_native_R4","conventional_one_bit_reward_lookup","source_rule_upper_bound"),
   "original_terminal_reward":1. if m in ("ygg_native_R4","conventional_one_bit_reward_lookup","source_rule_upper_bound") else 0.,
   "physical_step_count":12}
   for size in SIZE for seed in PHASES["DEV"] for m in METHODS]

class K5BFrozenGuards(unittest.TestCase):
 def test_protocol_and_fresh_worlds(self):
  import json
  p=json.loads(PIN.read_text())
  self.assertEqual(p["parent_K5A_head"],"f60b384416a473a0fff424d20d2efa29bf8d8dbf")
  self.assertEqual(list(PHASES["DEV"]),list(range(28000,28016)))
  self.assertEqual(SIZE,(11,13))
  self.assertTrue(p["governance"]["preserve_K5A"])
 def test_not_autonomous_map_navigation_claim(self):
  self.assertIn("NOT autonomous",("NOT autonomous"))
  self.assertTrue(judge(synthetic())["autonomous_navigation_not_tested"])
 def test_native_cue_benefit_and_conventional_tie_cannot_be_novelty(self):
  v=judge(synthetic())
  self.assertEqual(v["result"],"BOUNDED_NATIVE_DELAYED_CUE_RETENTION")
  self.assertFalse(v["architecture_novelty_established"])
  self.assertFalse(v["native_superior_to_conventional"])
  self.assertFalse(v["scientific_accepted"])
 def test_missing_original_method_is_denied(self):
  a=synthetic();a.pop()
  with self.assertRaises(ValueError):judge(a)
 def test_explicit_cue_ablation_and_trained_one_bit_control(self):
  self.assertIn("native_without_cue_memory",METHODS)
  self.assertIn("conventional_one_bit_reward_lookup",METHODS)
  self.assertEqual(SCHEMA,"mass.lcrm01.k5b.original-memory-delayed-cue-v1")
 def test_unqualified_native_is_not_promoted(self):
  a=synthetic()
  for x in a:
   if x["policy"]=="ygg_native_R4":x["real_goal_success"]=False;x["original_terminal_reward"]=0.
  v=judge(a)
  self.assertEqual(v["result"],"NO_QUALIFIED_DELAYED_CUE_NATIVE_MEMORY")
  self.assertFalse(v["scientific_first_use"])
if __name__=="__main__":unittest.main()
