"""Source-only V18 original owner transition gates and no-replay regression.

No live owner, provider, GitHub write, model execution, task dispatch, or
SQLite mutation. The existing full-F139 regression still runs separately.
"""
from __future__ import annotations

import inspect
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
