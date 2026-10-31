"""NR-M2F source-only equal-data negative-control experiment.

Prospectively fixed in NR_M2F_CONTROL_PREREG.json before code. This test
uses no MiniGrid engine or original-world actions, just authored valid public
frames under exact original R10/R18/MG19 source admission.
"""
import hashlib
import json
import time
import unittest

from nr_m2d_pinned_original_public import MISSION
from nr_m2e_extended_public import full_public, GOAL_MISSION
from nr_m2f_predictive import SelectedPublicPredictor
from nr_m2f_equal_data_control import EqualDataCategorical

MISSIONS = (MISSION, GOAL_MISSION, "pick up the red ball")
ACTIONS = tuple(range(7))
DIRECTIONS = tuple(range(4))

def frame(mission, direction):
    return {"image": [[[1, 0, 0] for _ in range(7)] for _ in range(7)],
            "direction": direction, "mission": mission}

def authored_return(before, action):
    # Explicitly synthetic evaluation rule. Not exposed to either predictor.
    returned = json.loads(json.dumps(before))
    if action not in (0, 1):
        returned["image"][0][0] = [1, action % 6, action]
    return full_public(returned)

def comparison():
    learner = SelectedPublicPredictor(full_public)
    control = EqualDataCategorical(full_public)
    cases = [(frame(mission, direction), action)
             for mission in MISSIONS for direction in DIRECTIONS for action in ACTIONS]
    start = time.process_time()
    for before, action in cases:
        after = authored_return(before, action)
        for _ in range(2):
            learner.begin(before)
            learner.select(before, action)
            learner.feedback(before, action, after)
            # The comparator receives ONLY this already-selected actual outcome.
            control.observe_selected(before, action, after)
    fit_cpu_seconds = time.process_time() - start
    matched = correct_candidate = correct_control = same_support = 0
    no_effect_matched = 0
    start = time.process_time()
    for before, action in cases:
        predicted, support = learner.predict(before, action)
        baseline, baseline_support = control.predict(before, action)
        expected = authored_return(before, action)
        matched += (predicted == baseline and support == baseline_support)
        correct_candidate += predicted == expected
        correct_control += baseline == expected
        same_support += support["supported"] == baseline_support["supported"]
        no_effect_matched += support["no_effect"] == (action in (0,1))
    query_cpu_seconds = time.process_time() - start
    unseen_matched = 0
    for action in ACTIONS:
        unseen = frame(MISSIONS[0], 0)
        unseen["image"][6][6] = [2, 4, 0]
        candidate, candidate_ev = learner.predict(unseen, action)
        reference, reference_ev = control.predict(unseen, action)
        unseen_matched += (candidate is None and reference is None and
                           not candidate_ev["supported"] and not reference_ev["supported"])
    before = frame(MISSIONS[0], 0)
    alternative = authored_return(before, 2)
    alternative["image"][0][0] = [1, 3, 2]
    learner.begin(before)
    learner.select(before, 2)
    learner.feedback(before, 2, alternative)
    control.observe_selected(before, 2, alternative)
    a, ae = learner.predict(before, 2)
    b, be = control.predict(before, 2)
    contradictions_abstain = a is None and b is None and not ae["supported"] and not be["supported"]
    snap = learner.checkpoint()
    restored = SelectedPublicPredictor.restore(full_public, snap, hashlib.sha256(snap).hexdigest())
    return {
        "schema": "nr-m2f-equal-data-control.source-only-result.v1",
        "source_only_no_minigrid_steps": True,
        "fit_events_per_arm": 2 * len(cases),
        "evaluation_queries": len(cases),
        "prediction_parity": matched,
        "candidate_correct": correct_candidate,
        "control_correct": correct_control,
        "support_parity": same_support,
        "no_effect_detected": no_effect_matched,
        "unseen_abstention_parity": unseen_matched,
        "contradiction_both_abstain": contradictions_abstain,
        "candidate_restored_exact": restored.checkpoint() == snap,
        "candidate_checkpoint_bytes": len(snap),
        "control_retained_events": len(control.events),
        "fit_process_cpu_seconds": fit_cpu_seconds,
        "query_process_cpu_seconds": query_cpu_seconds,
        "scientific_conclusion": "NO_UNIQUE_CAUSAL_ADVANTAGE_SOURCE_ONLY_PARITY"
    }

class EqualInputControlTest(unittest.TestCase):
    def test_frozen_source_only_equal_data_control(self):
        result = comparison()
        self.assertEqual(result["fit_events_per_arm"], 168)
        self.assertEqual(result["evaluation_queries"], 84)
        self.assertEqual(result["prediction_parity"], 84)
        self.assertEqual(result["candidate_correct"], 84)
        self.assertEqual(result["control_correct"], 84)
        self.assertEqual(result["support_parity"], 84)
        self.assertEqual(result["no_effect_detected"], 84)
        self.assertEqual(result["unseen_abstention_parity"], 7)
        self.assertTrue(result["contradiction_both_abstain"])
        self.assertTrue(result["candidate_restored_exact"])
        self.assertEqual(result["control_retained_events"], 169)
        print("NRM2F_EQUAL_INPUT_SOURCE_ONLY_NEGATIVE_CONTROL_PASS")
        print(json.dumps(result, sort_keys=True))

if __name__ == "__main__":
    unittest.main()
