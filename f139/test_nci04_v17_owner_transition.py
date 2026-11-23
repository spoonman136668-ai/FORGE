"""V17 original-owner source transition guards; no live provider or worker calls."""
from __future__ import annotations
import inspect
from pathlib import Path
import unittest
from f139.local_controller import (
    Database, cli, v2_owner_terminal_release_guard, v17_original_model_history_valid
)


class OriginalV17TransitionTests(unittest.TestCase):
    def test_cumulative_history_admits_new_authenticated_utc_day(self):
        base = {
            "G3_DRAFT_ATTEMPTED": 1,
            "G3_DRAFT_AUTHENTICATED": 1,
            "MODEL_DRAFT_ATTEMPTED": 3,
            "MODEL_DRAFT_AUTHENTICATED": 3,
            "FREE_REASONER_ATTEMPTED": 2,
        }
        self.assertTrue(v17_original_model_history_valid(base))
        # A subsequent original owner tick may commit another free request
        # after midnight. Its exact bytes remain sealed by event/sha custody.
        self.assertTrue(v17_original_model_history_valid({
            **base, "FREE_REASONER_ATTEMPTED": 3}))
        self.assertTrue(v17_original_model_history_valid({
            **base, "MODEL_DRAFT_ATTEMPTED": 4,
            "MODEL_DRAFT_AUTHENTICATED": 4,
            "FREE_REASONER_ATTEMPTED": 3}))
        self.assertTrue(v17_original_model_history_valid({
            **base, "MODEL_DRAFT_ATTEMPTED": 4,
            "FREE_REASONER_ATTEMPTED": 3}))
        for bad in (
            {**base, "G3_DRAFT_ATTEMPTED": 2},
            {**base, "MODEL_DRAFT_ATTEMPTED": 2},
            {**base, "MODEL_DRAFT_AUTHENTICATED": 4},
            {**base, "FREE_REASONER_ATTEMPTED": 1},
            {**base, "FREE_REASONER_ATTEMPTED": 9},
            {**base, "MODEL_DRAFT_ATTEMPTED": 9,
             "MODEL_DRAFT_AUTHENTICATED": 9},
            {**base, "FREE_REASONER_ATTEMPTED": True},
            {**base, "extra": 1},
        ):
            with self.subTest(bad=bad):
                self.assertFalse(v17_original_model_history_valid(bad))

    def test_cold_ledger_seals_v16_and_pretransition_model_history(self):
        src=inspect.getsource(Database.verify)
        for expected in (
            'is_v17 = (isinstance(doc, dict)',
            'forge.f139.source-transition.v17',
            'if is_v17:',
            '"SOURCE_TRANSITION_V17_ORIGINAL_CUSTODY_DRIFT"',
            'doc["v16_terminal_event_sha256"] == v16_rows[0]["sha"]',
            'doc["terminal_tasks_sha256"]',
            'doc["model_history_sha256"]',
            'kind IN ',
            'seq<? ORDER BY seq',
            'v17_original_model_history_valid(kinds)',
            'doc["v2_receipt_authorized"] is False',
            'verify_original_negative_custody(self)',
            'verify_second_negative_custody(self)',
            'verify_g49_custody(self)',
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected,src)

    def test_transition_writes_only_once_under_original_db(self):
        src=inspect.getsource(Database.transition_source)
        for expected in (
            'allow_v17: bool = False',
            'if prev_v16:',
            'require(allow_v17 is True',
            '"SOURCE_TRANSITION_V17_ORIGINAL_CUSTODY_REQUIRED"',
            'events[-1]["schema"]==',
            '"forge.f139.source-transition.v16"',
            'and self.active() is None and self.ready() is None',
            'event["v16_terminal_event_sha256"]',
            'event["terminal_tasks_sha256"]',
            'event["model_history_sha256"]',
            '"SOURCE_TRANSITION_V17_MODEL_HISTORY_DRIFT"',
            'self.event("SOURCE_TRANSITION_ADMITTED", event)',
            'self.verify()',
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected,src)

    def test_existing_native_v2_signer_accepts_only_sealed_v17(self):
        src=inspect.getsource(v2_owner_terminal_release_guard)
        for expected in (
            'v17 = False',
            'if event.get("schema")=="forge.f139.source-transition.v17":',
            'event.get("v16_terminal_event_sha256")==v16_rows[0]["sha"]',
            'verify_g49_custody(db)',
            'v7 or v8 or v9 or v10 or v11 or v12 or v13 or v14 or v15 or v16 or v17',
            'event.get("v2_receipt_authorized") is False',
            'verify_native_activation(db)',
        ):
            self.assertIn(expected,src)

    def test_transition_cli_uses_canonical_owner_lock_clean_source_and_readonly_proof(self):
        src=inspect.getsource(cli)
        for expected in (
            'transition-qualified-native-v17',
            'native_original_owner_profile(args.db)',
            'verify_v17_readonly_preflight(validator_db,approval)',
            'with SingleOwner(args.db.with_suffix(".lock")):',
            '"V17_PROTECTED_MAIN_SHA_DRIFT"',
            '"V17_INSTALLED_CLEAN_EXACT_SOURCE_REQUIRED"',
            'api.legacy_dispatchers_disabled()',
            'legacy_windows_task_disabled()',
            'allow_v17=True',
            '"V17_ONE_EVENT_TRANSITION_NOT_ATOMIC"',
        ):
            self.assertIn(expected,src)
        self.assertNotIn('infer_free_once(',src)

    def test_native_activation_preserves_original_v17_negative_set(self):
        from f139.nci04_owner_ledger import activate_native
        src=inspect.getsource(activate_native)
        self.assertIn('"forge.f139.source-transition.v17"',src)
        self.assertIn("v11_ambiguous.add(g54_original_canonical(db)",src)
        self.assertIn('negative_successors[-1]["custodied_negative_tickets"]',src)
        self.assertIn('"UNVERIFIED_HISTORICAL_TASK"',src)

    def test_no_old_cutover_replay_as_v17(self):
        workflow=(Path(__file__).resolve().parent.parent/
                  ".github/workflows/f139-g54-v9-owner-cutover.yml").read_text()
        self.assertIn('  cutover-v16:\n',workflow)
        self.assertIn('  cutover-v17:\n',workflow)
        self.assertEqual(workflow.count('  cutover-v17:\n'),1)
        begin=workflow.index('  cutover-v17:\n')
        end=workflow.index('  cutover-v16:\n',begin)
        v17=workflow[begin:end]
        for expected in (
            'F139-V17-OWNER-CUTOVER ',
            'FORGE-CODEX-REMOTE',
            'F139_V17_ORIGINAL_OWNER_NOT_QUIESCENT',
            'F139_V17_IMMUTABLE_RELEASE_REF_NOT_QUALIFIED',
            'build_v17_readonly_preflight',
            'transition-qualified-native-v17 --approval',
            'F139_V17_ORIGINAL_SOURCE_CUTOVER=PASS',
            'F139_V17_EXISTING_TASK_RESUMED=PASS',
            'F139_V17_PARTIAL_CUSTODY_EXISTING_TASK_HELD_DISABLED',
            'F139_V17_PAID_API_CALLS=0',
            'F139_V17_SCIENTIFIC_FIRST_USE=FALSE',
        ):
            self.assertIn(expected,v17)
        self.assertNotIn('transition-qualified-native-v16 --approval',v17)
        self.assertNotIn('Stop-Process -Force',v17)


    def test_v17_selection_witness_visible_in_existing_readonly_status(self):
        workflow=(Path(__file__).resolve().parent.parent/
                  ".github/workflows/f139-g54-v9-owner-cutover.yml").read_text()
        self.assertEqual(workflow.count("  read-only-status:\n"), 1)
        section=workflow.split("  read-only-status:\n",1)[1].split(
            "\n  cutover-v17:\n",1)[0]
        self.assertIn("F139_G54_CONTROLLER_LOG_TAIL=", section)
        self.assertEqual(section.count(
            "steering_selection=(OptionalField $e 'steering_selection')"), 1)
        self.assertIn("F139_G54_STATUS_READ_ONLY=PASS", section)


if __name__=="__main__":
    unittest.main()
