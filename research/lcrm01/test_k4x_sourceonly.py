"""K4X pure contract guards: no physics, no native-source modification."""
import json
import unittest
from k4x_curriculum_intervention import (
 FROZEN,protocol,CURRICULA,STEPS_PER_FAMILY,PHASE_SEEDS,
 METHODS,FAMILIES,science,SCHEMA)

def synthetic():
 rows=[]
 for family in FAMILIES:
  for seed in PHASE_SEEDS["DEV"]:
   for method in METHODS:
    rows.append({"family":family,"seed":seed,"policy":method,
     "success":method=="public_bfs_expert",
     "total_public_reward":1. if method=="public_bfs_expert" else 0.,
     "first_action":seed%3})
 return rows

class K4XSourceOnly(unittest.TestCase):
 def test_protocol_frozen_fresh_source(self):
  p=protocol()
  self.assertEqual(p["cohort"]["DEV_seeds"],{"from":9300,"to":9307})
  self.assertEqual(tuple(PHASE_SEEDS["CHECK"]),tuple(range(8300,8304)))
  self.assertEqual(STEPS_PER_FAMILY,6000)
  self.assertEqual(len(CURRICULA),2)
  self.assertTrue(p["governance"]["prior_source_artifacts_immutable"])
 def test_no_first_use_or_native_source_mutation(self):
  p=protocol()
  self.assertFalse(p["governance"]["scientific_first_use"])
  self.assertFalse(p["governance"]["scientific_accepted"])
  self.assertTrue(p["governance"]["no_undisclosed_native_edits"])
 def test_no_false_positive_for_all_native_failures(self):
  s=science(synthetic(),{})
  self.assertEqual(s["result"],"NO_QUALIFIED_CURRICULUM_RESCUE_OF_NATIVE_NAVIGATION")
  self.assertFalse(s["scientific_accepted"])
  self.assertFalse(s["native_new_architecture_discovered"])
 def test_random_curriculum_comparator_cannot_be_omitted(self):
  rows=[r for r in synthetic() if not
      r["policy"].startswith(CURRICULA[0]+"__wingless_native")]
  with self.assertRaises(ValueError):science(rows,{})
 def test_competent_expert_never_counts_as_native(self):
  s=science(synthetic(),{})
  self.assertFalse(s["teacher_FIT_learned_planner_qualified"])
  self.assertTrue(s["teacher_is_public_map_planning_extra_information"])
 def test_all_legal_public_actions(self):
  p=protocol()
  self.assertEqual(p["cohort"]["legal_actions"],[0,1,2])
  self.assertIn("wingless_native",METHODS[0])
  self.assertIn("yggdrasil_native",METHODS[1])
  self.assertEqual(SCHEMA,"mass.lcrm01.k4x.original-native-source-curriculum-study.v1")

if __name__=="__main__":
 unittest.main()
