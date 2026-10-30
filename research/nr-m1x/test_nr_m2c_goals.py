"""NR-M2C strict source-only action-selection evaluation on fixed authored data."""
import unittest

from nr_m2c_goals import (
    SOURCE_SEEDS, EIGHT_ACTIONS, PUBLIC_START_COUNT, EXPANSION_LIMIT,
    GOAL_SEQUENCES, ExactPublicTable, NoMemory,
    plan, public_effect, source_only_report, source_samples,
    true_chain, held_states
)

class SourceOnlyActionPlanning(unittest.TestCase):
    def test_model_free_planner_cannot_access_source_truth(self):
        def forbidden(_s,_a):
            return None,False
        chosen,expanded=plan(forbidden,9,14)
        self.assertIsNone(chosen)
        self.assertEqual(expanded,1)
        self.assertEqual(plan(forbidden,9,9),((),0))
        # On original source-only withheld states, exact-state count control
        # cannot invent unobserved action outcomes.
        for seed in SOURCE_SEEDS:
            first=held_states(seed)[0]
            memory=ExactPublicTable(seed)
            for action in range(3):
                self.assertEqual(memory.step(first,action),(None,False))
            self.assertEqual(NoMemory().step(first,0),(None,False))

    def test_planner_reaches_goal_without_oracle_inputs(self):
        transitions={0:{9:14,14:8},1:{14:8}}
        def known(state,action):
            if action in transitions and state in transitions[action]:
                return transitions[action][state],True
            return None,False
        goal,expanded=plan(known,9,8)
        self.assertEqual(goal,(0,0))
        self.assertLessEqual(expanded,EXPANSION_LIMIT)
        self.assertEqual(plan(known,9,42)[0],None)
        self.assertEqual(true_chain(11,9,EIGHT_ACTIONS),
                         self._manual_source_chain(11,9))

    def _manual_source_chain(self,seed,public):
        for action in EIGHT_ACTIONS:
            public=public_effect(seed,action,public)
        return public

    def test_full_source_only_strong_control_and_action_parity(self):
        result=source_only_report()
        self.assertEqual(result["schema"],"nr-m2c-source-only-matched-action-planning-v1")
        self.assertEqual(result["actual_original_world_actions"],0)
        self.assertEqual(result["predeclared_source_free_public_tasks"],64)
        self.assertEqual(len(result["regimes"]),2)
        self.assertEqual(result["total_action_choice_disagreements_strong_control"],0)
        for stage,seed in zip(result["regimes"],SOURCE_SEEDS):
            self.assertEqual(stage["source_only_regime"],seed)
            self.assertEqual(stage["heldout_public_starts"],64)
            self.assertEqual(stage["public_task_starts"],PUBLIC_START_COUNT)
            self.assertEqual(stage["source_only_reachable_public_goal_tasks"],32)
            self.assertEqual(stage["selected_action_disagreements_with_strong_fitted_R7"],0)
            self.assertTrue(stage["cold_restore_identical"])
            native=stage["arms"]["native_factor"]
            strong=stage["arms"]["strong_fitted_original_r7"]
            self.assertEqual(native["goals_reached"],strong["goals_reached"])
            self.assertEqual(native["synthetic_selected_actions"],strong["synthetic_selected_actions"])
            self.assertEqual(native["goals_reached"],32)
            self.assertEqual(native["plans"],32)
            self.assertEqual(native["eight_step_trials"],64)
            self.assertEqual(native["eight_step_correct"],64)
            self.assertEqual(native["eight_step_abstentions"],0)
            self.assertEqual(strong["eight_step_correct"],64)
            self.assertEqual(native["per_task_action_sequences"],
                             strong["per_task_action_sequences"])
            self.assertLess(native["checkpoint_bytes"],25000)
            self.assertGreater(native["planning_cost"]["cpu_ns"],0)
            self.assertGreater(strong["planning_cost"]["cpu_ns"],0)
            self.assertEqual(native["training_events_effective"],576)
            self.assertEqual(strong["training_events_effective"],576)
            self.assertEqual(stage["own_selected_events_cumulative"],576 if seed==11 else 1152)
            # This is a source-only negative control; untrained learner
            # must not hallucinate the eight-step authored transitions.
            self.assertEqual(stage["arms"]["no_memory"]["eight_step_abstentions"],64)
            self.assertEqual(stage["arms"]["exact_state_count"]["eight_step_abstentions"],64)
        print("NRM2C_SOURCE_ONLY_ACTION_GOALS_MATCH_STRONG_R7=64_OF_64")
        print("NRM2C_EIGHT_STEP_FORECASTS_MATCH_STRONG_R7=128_OF_128")
        print("NRM2C_NOT_GENUINE_ORIGINAL_WORLD_GOAL_OR_STRONG_CONTROL_SUPERIORITY")

if __name__=="__main__":
    unittest.main()
