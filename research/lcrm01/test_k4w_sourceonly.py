"""K4W source-only adversarial protection against causal overclaiming."""
import copy
import json
import unittest
from k4w_native_failure_attribution import (
    FROZEN,FAMILIES,METHODS,fit_factors,dev_factors,SCHEMA)


def rows():
    out=[]
    for family in FAMILIES:
        for seed in range(4100,4124):
            for action in (0,1,2):
                before={"X":1,"Y":2,"GoalX":5,"GoalY":6,
                        "Direction":0,"FrontBlocked":False}
                after=dict(before)
                after["Direction"]=(action+1)%4
                out.append({"family":family,"seed":seed,"action":action,
                    "before":before,"after":after,
                    "reward":1. if action==2 and seed==4100 else 0.,
                    "terminal":action==2})
    return out

def worlds():
    source=[]
    for family in FAMILIES:
        for seed in range(6100,6108):
            for method in METHODS:
                source.append({"family":family,"seed":seed,"policy":method,
                  "first_action":seed%3,"steps":4,"real_reward":0.,
                  "success":False,
                  "actual_public_trace_sha256":"a"*64})
    return source

class ReadOnlyK4W(unittest.TestCase):
    def test_frozen_source_pins_and_nogo(self):
        pin=json.loads(FROZEN.read_text())
        self.assertEqual(pin["source"]["original_K4U_artifact_id"],12563001215)
        self.assertEqual(len(pin["source"]["members_sha256"]),5)
        self.assertEqual(pin["diagnostics"]["mandatory_verdict"].split(";")[0],
           "RETROSPECTIVE_FAILURE_FACTORS_IDENTIFIED_WITH_CAUSAL_LIMITS")
        self.assertFalse(pin["governance"]["scientific_first_use"])
        self.assertTrue(pin["governance"]["no_new_minigrid_episodes"])

    def test_reward_sparsity_counts_are_from_real_rows(self):
        table=fit_factors(rows(),expected_count=144)
        for family in FAMILIES:
            self.assertEqual(table[family]["FIT_actual_steps"],72)
            self.assertEqual(table[family]["FIT_positive_public_reward_events"],1)
            self.assertEqual(table[family]["FIT_terminal_events"],24)
            self.assertEqual(table[family]["FIT_action_counts"],{"0":24,"1":24,"2":24})
        self.assertEqual(SCHEMA,"mass.lcrm01.k4w.original-native-failure-factors-v1")

    def test_source_rewards_are_not_fabricated(self):
        source=rows()
        source[0]["reward"]=2.
        with self.assertRaises(ValueError):
            fit_factors(source,expected_count=144)

    def test_invalid_public_source_action_fails(self):
        source=rows()
        source[0]["action"]=3
        with self.assertRaises(ValueError):
            fit_factors(source,expected_count=144)

    def test_same_state_action_conflict_is_only_observation(self):
        table=fit_factors(rows(),expected_count=144)
        self.assertIn("FIT_reused_source_state_action_conflicting_results",
            table["empty"])
        self.assertTrue(table["empty"]["feature_collision_absence_does_not_prove_representation_sufficiency"])

    def test_dev_lacks_full_per_step_trace(self):
        table=dev_factors(worlds())
        self.assertEqual(table["fourrooms"]["wingless_native"]["worlds"],8)
        self.assertFalse(table["fourrooms"]["wingless_native"]["per_step_DEV_action_trace_recoverable"])

    def test_dev_policy_is_not_inferred_from_first_action(self):
        table=dev_factors(worlds())
        self.assertEqual(table["empty"]["wingless_native"]["first_action_counts"],{"0":2,"1":3,"2":3})
        self.assertEqual(table["empty"]["wingless_native"]["total_steps"],32)

    def test_missing_dev_method_fails_closed(self):
        source=worlds()
        source.pop()
        with self.assertRaises(ValueError):
            dev_factors(source)

if __name__=="__main__":
    unittest.main()
