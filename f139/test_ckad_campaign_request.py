"""Inert autonomous training specification tests; no runner or model calls."""
from __future__ import annotations

import copy
import unittest

from f139.ckad_campaign_request import (
    SCHEMA, OWNER_REPO, OWNER_TASK, SCIENCE_OWNER, MODE,
    CampaignDenied, validate_campaign, next_stage, seal_owner_result,
)
from f139.ckad_stage_custody import (
    SCHEMA as PLAN_SCHEMA, SOURCE_REPO, SOURCE_MAIN, CKAD13_SHA, CKAD13_TREE,
    digest, receipt_digest,
)


def campaign(initial=b"native-start"):
    component = "yggdrasil.native_cumulative_learner.NativeCumulativeLearner"
    stages = [
        {"id": "observe-01", "phase": "observe", "component": component,
         "max_observations": 10, "max_interventions": 0, "max_cpu_seconds": 10},
        {"id": "learn-02", "phase": "learn", "component": component,
         "max_observations": 10, "max_interventions": 5, "max_cpu_seconds": 10},
        {"id": "evaluate-03", "phase": "evaluate", "component": component,
         "max_observations": 10, "max_interventions": 0, "max_cpu_seconds": 10},
    ]
    plan = {"schema": PLAN_SCHEMA, "source_repo": SOURCE_REPO,
            "accepted_main": SOURCE_MAIN, "candidate_sha": CKAD13_SHA,
            "candidate_tree": CKAD13_TREE,
            "native_architecture": "yggdrasil-native-tokenless",
            "source_mode": "previously-consumed-synthetic-only",
            "initial_checkpoint_sha256": digest(initial),
            "frozen_prereg_sha256": "a" * 64,
            "frozen_controls_sha256": "b" * 64,
            "frozen_split_sha256": "c" * 64,
            "seeds": [101, 202, 303], "stages": stages,
            "scientific_first_use": False,
            "training_execution_authorized": False}
    return {"schema": SCHEMA, "campaign_id": "ckad-dev-001",
            "lane": "Yggdrasil", "science_owner": SCIENCE_OWNER,
            "owner_repo": OWNER_REPO, "owner_task": OWNER_TASK,
            "original_owner_source_sha": "1e3a3b7d63d7dce13924e279cfb61f3d975bd9aa",
            "mode": MODE, "plan": plan, "max_total_observations": 30,
            "max_total_interventions": 5, "max_total_cpu_seconds": 30,
            "max_stages": 3, "scientific_first_use": False,
            "training_execution_authorized": False,
            "promotion_authorized": False, "paid_api_calls": 0,
            "new_controller": False, "new_scheduler": False, "new_queue": False}


def result(c, history, old, new, external=None):
    req = next_stage(c, history, independently_pinned_head=external)
    receipt = seal_owner_result(
        c, history, req["next_stage"], independently_pinned_head=external,
        checkpoint_input=old, checkpoint_output=new,
        evidence_bytes=b"observed-source-record", control_receipt_bytes=b"frozen-control",
        evaluation_receipt_bytes=b"held-evaluation", observations=1,
        interventions=0, cpu_seconds=1)
    return receipt


class SpecifiedTrainingRequestTests(unittest.TestCase):
    def test_stage_by_stage_cold_continuation_with_independent_head(self):
        c = campaign()
        a = result(c, [], b"native-start", b"native-v1")
        b = result(c, [a], b"native-v1", b"native-v2",
                   external=receipt_digest(a))
        d = result(c, [a, b], b"native-v2", b"native-v3",
                   external=receipt_digest(b))
        end = next_stage(c, [a, b, d],
                         independently_pinned_head=receipt_digest(d))
        self.assertEqual(end["status"], "ALL_REQUESTED_STAGES_SEALED")
        self.assertIsNone(end["next_stage"])
        self.assertEqual(end["checkpoint_sha256"], digest(b"native-v3"))
        self.assertFalse(end["training_execution_authorized"])
        self.assertFalse(end["scientific_pass"])
        self.assertEqual(next_stage(c, [a],
                         independently_pinned_head=receipt_digest(a))
                         ["stages_completed"], 1)

    def test_initial_request_is_specific_and_not_authority(self):
        c = campaign()
        initial = next_stage(c, [])
        self.assertEqual(initial["status"],
                         "CKAD_OWNER_STAGE_AUTHORIZATION_REQUIRED")
        self.assertEqual(initial["next_stage"]["phase"], "observe")
        self.assertEqual(initial["next_stage"]["target_source_sha"], CKAD13_SHA)
        self.assertEqual(initial["next_stage"]["input_checkpoint_sha256"],
                         digest(b"native-start"))
        self.assertFalse(initial["dispatch_authorized"])
        self.assertFalse(initial["next_stage"]["scientific_first_use"])
        self.assertEqual(len(initial["next_request_sha256"]), 64)

    def test_no_unpinned_resume_or_tampered_terminal_receipt(self):
        c = campaign()
        a = result(c, [], b"native-start", b"native-v1")
        with self.assertRaises(CampaignDenied):
            next_stage(c, [a])
        with self.assertRaises(CampaignDenied):
            next_stage(c, [a], independently_pinned_head="0" * 64)
        altered = [dict(a, output_checkpoint_sha256="f" * 64)]
        with self.assertRaises(CampaignDenied):
            next_stage(c, altered,
                       independently_pinned_head=receipt_digest(a))
        with self.assertRaises(CampaignDenied):
            next_stage(c, [], independently_pinned_head="0" * 64)

    def test_authority_scope_and_global_budget_are_frozen(self):
        c = campaign()
        self.assertEqual(len(validate_campaign(c)["campaign_sha256"]), 64)
        changes = [
            ("training_execution_authorized", True),
            ("scientific_first_use", True),
            ("promotion_authorized", True),
            ("paid_api_calls", True),
            ("new_scheduler", True),
            ("new_queue", True),
            ("lane", "Wingless"),
            ("owner_task", "other-controller"),
            ("original_owner_source_sha", "bad"),
            ("max_total_cpu_seconds", 29),
            ("max_total_interventions", 4),
            ("max_total_observations", 29),
        ]
        for key, value in changes:
            changed = copy.deepcopy(c)
            changed[key] = value
            with self.subTest(key=key), self.assertRaises(CampaignDenied):
                validate_campaign(changed)

    def test_replay_wrong_proposal_and_checkpoint_reset_fail_closed(self):
        c = campaign()
        step = next_stage(c, [])
        altered = dict(step["next_stage"], stage_index=1)
        with self.assertRaises(CampaignDenied):
            seal_owner_result(
                c, [], altered, checkpoint_input=b"native-start",
                checkpoint_output=b"native-v1", evidence_bytes=b"ok",
                control_receipt_bytes=b"ok", evaluation_receipt_bytes=b"ok",
                observations=1, interventions=0, cpu_seconds=1)
        with self.assertRaises(CampaignDenied):
            result(c, [], b"unrelated-reset", b"native-v1")

    def test_stage_limit_and_budgets_stop_extra_training(self):
        c = campaign()
        c["max_stages"] = 2
        c["max_total_cpu_seconds"] = 20
        c["max_total_observations"] = 20
        a = result(c, [], b"native-start", b"native-v1")
        b = result(c, [a], b"native-v1", b"native-v2",
                   external=receipt_digest(a))
        end = next_stage(c, [a, b],
                         independently_pinned_head=receipt_digest(b))
        self.assertIsNone(end["next_stage"])
        with self.assertRaises(CampaignDenied):
            next_stage(c, [a, b, b],
                       independently_pinned_head=receipt_digest(b))


if __name__ == "__main__":
    unittest.main()
