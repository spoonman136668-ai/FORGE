"""F139/CKAD source and checkpoint continuity regression; no model training."""
from __future__ import annotations
import copy
import hashlib
import unittest

from f139.ckad_stage_custody import (
    SCHEMA, SOURCE_REPO, SOURCE_MAIN, CKAD12_SHA, CKAD12_TREE,
    CustodyDenied, audit_chain, digest, plan_digest, receipt_digest, seal_stage,
)

def mock_plan(initial):
    return {
        "schema": SCHEMA, "source_repo": SOURCE_REPO,
        "accepted_main": SOURCE_MAIN, "candidate_sha": CKAD12_SHA,
        "candidate_tree": CKAD12_TREE,
        "native_architecture": "yggdrasil-native-tokenless",
        "source_mode": "previously-consumed-synthetic-only",
        "initial_checkpoint_sha256": digest(initial),
        "frozen_prereg_sha256": "a"*64,
        "frozen_controls_sha256": "b"*64,
        "frozen_split_sha256": "c"*64,
        "seeds": [101, 202, 303],
        "stages": [
            {"id": "learn-a", "phase": "learn",
             "component": "yggdrasil.native_context_basis.NativeContextBasis",
             "max_observations": 512, "max_interventions": 0,
             "max_cpu_seconds": 120},
            {"id": "evaluate-b", "phase": "evaluate",
             "component": "yggdrasil.native_context_basis.NativeContextBasis",
             "max_observations": 512, "max_interventions": 0,
             "max_cpu_seconds": 120},
            {"id": "repair-c", "phase": "repair",
             "component": "yggdrasil.native_intervention_repair.NativeInterventionRepair",
             "max_observations": 64, "max_interventions": 16,
             "max_cpu_seconds": 120},
        ], "scientific_first_use": False,
        "training_execution_authorized": False,
    }

def stage(plan, prev, a, b, i):
    return seal_stage(
        plan, prev, stage_index=i, checkpoint_input=a, checkpoint_output=b,
        evidence_bytes=("source-view-%s"%i).encode(),
        control_receipt_bytes=("independent-control-%s"%i).encode(),
        evaluation_receipt_bytes=("frozen-eval-%s"%i).encode(),
        observations=4, interventions=0, cpu_seconds=8)

class CkadHandoffTests(unittest.TestCase):
    def setUp(self):
        self.initial=b"native-checkpoint-v0"
        self.plan=mock_plan(self.initial)

    def test_two_stage_state_is_reused_and_immutable(self):
        a=stage(self.plan, [], self.initial,b"native-checkpoint-v1",0)
        b=stage(self.plan, [a],b"native-checkpoint-v1",
                b"native-checkpoint-v1",1)
        c=stage(self.plan,[a,b],b"native-checkpoint-v1",
                b"native-checkpoint-v2",2)
        summary=audit_chain(self.plan,[a,b,c])
        self.assertEqual(summary["completed_stages"],3)
        self.assertEqual(summary["current_checkpoint_sha256"],
                         digest(b"native-checkpoint-v2"))
        self.assertFalse(summary["scientific_pass"])
        self.assertFalse(summary["execution_authorized"])
        self.assertFalse(b["checkpoint_changed"])
        self.assertTrue(c["checkpoint_changed"])

    def test_cold_reset_replay_and_reordered_stages_denied(self):
        a=stage(self.plan,[],self.initial,b"v1",0)
        with self.assertRaises(CustodyDenied):
            stage(self.plan,[a],self.initial,b"fresh-reset",1)
        with self.assertRaises(CustodyDenied):
            stage(self.plan,[a],b"v1",b"v2",0)
        with self.assertRaises(CustodyDenied):
            stage(self.plan,[],b"v1",b"v2",1)
        self.assertEqual(audit_chain(self.plan,[a])["completed_stages"],1)
        # A stored/pinned receipt head prevents a changed terminal record.
        self.assertEqual(
            audit_chain(self.plan,[a],
                        expected_head_receipt_sha256=receipt_digest(a))
            ["completed_stages"], 1)

    def test_changed_source_tree_seed_budget_control_or_training_authority_denied(self):
        for key,value in (
                ("candidate_tree","0"*40),
                ("candidate_sha","0"*40),
                ("accepted_main","0"*40),
                ("source_mode","original-scientific"),
                ("scientific_first_use",True),
                ("training_execution_authorized",True),
                ("seeds",[101,101]),
                ("frozen_controls_sha256","broken")):
            changed=copy.deepcopy(self.plan)
            changed[key]=value
            with self.subTest(key=key),self.assertRaises(CustodyDenied):
                plan_digest(changed)
        broken=copy.deepcopy(self.plan)
        broken["stages"][0]["max_cpu_seconds"]=3601
        with self.assertRaises(CustodyDenied):
            plan_digest(broken)

    def test_tampered_previous_receipt_or_checkpoint_denied(self):
        a=stage(self.plan,[],self.initial,b"v1",0)
        cases=[
            {"input_checkpoint_sha256": "0"*64},
            {"output_checkpoint_sha256": "0"*64},
            {"prior_receipt_sha256": "0"*64},
            {"scientific_pass": True},
            {"training_executed_by_forge": True},
            {"stage_index": 1},
            {"source_tree": "1"*40},
            {"cpu_seconds_reported": 1000},
        ]
        for change in cases:
            item=dict(a,**change)
            with self.subTest(change=change),self.assertRaises(CustodyDenied):
                audit_chain(
                    self.plan,[item],
                    expected_head_receipt_sha256=receipt_digest(a))
        with self.assertRaises(CustodyDenied):
            stage(self.plan,[dict(a,**{"output_checkpoint_sha256":"f"*64})],
                  b"v1",b"v2",1)

    def test_custody_bytes_are_hashed_and_not_embedded(self):
        a=stage(self.plan,[],self.initial,b"v1",0)
        self.assertEqual(a["evidence_sha256"],digest(b"source-view-0"))
        self.assertEqual(a["control_receipt_sha256"],
                         digest(b"independent-control-0"))
        self.assertEqual(a["input_checkpoint_sha256"],digest(self.initial))
        self.assertNotIn("native-checkpoint-v0",str(a))
        self.assertEqual(len(receipt_digest(a)),64)

    def test_mismatched_stage_limits_or_unknown_modules_denied(self):
        broken=copy.deepcopy(self.plan)
        broken["stages"][0]["component"]="gpt-llm"
        with self.assertRaises(CustodyDenied):
            plan_digest(broken)
        with self.assertRaises(CustodyDenied):
            seal_stage(self.plan,[],stage_index=0,
                       checkpoint_input=self.initial,
                       checkpoint_output=b"v1",evidence_bytes=b"",
                       control_receipt_bytes=b"ok",
                       evaluation_receipt_bytes=b"ok",
                       observations=0,interventions=0,cpu_seconds=0)
        with self.assertRaises(CustodyDenied):
            seal_stage(self.plan,[],stage_index=0,
                       checkpoint_input=self.initial,
                       checkpoint_output=b"v1",evidence_bytes=b"ok",
                       control_receipt_bytes=b"ok",
                       evaluation_receipt_bytes=b"ok",
                       observations=513,interventions=0,cpu_seconds=120)

if __name__ == "__main__":
    unittest.main()
