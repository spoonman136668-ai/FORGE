"""Original-ledger UTC rollover coverage; strictly isolated, no provider or owner.

Qualification only: this does not exercise a real model request or authorize
a second F139 controller, an original-owner ledger mutation or scientific use.
"""
from __future__ import annotations

import unittest
from unittest.mock import Mock

from f139.local_controller import Database, SingleOwner
from f139.nci04_v19_original_atomic_reserve_no_post import (
    reserve_original_intent_without_post,
)
from f139.nci04_v19_original_attempt_schema import KIND
from test_nci04_v19_original_attempt_schema import (
    OriginalRequestColdVerifierTests,
)


class OriginalUTCModelRenewalBoundaryTests(unittest.TestCase):
    def setUp(self):
        # This fixture creates its own temporary ORIGINAL-schema SQLite file.
        # All event kinds and full cold chain checks are production validators.
        fixture = OriginalRequestColdVerifierTests(
            "test_no_new_events_original_behavior_and_original_head_unchanged"
        )
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.fixture = fixture
        self.db = fixture.db
        self.mutex = fixture.mutex
        self.owner_witness = Mock(return_value=True)

    def reserve(self, lane, day):
        return reserve_original_intent_without_post(
            self.db,
            lane=lane,
            utc_day=day,
            owner_witness=self.owner_witness,
        )

    def count_renewals(self):
        return self.db.conn.execute(
            "SELECT COUNT(*) FROM events WHERE kind=?", (KIND,)
        ).fetchone()[0]

    def assert_cold_equivalence(self, expected):
        self.db.verify()
        self.assertEqual(self.db.meta(), expected)
        cold = Database(self.db.filename)
        try:
            cold.verify()
            self.assertEqual(cold.meta(), expected)
        finally:
            cold.close()

    def test_next_utc_day_reopens_only_budget_not_spent_terminal(self):
        """Fresh native evidence is admissible after day reset, just ONCE."""
        self.fixture.original_spent_free_request(day="2026-10-28")
        candidate = self.fixture.real_native()  # New terminal AFTER legacy spend.
        with SingleOwner(self.mutex):
            original = self.db.meta().copy()
            same_day = self.reserve(candidate.lane, "2026-10-28")
            self.assertEqual(
                same_day["disposition"],
                "BLOCKED_COMBINED_ORIGINAL_AND_V19_BUDGET",
            )
            self.assertEqual(self.count_renewals(), 0)
            self.assert_cold_equivalence(original)

            # Crossing UTC midnight must not reset the original old attempt,
            # erase the genuine terminal, or change the owner source.
            next_day = self.reserve(candidate.lane, "2026-10-29")
            self.assertEqual(
                next_day["disposition"], "ORIGINAL_ATOMIC_INTENT_COMMITTED_NO_POST"
            )
            self.assertEqual(self.count_renewals(), 1)
            accepted = self.db.meta().copy()
            self.assertEqual(accepted["head_seq"], original["head_seq"] + 1)
            self.assert_cold_equivalence(accepted)

            # No additional inference becomes legitimate via another rollover.
            for later in ("2026-10-29", "2026-10-30", "2026-11-30"):
                with self.subTest(day=later):
                    repeat = self.reserve(candidate.lane, later)
                    self.assertEqual(repeat["disposition"], "BLOCKED_ALREADY_CONSUMED")
                    self.assertEqual(self.count_renewals(), 1)
                    self.assert_cold_equivalence(accepted)

    def test_old_terminal_remains_stale_after_utc_day_rollover(self):
        """Rollover alone cannot turn evidence before a free spend into work."""
        candidate = self.fixture.real_native()
        self.fixture.original_spent_free_request(day="2026-10-28")
        with SingleOwner(self.mutex):
            original = self.db.meta().copy()
            for later in ("2026-10-29", "2026-10-30", "2026-11-30"):
                with self.subTest(day=later):
                    response = self.reserve(candidate.lane, later)
                    self.assertEqual(
                        response["disposition"],
                        "BLOCKED_NO_NEW_TERMINAL_AFTER_ORIGINAL_ATTEMPT",
                    )
                    self.assertEqual(self.count_renewals(), 0)
                    self.assert_cold_equivalence(original)

    def test_no_original_mutex_blocks_every_utc_day(self):
        """A fresh date is never an authorization to bypass SingleOwner."""
        self.fixture.original_spent_free_request(day="2026-10-28")
        candidate = self.fixture.real_native()
        original = self.db.meta().copy()
        with self.assertRaisesRegex(Exception, "MUTEX_NOT_HELD"):
            self.reserve(candidate.lane, "2026-10-29")
        self.assertEqual(self.count_renewals(), 0)
        self.assert_cold_equivalence(original)


if __name__ == "__main__":
    unittest.main()
