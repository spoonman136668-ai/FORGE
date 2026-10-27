"""Wingless native R8 free-model lane source-only qualification.

No network, owner database mutation, remote model execution or first-use rights.
"""
from __future__ import annotations
import inspect
import unittest

from f139.nci04_native_contract import (
    REPOS, WINGLESS_R8_TRAINING, model_source_path_allowed,
)
from f139.nci04_owner_free_reasoner_proposal import (
    WINGLESS_R8_PARENT, MAX_DAILY_REQUESTS, MAX_LIFETIME_REQUESTS,
    select_bounded_free_lane, run_original_free_reasoner_once,
)
from f139.nci04_model_proposal import build_request, validate
from f139.nci04_model_owner_bridge import owner_request
from f139.nci04_free_reasoner_provider import (
    public_packet, verify_anonymous_public_source,
)
from f139.local_controller import GitHub


class BothNativeModelsFreeReasonerTests(unittest.TestCase):
    def test_both_lanes_share_one_owner_budget_and_preserve_yggdrasil_first(self):
        self.assertEqual(MAX_DAILY_REQUESTS, 1)
        self.assertEqual(MAX_LIFETIME_REQUESTS, 8)
        self.assertEqual(select_bounded_free_lane([]), "Yggdrasil")
        self.assertEqual(select_bounded_free_lane(
            [{"lane": "Yggdrasil"}]), "Wingless")
        self.assertEqual(select_bounded_free_lane(
            [{"lane": "Yggdrasil"}, {"lane": "Wingless"}]), "Yggdrasil")
        self.assertEqual(select_bounded_free_lane(
            [{"lane": "Yggdrasil"}, {"lane": "Wingless"},
             {"lane": "Yggdrasil"}]), "Wingless")

    def test_only_single_native_wingless_r8_file_is_newly_allowed(self):
        self.assertIn("Wingless", REPOS)
        self.assertIn("Yggdrasil", REPOS)
        self.assertEqual(WINGLESS_R8_TRAINING,
                         "research/native/itd02/outcome/training_session.go")
        self.assertEqual(WINGLESS_R8_PARENT,
                         "01ca1471b60616fe323dae2ecbc0f16d053b38f3")
        self.assertTrue(model_source_path_allowed("Wingless", WINGLESS_R8_TRAINING))
        self.assertTrue(model_source_path_allowed("Wingless", "cmd/wingless/local.go"))
        self.assertTrue(model_source_path_allowed(
            "Yggdrasil", "yggdrasil/public_causal_cells.py"))
        for path in (
            "research/native/itd02/outcome/selected.go",
            "research/native/itd02/outcome/training_session.go.backup.go",
            "research/native/itd02/outcome/../training_session.go",
            "research/native/itd02/outcome/training_session_test.go",
            "research/native/itd02/outcomebridge/main.go",
            ".github/workflows/itd02-native-self-training-dev.yml",
            "docs/AGENTS.md",
        ):
            with self.subTest(path=path):
                self.assertFalse(model_source_path_allowed("Wingless", path))
        self.assertFalse(model_source_path_allowed("Yggdrasil", WINGLESS_R8_TRAINING))
        self.assertFalse(model_source_path_allowed("Unknown", WINGLESS_R8_TRAINING))

    def test_all_model_read_and_write_boundaries_reuse_single_exact_path_guard(self):
        boundaries = (build_request, validate, owner_request,
                      public_packet, verify_anonymous_public_source,
                      GitHub.owner_model_write)
        for fn in boundaries:
            with self.subTest(fn=fn.__qualname__):
                self.assertIn("model_source_path_allowed", inspect.getsource(fn))

    def test_original_owner_selects_one_target_without_new_scheduler(self):
        src=inspect.getsource(run_original_free_reasoner_once)
        self.assertIn("original_canonical_db(db, db_path)",src)
        self.assertIn("select_bounded_free_lane(_attempts(owner))",src)
        self.assertIn("(WINGLESS_R8_PARENT, WINGLESS_R8_TRAINING)",src)
        self.assertIn('(g29.PARENT, "yggdrasil/public_causal_cells.py")',src)
        self.assertIn("SingleOwner",src)
        self.assertIn("reasoner_proposal_once(",src)
        self.assertNotIn("codex exec",src)
        self.assertNotIn("Start-ScheduledTask",src)


if __name__ == "__main__":
    unittest.main()
