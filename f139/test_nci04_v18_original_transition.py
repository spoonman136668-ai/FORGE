"""Source-only V18 original owner transition gates and no-replay regression.

No live owner, provider, GitHub write, model execution, task dispatch, or
SQLite mutation. The existing full-F139 regression still runs separately.
"""
from __future__ import annotations

import inspect
from pathlib import Path
import unittest

from f139.local_controller import Database, cli, v2_owner_terminal_release_guard
from f139.nci04_owner_ledger import activate_native
from f139.nci04_v18_owner_readonly_preflight import (
    FROM_V17, SCHEMA, build_v18_readonly_preflight,
    verify_v18_readonly_preflight,
)


class OriginalV18TransitionSourceTests(unittest.TestCase):
    def test_exact_v17_predecessor_and_readonly_schema(self):
        self.assertEqual(FROM_V17, "3775bed30891ff748197a539afe5b92813680e26")
        self.assertEqual(SCHEMA, "forge.f139.nci04.v18.original-owner-readonly-preflight.v1")
        p = inspect.getsource(build_v18_readonly_preflight)
        v = inspect.getsource(verify_v18_readonly_preflight)
        self.assertIn("verify_v18_readonly_preflight(db, proof)", p)
        self.assertIn('"runtime_cutover_authorized": False', v)
        for raw in (p, v):
            self.assertNotIn("db.transition_source(", raw)
            self.assertNotIn("db.event(", raw)

    def test_cold_original_ledger_accepts_only_custodied_v18(self):
        src = inspect.getsource(Database.verify)
        for token in (
            'is_v18 = (isinstance(doc, dict)',
            '"forge.f139.source-transition.v18"',
            '"v17_terminal_event_sha256"',
            'if is_v18:',
            '"SOURCE_TRANSITION_V18_ORIGINAL_CUSTODY_DRIFT"',
            'v17_original_model_history_valid(kinds)',
            '"SOURCE_TRANSITION_HEAD_INVALID"',
            'self.verified_native_provider_failures(',
            'verify_original_negative_custody(self)',
            'verify_second_negative_custody(self)',
            'verify_g49_custody(self)',
        ):
            with self.subTest(token=token):
                self.assertIn(token, src)

    def test_v18_is_unique_idle_source_transition_under_existing_transaction(self):
        src = inspect.getsource(Database.transition_source)
        for token in (
            'allow_v18: bool = False',
            'if prev_v17:',
            'allow_v18 is True and len(prev_v17)==1',
            '"forge.f139.source-transition.v17"',
            '"SOURCE_TRANSITION_V18_ORIGINAL_CUSTODY_REQUIRED"',
            '"forge.f139.source-transition.v18"',
            'and self.active() is None and self.ready() is None',
            'self.event("SOURCE_TRANSITION_ADMITTED", event)',
            '"SOURCE_TRANSITION_V18_V17_SEAL_MISSING"',
            'v17_original_model_history_valid(kinds)',
            'self.verify()',
        ):
            with self.subTest(token=token):
                self.assertIn(token, src)
        self.assertIn('self.conn.execute("UPDATE meta SET source_sha=? WHERE id=1"', src)

    def test_no_existing_v2_authority_regression(self):
        src = inspect.getsource(v2_owner_terminal_release_guard)
        self.assertIn('v18 = False', src)
        self.assertIn('"forge.f139.source-transition.v18"', src)
        self.assertIn('and event.get("v2_receipt_authorized") is False', src)
        self.assertIn('verify_native_activation(db)', src)

    def test_explicit_v18_is_never_default_enabled_and_keeps_v17_historical(self):
        transition = inspect.getsource(Database.transition_source)
        verify = inspect.getsource(Database.verify)
        self.assertIn('allow_v18: bool = False', transition)
        self.assertIn('require(allow_v18 is True and len(prev_v17)==1', transition)
        self.assertIn('elif prev_v16:', transition)
        self.assertIn('if is_v17:', verify)
        self.assertIn('if is_v18:', verify)
        self.assertLess(verify.index('if is_v17:'), verify.index('if is_v18:'))
        self.assertIn('v17_original_model_history_valid(kinds)', verify)
        self.assertIn('"v17_terminal_event_sha256"', verify)

    def test_original_native_activation_retains_negative_custody_at_v18(self):
        source = inspect.getsource(activate_native)
        self.assertIn('"forge.f139.source-transition.v18"', source)
        self.assertIn('negative_successors[-1]["custodied_negative_tickets"]', source)
        self.assertIn('verify_original_negative_custody(db)', source)
        self.assertIn('verify_second_negative_custody(db)', source)
        self.assertIn('verify_g49_custody(db)', source)

    def test_one_time_guarded_windows_owner_release_is_separate_and_deny_by_default(self):
        workflow = (Path(__file__).resolve().parent.parent /
                    ".github/workflows/f139-g54-v9-owner-cutover.yml").read_text()
        self.assertEqual(workflow.count("  cutover-v18:\n"), 1)
        begin = workflow.index("  cutover-v18:\n")
        end = workflow.index("  cutover-v17:\n", begin)
        part = workflow[begin:end]
        for expected in (
            "github.actor == 'spoonman136668-ai'",
            "github.event.issue.number == 807",
            "F139-V18-OWNER-CUTOVER ",
            "$old='3775bed30891ff748197a539afe5b92813680e26'",
            "FORGE-CODEX-REMOTE",
            "F139_V18_ORIGINAL_OWNER_NOT_QUIESCENT",
            "F139_V18_IMMUTABLE_RELEASE_REF_NOT_QUALIFIED",
            "$release.protected -ne $true",
            "F139_V18_ORIGINAL_LEDGER_BACKUP=PASS",
            "build_v18_readonly_preflight",
            "transition-qualified-native-v18 --approval",
            "F139_V18_ORIGINAL_SOURCE_CUTOVER=PASS",
            "F139_V18_EXISTING_TASK_RESUMED=PASS",
            "F139_V18_PARTIAL_CUSTODY_EXISTING_TASK_HELD_DISABLED",
            "F139_V18_PAID_API_CALLS=0",
            "F139_V18_SCIENTIFIC_FIRST_USE=FALSE",
            "F139_V18_POLICY_SOURCE_PROMOTION_FAILED",
            "F139_V18_SOURCE_PINNED_OWNER_POLICY_DRIFT",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, part)
        for forbidden in (
            "F139-V17-OWNER-CUTOVER ",
            "transition-qualified-native-v17 --approval",
            "Stop-Process -Force",
            "F139_V17_",
        ):
            self.assertNotIn(forbidden, part)
        # Verify actual enforcement, not the generic GitHub protected bit.
        for locked in (
            "F139_V18_RELEASE_RULESET_READ_DENIED",
            "F139_V18_RELEASE_RULESET_NOT_UNIQUE_OR_ACTIVE",
            "F139_V18_RELEASE_RULESET_SCOPE_OR_BYPASS_DRIFT",
            "F139_V18_RELEASE_RULESET_LOCK_WEAKENED",
            "FORGE F139 immutable owner release refs",
            "refs/heads/f139-owner-release-*",
            "@($rule.bypass_actors).Count -ne 0",
            "$lockTypes[0] -cne 'deletion'",
            "$lockTypes[1] -cne 'update'",
            "F139_V18_RELEASE_REF_IMMUTABILITY=VERIFIED",
        ):
            with self.subTest(locked=locked):
                self.assertIn(locked, part)
        self.assertLess(
            part.index("F139_V18_RELEASE_REF_IMMUTABILITY=VERIFIED"),
            part.index("Disable-ScheduledTask"))
        self.assertIn("concurrency:\n  group: forge-f139-g54-v9-owner-cutover",
                      workflow)

    def test_original_cli_adds_no_automatic_release_or_worker(self):
        src = inspect.getsource(cli)
        self.assertIn('transition-qualified-native-v18', src)
        for token in (
            'verify_v18_readonly_preflight(validator_db,approval)',
            'native_original_owner_profile(args.db)',
            'with SingleOwner(args.db.with_suffix(".lock")):',
            '"V18_PROTECTED_MAIN_SHA_DRIFT"',
            '"V18_INSTALLED_CLEAN_EXACT_SOURCE_REQUIRED"',
            'api.legacy_dispatchers_disabled()',
            'legacy_windows_task_disabled()',
            'allow_v18=True',
            '"V18_ONE_EVENT_TRANSITION_NOT_ATOMIC"',
            '"scientific_first_use":False',
            '"paid_api_calls":0',
        ):
            with self.subTest(token=token):
                self.assertIn(token, src)
        self.assertNotIn('first_use=True', src)


if __name__ == "__main__":
    unittest.main()
