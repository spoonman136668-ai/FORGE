"""Original owner natural loop routing; no model API or worker calls in tests."""
from __future__ import annotations

import inspect
import unittest

from f139.local_controller import run_once


class OriginalOwnerFreeReasonerRoutingTests(unittest.TestCase):
    def test_bounded_reasoner_runs_only_after_consumed_authenticated_g29(self):
        src=inspect.getsource(run_once)
        self.assertIn("publication_slot_empty and not db.actives()",src)
        self.assertIn("SELECT COUNT(*) FROM events WHERE kind='G3_DRAFT_ATTEMPTED'",src)
        self.assertIn("SELECT COUNT(*) FROM events WHERE kind='MODEL_DRAFT_ATTEMPTED'",src)
        self.assertIn("SELECT COUNT(*) FROM events WHERE kind='MODEL_DRAFT_AUTHENTICATED'",src)
        self.assertIn("if model_attempts != model_successes:",src)
        self.assertIn("MODEL_DRAFT_UNRESOLVED_NO_REPLAY",src)
        self.assertIn("if model_successes:",src)
        self.assertIn("run_original_free_reasoner_once(",src)
        self.assertIn("native_original_running_publisher_profile(db_path)",src)
        self.assertIn("run_original_g29_once(",src)
        self.assertIn("FREE_REASONER_GUARD_BLOCKED_FAIL_CLOSED",src)
        self.assertNotIn("OPENROUTER_API_KEY",src)
        self.assertNotIn("codex exec",src)
        self.assertNotIn("first_use=True",src)
        self.assertNotIn("dispatch_science(",src)

    def test_original_loop_reconciles_before_new_model_proposal(self):
        src=inspect.getsource(run_once)
        self.assertLess(src.index("for active_record in db.actives():"),
                        src.index("run_original_free_reasoner_once("))
        self.assertLess(src.index("api.native_eligible_issues("),
                        src.index("run_original_free_reasoner_once("))
        self.assertLess(src.index("publication_slot_empty"),
                        src.index("run_original_free_reasoner_once("))
        self.assertLess(src.index("if model_attempts != model_successes:"),
                        src.index("run_original_free_reasoner_once("))
        self.assertLess(src.index("if model_successes:"),
                        src.index("run_original_free_reasoner_once("))


if __name__ == "__main__":
    unittest.main()
