"""K4E preregistration integrity and causal ablation source-only adversarial tests."""
import copy
import hashlib
import json
import unittest
from types import SimpleNamespace

import numpy as np

from k4e_reward_ablation import (
    FROZEN,SCHEMA,BASE,REPAIR,ExperimentFailure,cases,
    memory_snapshot,memory_restore,first_difference)
from k4e_compare import compare_reports

FIELDS=["previous_end_effector_positions","previous_object_position",
        "previous_object_orientation"]

def results():
    f=json.loads(FROZEN.read_text())
    rows=[]
    for spec in cases(f):
        for arm in (BASE,REPAIR):
            rows.append({"case":spec,"arm":arm,
                         "status":"BASELINE_REWARD_DRIFT" if arm==BASE else "REPAIR_ALL_CHECKS_PASS",
                         "control_mismatch":{"step":0,"fields":["reward"]} if arm==BASE else None})
    a={"schema":SCHEMA,"gate":"LCRM01-K4E","cases":rows,
       "result":"HYPOTHESIS_SUPPORTED_FOR_FROZEN_DEV_CASES",
       "protocol_sha256":hashlib.sha256(FROZEN.read_bytes()).hexdigest(),
       "source_sha":f["source"]["commit"],
       "K4D_negative_preserved":True,"scientific_first_use":False,
       "scientific_accepted":False,"learned_transfer":False,
       "dispatch_authorized":False}
    return a,copy.deepcopy(a)

class K4EFrozenTests(unittest.TestCase):
    def test_frozen_new_seeds_no_retrospective_replay(self):
        cs=cases(json.loads(FROZEN.read_text()))
        self.assertEqual(len(cs),4)
        self.assertEqual({c["seed"] for c in cs},{67,79})
        self.assertNotIn(41,{c["seed"] for c in cs})
        self.assertEqual({c["joint_index"] for c in cs},{0,2})

    def test_memory_snapshot_is_deep_copy(self):
        t=SimpleNamespace(
            previous_end_effector_positions=np.ones((3,3)),
            previous_object_position=np.array([1.,2.,3.]),
            previous_object_orientation=np.array([0.,0.,0.,1.]))
        saved=memory_snapshot(t,FIELDS)
        t.previous_object_position[0]=12
        self.assertEqual(saved["previous_object_position"][0],1)
        memory_restore(t,saved)
        self.assertEqual(float(t.previous_object_position[0]),1)

    def test_unrecognized_memory_field_denied(self):
        t=SimpleNamespace(previous_end_effector_positions=np.zeros((3,3)))
        with self.assertRaises(ExperimentFailure):
            memory_snapshot(t,["previous_end_effector_positions","hidden_label"])

    def test_absent_reward_history_denied(self):
        t=SimpleNamespace(previous_end_effector_positions=np.zeros((3,3)),
                          previous_object_position=np.zeros(3))
        with self.assertRaises(ExperimentFailure):
            memory_snapshot(t,FIELDS)

    def test_uninitialized_reward_memory_denied(self):
        t=SimpleNamespace(previous_end_effector_positions=np.zeros((3,3)),
                          previous_object_position=None,
                          previous_object_orientation=np.zeros(4))
        with self.assertRaises(ExperimentFailure):
            memory_snapshot(t,FIELDS)

    def test_only_reward_mismatch_is_detected(self):
        a=[{"reward":1,"world_state":"same"},{"reward":2,"world_state":"same"}]
        b=[{"reward":0,"world_state":"same"},{"reward":2,"world_state":"same"}]
        self.assertEqual(first_difference(a,b),{"step":0,"fields":["reward"]})
        b[0]["world_state"]="changed"
        self.assertEqual(first_difference(a,b)["fields"],["reward","world_state"])

    def test_compare_two_identical_bounded_results(self):
        a,b=results()
        x=compare_reports(a,b)
        self.assertEqual(x["result"],"SUPPORTED_BOUNDED_DEV_CAUSE")
        self.assertFalse(x["scientific_accepted"])

    def test_cross_process_digest_disagreement_blocks(self):
        a,b=results()
        b["cases"][0]["control_mismatch"]["step"]=1
        x=compare_reports(a,b)
        self.assertEqual(x["result"],"NOT_QUALIFIED_RETAIN_ORIGINAL_FINDINGS")
        self.assertEqual(x["mismatches"][0]["index"],0)

    def test_forged_science_acceptance_denied(self):
        a,b=results()
        b["scientific_accepted"]=True
        with self.assertRaises(ValueError):
            compare_reports(a,b)

    def test_forged_original_negative_loss_denied(self):
        a,b=results()
        b["K4D_negative_preserved"]=False
        with self.assertRaises(ValueError):
            compare_reports(a,b)

    def test_missing_arm_denied(self):
        a,b=results()
        b["cases"].pop()
        with self.assertRaises(ValueError):
            compare_reports(a,b)

    def test_science_disposition_cannot_claim_support_from_failure(self):
        a,b=results()
        b["cases"][1]["status"]="NEGATIVE"
        with self.assertRaises(ValueError):
            compare_reports(a,b)

if __name__=="__main__":
    unittest.main()
