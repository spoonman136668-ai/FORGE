"""Disarmed V41 installation rollback boundary and owner-state negative controls.

All examples are synthetic records. No original task, owner SQLite, release
branch or approval comment is read or modified. No science first use.
"""
import copy
import unittest

from f139 import nci04_v41_owner_install_failure_fence as fence
from f139 import nci04_v41_guarded_release_preflight as release
from f139 import nci04_v41_source_transition as source
from f139 import nci04_v41_pending_escrow as escrow

ORIGINAL = source.FROM_V40
TARGET = "c" * 40
TREE = "d" * 40
HEAD = "e" * 64
COPY_HEAD = "f" * 64
ESCROW_SHA = "a" * 64
MANIFEST = "b" * 64


def synthetic_receipts():
    readiness = {
        "schema": release.SCHEMA,
        "source_sha": TARGET,
        "source_tree_sha": TREE,
        "original_source_sha": ORIGINAL,
        "original_head_seq": escrow.OBSERVED_SEQ,
        "original_head_sha256": HEAD,
        "sealed_manifest_sha256": MANIFEST,
        "backup_run_id": 123456,
        "independent_restore_verified": True,
        "candidate_inputs_readonly_qualified": True,
        "pending_1715_escrow_intent_verified": True,
        "original_owner_installed": False,
        "release_qualified": False,
        "source_transition_authorized": False,
        "scientific_first_use": False,
        "hybrid_admission": False,
        "new_dispatches": 0,
        "owner_mutations": 0,
    }
    copied = {
        "schema": "forge.f139.v41.atomic-copy-rehearsal.v1",
        "original_source_sha": ORIGINAL,
        "copy_source_sha": TARGET,
        "original_head_seq": escrow.OBSERVED_SEQ,
        "copy_head_seq": escrow.OBSERVED_SEQ + 2,
        "copy_head_sha256": COPY_HEAD,
        "escrow_event_sha256": ESCROW_SHA,
        "original_unchanged": True,
        "copy_only": True,
        "release_qualified": False,
        "source_transition_authorized": False,
        "reissue_authorized": False,
        "scientific_first_use": False,
        "hybrid_admission": False,
        "new_dispatches": 0,
    }
    owner = {
        "schema": "forge.f139.v41.original-locked-readonly-status.v1",
        "installed_source_sha": ORIGINAL,
        "target_source_sha": TARGET,
        "original_head_seq": escrow.OBSERVED_SEQ,
        "original_head_sha256": HEAD,
        "verified_historical_tasks": 153,
        "quarantined_historical_tasks": 56,
        "pending_issue_number": 1715,
        "sqlite_query_only": True,
        "original_owner_mutations": 0,
        "new_dispatches": 0,
        "reissue_authorized": False,
        "source_transition_authorized": False,
        "source_release_qualified": False,
        "scientific_first_use": False,
        "hybrid_admission": False,
    }
    return readiness, copied, owner


def synthetic_observation(stage):
    pre = stage in fence.PRE_COMMIT
    policy_new = stage in {"POLICY_UPDATED", "TARGET_INSTALLED",
                           "TARGET_TASK_RESUMED"}
    code_new = stage in {"TARGET_INSTALLED", "TARGET_TASK_RESUMED"}
    return {
        "source_sha": ORIGINAL if pre else TARGET,
        "head_seq": escrow.OBSERVED_SEQ if pre else escrow.OBSERVED_SEQ + 2,
        "head_sha256": HEAD if pre else COPY_HEAD,
        "task_disabled": stage not in {"OWNER_READONLY",
                                      "TARGET_TASK_RESUMED"},
        "policy_source_sha": TARGET if policy_new else ORIGINAL,
        "installed_source_sha": TARGET if code_new else ORIGINAL,
        "escrow_count": 0 if pre else 1,
        "source_transition_count": 0 if pre else 1,
        "new_dispatches": 0,
        "scientific_first_use": False,
        "hybrid_admission": False,
    }


class V41InstallFailureFenceTests(unittest.TestCase):
    def setUp(self):
        self.readiness, self.copied, self.owner = synthetic_receipts()
        self.plan = fence.inert_handoff(
            self.readiness, self.copied, self.owner)

    def test_exact_three_way_owner_and_copied_history_match_is_disarmed(self):
        expected = {
            "source_sha": TARGET,
            "original_head_seq": escrow.OBSERVED_SEQ,
            "expected_copy_head_seq": escrow.OBSERVED_SEQ + 2,
            "expected_copy_head_sha256": COPY_HEAD,
            "expected_escrow_sha256": ESCROW_SHA,
        }
        self.assertEqual({k: self.plan[k] for k in expected}, expected)
        for key in ("approved_live_release", "original_owner_installed",
                    "source_transition_authorized", "scientific_first_use",
                    "hybrid_admission"):
            self.assertFalse(self.plan[key])
        self.assertEqual(self.plan["new_dispatches"], 0)
        self.assertEqual(self.plan["original_owner_mutations"], 0)
        self.assertEqual(self.plan["remote_writes"], 0)

    def test_bad_readiness_or_forged_release_authority_denied(self):
        for field, replacement in (
            ("schema", "forged-schema"),
            ("original_source_sha", "0"*40),
            ("source_sha", ORIGINAL),
            ("independent_restore_verified", False),
            ("candidate_inputs_readonly_qualified", False),
            ("pending_1715_escrow_intent_verified", False),
            ("source_transition_authorized", True),
            ("release_qualified", True),
            ("original_owner_installed", True),
            ("scientific_first_use", True),
            ("hybrid_admission", True),
            ("owner_mutations", 1),
            ("new_dispatches", 1),
            ("sealed_manifest_sha256", "0"),
        ):
            with self.subTest(field=field):
                bad = dict(self.readiness, **{field: replacement})
                with self.assertRaises(fence.InstallSafetyDenied):
                    fence.inert_handoff(bad, self.copied, self.owner)

    def test_copy_and_original_custody_mismatches_denied(self):
        for field, replacement in (
            ("copy_source_sha", "2"*40),
            ("copy_head_seq", escrow.OBSERVED_SEQ+1),
            ("original_head_seq", escrow.OBSERVED_SEQ+1),
            ("copy_head_sha256", "bad"),
            ("original_unchanged", False),
            ("copy_only", False),
            ("release_qualified", True),
            ("source_transition_authorized", True),
            ("new_dispatches", 1),
        ):
            with self.subTest(field=field):
                bad = dict(self.copied, **{field: replacement})
                with self.assertRaises(fence.InstallSafetyDenied):
                    fence.inert_handoff(self.readiness, bad, self.owner)
        for field, replacement in (
            ("target_source_sha", "3"*40),
            ("original_head_sha256", "0"*64),
            ("source_release_qualified", True),
            ("original_owner_mutations", 1),
            ("pending_issue_number", 1714),
            ("sqlite_query_only", False),
            ("verified_historical_tasks", 152),
            ("quarantined_historical_tasks", 55),
        ):
            with self.subTest(field=field):
                bad = dict(self.owner, **{field: replacement})
                with self.assertRaises(fence.InstallSafetyDenied):
                    fence.inert_handoff(self.readiness, self.copied, bad)

    def test_precommit_faults_preserve_old_owner_no_sqlite_restore(self):
        original = copy.deepcopy(self.plan)
        for stage in sorted(fence.PRE_COMMIT):
            with self.subTest(stage=stage):
                report = fence.interrupted_cutover_response(
                    self.plan, stage=stage,
                    observation=synthetic_observation(stage))
                self.assertEqual(
                    report["recovery_decision"],
                    "V40_RECOVERY_ELIGIBLE_AFTER_SEPARATE_OWNER_VERIFICATION")
                self.assertFalse(report["hold_original_task_disabled"])
                self.assertFalse(report["sqlite_backup_restore_authorized"])
                self.assertFalse(report["automatic_rollback_or_replay_authorized"])
                self.assertFalse(report["actual_task_action_performed"])
                self.assertFalse(report["original_db_written"])
                self.assertFalse(report["scientific_first_use"])
        self.assertEqual(self.plan, original)

    def test_postcommit_faults_require_forward_repair_and_never_restore(self):
        for stage in ("SOURCE_PAIR_COMMITTED", "POLICY_UPDATED",
                      "TARGET_INSTALLED"):
            with self.subTest(stage=stage):
                out = fence.interrupted_cutover_response(
                    self.plan, stage=stage,
                    observation=synthetic_observation(stage))
                self.assertTrue(out["hold_original_task_disabled"])
                self.assertEqual(out["recovery_decision"],
                                 "HOLD_DISABLED_FORWARD_REPAIR_ONLY")
                self.assertFalse(out["sqlite_backup_restore_authorized"])
                self.assertFalse(out["source_transition_authorized"])
                self.assertFalse(out["actual_task_action_performed"])

    def test_resumed_owner_still_requires_independent_acceptance(self):
        out = fence.interrupted_cutover_response(
            self.plan, stage="TARGET_TASK_RESUMED",
            observation=synthetic_observation("TARGET_TASK_RESUMED"))
        self.assertEqual(out["recovery_decision"],
                         "POSTINSTALL_INDEPENDENT_ACCEPTANCE_REQUIRED")
        self.assertFalse(out["hold_original_task_disabled"])
        self.assertFalse(out["source_transition_authorized"])
        self.assertFalse(out["scientific_first_use"])

    def test_precommit_original_drift_and_stranded_escrow_denied(self):
        for stage in fence.PRE_COMMIT:
            for field, value in (
                ("source_sha", TARGET),
                ("head_seq", escrow.OBSERVED_SEQ + 1),
                ("head_sha256", COPY_HEAD),
                ("escrow_count", 1),
                ("source_transition_count", 1),
                ("policy_source_sha", TARGET),
                ("installed_source_sha", TARGET),
            ):
                with self.subTest(stage=stage, field=field):
                    observed = synthetic_observation(stage)
                    observed[field] = value
                    with self.assertRaises(fence.InstallSafetyDenied):
                        fence.interrupted_cutover_response(
                            self.plan, stage=stage, observation=observed)

    def test_postcommit_wrong_head_partial_pair_and_running_owner_denied(self):
        for stage in fence.POST_COMMIT:
            for field, value in (
                ("source_sha", ORIGINAL),
                ("head_seq", escrow.OBSERVED_SEQ + 1),
                ("head_sha256", HEAD),
                ("escrow_count", 0),
                ("source_transition_count", 0),
            ):
                with self.subTest(stage=stage, field=field):
                    observed = synthetic_observation(stage)
                    observed[field] = value
                    with self.assertRaises(fence.InstallSafetyDenied):
                        fence.interrupted_cutover_response(
                            self.plan, stage=stage, observation=observed)
        for stage in fence.POST_COMMIT - {"TARGET_TASK_RESUMED"}:
            observed = synthetic_observation(stage)
            observed["task_disabled"] = False
            with self.assertRaisesRegex(
                    fence.InstallSafetyDenied, "TASK_MUST_REMAIN_DISABLED"):
                fence.interrupted_cutover_response(
                    self.plan, stage=stage, observation=observed)

    def test_partial_policy_or_code_activation_never_qualifies(self):
        for stage, field in (
            ("POLICY_UPDATED", "policy_source_sha"),
            ("TARGET_INSTALLED", "policy_source_sha"),
            ("TARGET_INSTALLED", "installed_source_sha"),
            ("TARGET_TASK_RESUMED", "policy_source_sha"),
            ("TARGET_TASK_RESUMED", "installed_source_sha"),
        ):
            with self.subTest(stage=stage, field=field):
                observed = synthetic_observation(stage)
                observed[field] = ORIGINAL
                with self.assertRaises(fence.InstallSafetyDenied):
                    fence.interrupted_cutover_response(
                        self.plan, stage=stage, observation=observed)

    def test_false_science_or_model_admission_never_allowed(self):
        for stage in fence.ALL_STAGES:
            for field, value in (
                ("new_dispatches", 1),
                ("scientific_first_use", True),
                ("hybrid_admission", True),
            ):
                with self.subTest(stage=stage, field=field):
                    observed = synthetic_observation(stage)
                    observed[field] = value
                    with self.assertRaises(fence.InstallSafetyDenied):
                        fence.interrupted_cutover_response(
                            self.plan, stage=stage, observation=observed)

    def test_invalid_replay_input_and_injected_release_permit_denied(self):
        for field, value in (
            ("schema", "forged"),
            ("source_transition_authorized", True),
            ("approved_live_release", True),
            ("target_source_sha", "bad"),
            ("original_head_sha256", "bad"),
            ("expected_copy_head_seq", escrow.OBSERVED_SEQ + 1),
        ):
            with self.subTest(field=field):
                bad = dict(self.plan, **{field: value})
                with self.assertRaises(fence.InstallSafetyDenied):
                    fence.interrupted_cutover_response(
                        bad, stage="ORIGINAL_TRANSACTION_OPEN",
                        observation=synthetic_observation(
                            "ORIGINAL_TRANSACTION_OPEN"))
        with self.assertRaises(fence.InstallSafetyDenied):
            fence.interrupted_cutover_response(
                self.plan, stage="UNSUPPORTED_REPLAY",
                observation=synthetic_observation("OWNER_READONLY"))


if __name__ == "__main__":
    unittest.main()
