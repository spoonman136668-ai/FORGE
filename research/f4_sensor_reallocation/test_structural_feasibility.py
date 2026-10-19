"""F4 source-only impossibility audit tests; no F4 development/heldout use."""
import unittest
from unittest.mock import patch

from historical_train import historical_training_cases,learn_coverage
from matched_worker import CONTROL,SET_FIXTURE,ORDER_FIXTURE
from structural_feasibility import compare_pair,review,STATUS,load_proposal

class SourceFeasibilityTests(unittest.TestCase):
    def test_actual_prospective_pairs_cannot_affect_trained_sensor_inputs(self):
        p=load_proposal()
        model=learn_coverage(historical_training_cases())
        self.assertEqual(model["learned_physical_sensors"],[8,11])
        pairs=p["proposed_conditions"]["prospective_novel_sealed_evaluation_pairs"]
        self.assertEqual(pairs,[[6,9],[12,14]])
        for swap in pairs:
            with self.subTest(swap=swap):
                for schedule in (CONTROL,SET_FIXTURE,ORDER_FIXTURE):
                    obs=compare_pair(schedule,swap)
                    self.assertFalse(obs["publicly_observable_by_schedule"])
                    self.assertEqual(obs["observed_swapped_cells"],[])
    def test_positive_control_observation_proves_gate_is_not_blanket_no(self):
        self.assertTrue(compare_pair(SET_FIXTURE,(8,10))["publicly_observable_by_schedule"])
        self.assertTrue(compare_pair(ORDER_FIXTURE,(11,13))["publicly_observable_by_schedule"])
        self.assertTrue(compare_pair(CONTROL,(2,3))["publicly_observable_by_schedule"])
    def test_negative_read_address_validation(self):
        for schedule,pair in [
            (((0,1),)*3+((2,2),(0,1)),(6,9)),
            (SET_FIXTURE,(0,9)),
            (SET_FIXTURE,(6,6)),
            (SET_FIXTURE,(12,16)),
        ]:
            with self.subTest(schedule=schedule,pair=pair):
                with self.assertRaises(ValueError):
                    compare_pair(schedule,pair)
    def test_preflight_never_admits_science(self):
        record=review()
        self.assertEqual(record["status"],STATUS)
        self.assertEqual(record["f4_original_feasibility"],"BLOCKED_AS_PROPOSED")
        self.assertEqual(record["f4_development_cohort_accesses"],0)
        self.assertEqual(record["f4_sealed_cohort_accesses"],0)
        self.assertEqual(record["first_use_claims_consumed"],0)
        self.assertFalse(record["scientific_dispatch_authorized"])
        self.assertFalse(record["candidate_retrained_after_inspecting_novel_pair_labels"])
        self.assertEqual(set(record["source_only_pair_checks"]),{"6_9","12_14"})

if __name__=="__main__":unittest.main()
