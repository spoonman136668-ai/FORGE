"""Synthetic non-activation negative controls for the fresh F139 epoch.

They exercise deterministic exclusion/replay classification, not a native
Windows task, real original event1864, GitHub remote authority or training.
"""
from __future__ import annotations

import base64
import copy
import unittest

from f139.nci04_native_contract import canonical
from f139.nci04_autonomy_feed import candidate_identity
from f139.nci04_fresh_dev_exclusions import (
    SCHEMA, FreshExclusionsDenied, derive_exclusions,
    candidate_violates_frozen_exclusions,
)
from f139.nci04_v59_owner_forward_readiness import SOURCE, HEAD_SEQ, HEAD_SHA256

TARGET = "a" * 40
AFTER = "b" * 64
NEW_AFTER = "c" * 64
MODEL_AFTER = "d" * 64
PATH = "yggdrasil/public_causal_cells.py"


class FrozenConsumedWorkTests(unittest.TestCase):
    def setUp(self):
        intent = canonical({
            "lane": "Yggdrasil", "target_commit": TARGET,
            "path": PATH, "after_sha256": AFTER,
        })
        native = {
            "kind": "NATIVE_DEVELOPMENT_ADMITTED",
            "payload": {
                "issue_number": 1715, "issue_id": 20315,
                "ticket": "f139-nci04-i1715-consumed",
                "lane": "Yggdrasil",
                "native_target_commit": TARGET,
                "native_path": PATH,
                "after_sha256": AFTER,
                "native_intent_base64":
                    base64.b64encode(intent).decode("ascii"),
            },
        }
        self.native = native
        self.model = {
            "kind": "MODEL_DRAFT_ATTEMPTED",
            "payload": {"candidate_identity": "e" * 64,
                        "source_after_sha256": MODEL_AFTER},
        }
        self.d2k = {
            "kind": "DEVELOPMENT_WORK_ADMITTED",
            "payload": {"issue_number": 687, "issue_id": 1687,
                        "ticket": "f139-d2k-i687-old"},
        }
        self.g3 = {"kind": "G3_DRAFT_ATTEMPTED", "payload": {}}
        self.events = [native, self.model, self.d2k, self.g3] + [
            {"kind": "D2K_RETAINED_OTHER", "payload": {}}
            for _ in range(HEAD_SEQ - 4)
        ]
        self.tasks = [
            "f139-nci04-i1715-consumed", "f139-d2k-i687-old", "old-negative",
        ]
        self.history = self.freeze()

    def freeze(self, *, events=None, tasks=None, source=None, head=None):
        return derive_exclusions(
            source_sha=SOURCE if source is None else source,
            head_seq=HEAD_SEQ,
            head_hash=HEAD_SHA256 if head is None else head,
            events=self.events if events is None else events,
            tasks=self.tasks if tasks is None else tasks,
        )

    def fresh_candidate(self, **kw):
        fields = {
            "issue_number": 3001,
            "issue_id": 400000,
            "ticket": "f139-nci04-i3001-fresh",
            "lane": "Yggdrasil",
            "target_commit": TARGET,
            "path": PATH,
            "after_sha256": NEW_AFTER,
            "authenticated_remote_issue_floor": 3000,
        }
        fields.update(kw)
        return candidate_violates_frozen_exclusions(
            self.history, **fields)

    def test_frozen_history_preserves_all_prior_identifiers(self):
        got = self.history
        self.assertEqual(got["schema"], SCHEMA)
        self.assertEqual(got["original_event_count"], HEAD_SEQ)
        self.assertEqual(got["original_task_count"], 3)
        self.assertEqual(got["native_admission_count"], 1)
        self.assertEqual(got["model_draft_attempt_count"], 1)
        self.assertEqual(got["other_historical_remote_attempt_count"], 1)
        self.assertEqual(got["old_issue_numbers"], [687, 1715])
        self.assertEqual(got["old_issue_ids"], [1687, 20315])
        self.assertEqual(got["old_tickets"], sorted(self.tasks))
        semantic = candidate_identity("Yggdrasil", TARGET, PATH, AFTER)
        self.assertEqual(got["old_native_candidate_identities"], [semantic])
        self.assertEqual(got["old_source_after_sha256"],
                         sorted([AFTER, MODEL_AFTER]))
        self.assertEqual(got["old_model_candidate_identities"], ["e" * 64])
        self.assertFalse(got["release_qualified"])
        self.assertFalse(got["fresh_activation_authorized"])
        self.assertFalse(got["remote_issue_high_water_verified"])
        self.assertFalse(got["previous_work_replay_authorized"])
        self.assertEqual(canonical(got), canonical(self.freeze()))

    def test_rejects_old_issue_number_id_ticket_and_content(self):
        self.assertTrue(self.fresh_candidate(issue_number=1715))
        self.assertTrue(self.fresh_candidate(issue_id=1687))
        self.assertTrue(self.fresh_candidate(ticket="old-negative"))
        self.assertTrue(self.fresh_candidate(after_sha256=AFTER))
        self.assertTrue(self.fresh_candidate(after_sha256=MODEL_AFTER))

    def test_remote_high_water_fails_closed_without_positive_admission(self):
        self.assertTrue(self.fresh_candidate(authenticated_remote_issue_floor=None))
        self.assertTrue(self.fresh_candidate(authenticated_remote_issue_floor=1700))
        self.assertTrue(self.fresh_candidate(issue_number=3000))
        # Only means it was not an EXACT known replay; it grants no
        # GitHub issue authenticity, owner-task rebind or native activation.
        self.assertFalse(self.fresh_candidate())

    def test_invalid_history_flags_are_never_considered(self):
        for key, value in (
            ("release_qualified", True),
            ("fresh_activation_authorized", True),
            ("source_sha", "f" * 40),
            ("original_head_sha256", "f" * 64),
        ):
            with self.subTest(key=key):
                bad = dict(self.history)
                bad[key] = value
                with self.assertRaisesRegex(
                        FreshExclusionsDenied, "FROZEN_HISTORY_INVALID"):
                    candidate_violates_frozen_exclusions(
                        bad, issue_number=3001, issue_id=400000,
                        ticket="f139-nci04-i3001-fresh", lane="Yggdrasil",
                        target_commit=TARGET, path=PATH,
                        after_sha256=NEW_AFTER,
                        authenticated_remote_issue_floor=3000)

    def test_frozen_head_or_missing_event_rejected(self):
        with self.assertRaisesRegex(
                FreshExclusionsDenied, "ORIGINAL_HEAD_OR_INPUT_DRIFT"):
            self.freeze(head="f" * 64)
        with self.assertRaisesRegex(
                FreshExclusionsDenied, "ORIGINAL_HEAD_OR_INPUT_DRIFT"):
            self.freeze(events=self.events[:-1])

    def test_bad_native_semantic_intent_rejected(self):
        bad = copy.deepcopy(self.events)
        bad[0]["payload"]["after_sha256"] = NEW_AFTER
        with self.assertRaisesRegex(
                FreshExclusionsDenied, "NATIVE_INTENT_SEMANTIC_DRIFT"):
            self.freeze(events=bad)

    def test_incomplete_model_draft_rejected(self):
        bad = copy.deepcopy(self.events)
        del bad[1]["payload"]["source_after_sha256"]
        with self.assertRaisesRegex(
                FreshExclusionsDenied, "MODEL_ATTEMPT_IDENTITY_INCOMPLETE"):
            self.freeze(events=bad)

    def test_duplicate_ticket_and_foreign_issue_type_rejected(self):
        with self.assertRaisesRegex(
                FreshExclusionsDenied, "DUPLICATE_ORIGINAL_TASK"):
            self.freeze(tasks=["duplicate", "duplicate"])
        bad = copy.deepcopy(self.events)
        bad[0]["payload"]["issue_number"] = True
        with self.assertRaisesRegex(
                FreshExclusionsDenied, "ISSUE_NUMBER_INVALID"):
            self.freeze(events=bad)

    def test_no_original_mutation_or_remote_execution_effect(self):
        self.assertIsNone(self.history.get("worker_dispatched"))
        self.assertEqual(self.history["paid_model_calls"], 0)
        self.assertEqual(self.history["owner_task_mutations"], 0)
        self.assertFalse(self.history["scientific_first_use"])


if __name__ == "__main__":
    unittest.main()
