"""V19 original draft source preflight: original SQLite and Git are fakes."""
from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from f139.local_controller import SingleOwner
from f139.nci04_autonomy_feed import (
    POLICY_SCHEMA, TITLE_PREFIX,
)
from f139.nci04_model_owner_publication import ModelDraftDenied
from f139.nci04_v19_original_publication_preflight_no_write import (
    ShadowDenied, preflight_original_v19_candidate_without_writing,
)
from test_nci04_v19_original_proposal_validation_custody import (
    OriginalProposalValidationCustodyTests,
)


class OriginalDraftPreflightTests(unittest.TestCase):
    def setUp(self):
        source = OriginalProposalValidationCustodyTests(
            "test_real_original_send_to_validated_candidate_and_cold_reopen")
        source.setUp()
        self.addCleanup(source.doCleanups)
        self.stage = source
        self.db = source.db
        self.mutex = source.mutex
        self.public_reader = source.fixture.source.reader_fixture.public_reader
        self.route_log = []
        self.branch_taken = False
        self.policy_enabled = True
        self.owner_source = self.db.meta()["source_sha"]

    def original_get(self, route):
        self.route_log.append(route)
        if route == "repos/spoonman136668-ai/FORGE/issues/807":
            policy = {
                "schema": POLICY_SCHEMA,
                "enabled": self.policy_enabled,
                "source_sha": self.owner_source,
                "title_prefix": TITLE_PREFIX,
                "lanes": ["Wingless", "Yggdrasil"],
                "max_issue_creations_per_cycle": 2,
                "require_owner_authored_pr": True,
                "require_single_head_commit_delta": True,
                "require_single_allowed_source_file": True,
                "scientific_first_use": False,
                "paid_model_calls": 0,
                "accepted_ref_mutations": 0,
                "new_controller": False,
                "new_scheduler": False,
                "new_queue": False,
            }
            return {
                "number": 807, "state": "open",
                "user": {"login": "spoonman136668-ai"},
                "author_association": "OWNER", "body": json.dumps(policy),
            }
        if route == "repos/spoonman136668-ai/FORGE/branches/main":
            return {
                "protected": True, "commit": {"sha": self.owner_source},
            }
        if "/git/matching-refs/heads/f139/auto-model-" in route:
            return [{"ref": "occupied"}] if self.branch_taken else []
        if "/pulls?state=all&per_page=100&page=1" in route:
            return []
        raise AssertionError("Unexpected remote read " + route)

    def stage_candidate(self):
        send = self.stage.prepared_response()
        with SingleOwner(self.mutex):
            saved = self.stage.validate(send)
        self.assertEqual(saved["disposition"], "ORIGINAL_PROPOSAL_VALIDATED_DATA_ONLY")
        return saved

    def preflight(self, saved, *, source=None, packet=None,
                  getter=None, reader=None, owner=None):
        return preflight_original_v19_candidate_without_writing(
            self.db,
            validation_seq=saved["validation_event_seq"],
            validation_sha256=saved["validation_event_sha256"],
            candidate_source=(
                saved["candidate"]["candidate_source"] if source is None else source),
            public_packet=(
                self.stage.fixture.source.packet if packet is None else packet),
            original_get=self.original_get if getter is None else getter,
            public_reader=self.public_reader if reader is None else reader,
            owner_witness=(lambda: True) if owner is None else owner,
        )

    def test_exact_original_candidate_compiles_native_draft_no_write(self):
        saved = self.stage_candidate()
        with SingleOwner(self.mutex), patch(
                "f139.nci04_free_reasoner_provider._post_one",
                side_effect=AssertionError("MODEL POST FORBIDDEN")):
            old = self.db.meta().copy()
            receipt = self.preflight(saved)
            self.assertEqual(receipt["disposition"],
                             "SOURCE_AND_ORIGINAL_PUBLICATION_PREFLIGHT_ONLY")
            self.assertEqual(receipt["lane"], "Wingless")
            self.assertEqual(receipt["original_validation_sha256"],
                             saved["validation_event_sha256"])
            self.assertEqual(receipt["candidate_identity"],
                             saved["candidate"]["candidate_identity"])
            self.assertEqual(receipt["source_after_sha256"],
                             saved["candidate"]["source_after_sha256"])
            self.assertTrue(receipt["branch"].startswith("f139/auto-model-w-"))
            self.assertEqual(receipt["provider_requests"], 0)
            self.assertEqual(receipt["original_write_calls"], 0)
            self.assertFalse(receipt["publication_authorized"])
            self.assertFalse(receipt["scientific_first_use"])
            self.assertFalse(receipt["worker_dispatched"])
            self.assertFalse(receipt["accepted_ref_mutations"])
            self.assertEqual(self.db.meta(), old)
            self.db.verify()
            self.assertEqual(len(self.stage.fixture.calls), 1)
        self.assertEqual(sum("/pulls?state=all" in x for x in self.route_log), 2)

    def test_ref_occupied_denies_before_write(self):
        saved = self.stage_candidate()
        self.branch_taken = True
        with SingleOwner(self.mutex):
            old = self.db.meta().copy()
            with self.assertRaisesRegex(ModelDraftDenied,
                                         "REF_ALREADY_EXISTS"):
                self.preflight(saved)
            self.assertEqual(self.db.meta(), old)

    def test_disabled_original_owner_policy_denied(self):
        saved = self.stage_candidate()
        self.policy_enabled = False
        with SingleOwner(self.mutex):
            old = self.db.meta().copy()
            with self.assertRaises(Exception):
                self.preflight(saved)
            self.assertEqual(self.db.meta(), old)

    def test_modified_candidate_bytes_denied_before_remote_reads(self):
        saved = self.stage_candidate()
        self.route_log = []
        with SingleOwner(self.mutex):
            with self.assertRaisesRegex(
                    ShadowDenied, "MODEL_CANDIDATE_BYTES_OR_SOURCE_DRIFT"):
                self.preflight(saved, source=b"forged source")
            self.assertEqual(self.route_log, [])

    def test_wrong_public_tree_or_history_denied_before_remote_reads(self):
        saved = self.stage_candidate()
        packet = {**self.stage.fixture.source.packet,
                  "target_tree_sha": "f" * 40}
        with SingleOwner(self.mutex):
            with self.assertRaisesRegex(
                    ShadowDenied, "VALIDATED_PUBLIC_SOURCE_SCOPE_DRIFT"):
                self.preflight(saved, packet=packet)
            self.assertEqual(self.route_log, [])

    def test_original_mutex_and_owner_witness_required(self):
        saved = self.stage_candidate()
        with self.assertRaisesRegex(
                ShadowDenied, "ORIGINAL_INPUT_OWNER_MUTEX_OR_WITNESS"):
            self.preflight(saved)
        with SingleOwner(self.mutex):
            with self.assertRaisesRegex(
                    ShadowDenied, "ORIGINAL_INPUT_OWNER_MUTEX_OR_WITNESS"):
                self.preflight(saved, owner=lambda: False)

    def test_original_head_moves_refuses_cold_replay_before_remote_reads(self):
        saved = self.stage_candidate()
        with SingleOwner(self.mutex):
            with self.db.transaction():
                self.db.event("SCOPE_MOVED", {"test_only": True})
            self.db.verify()
            old = self.db.meta().copy()
            with self.assertRaisesRegex(
                    ShadowDenied, "VALIDATION_ALREADY_CONSUMED_OR_HEAD_MOVED"):
                self.preflight(saved)
            self.assertEqual(self.db.meta(), old)
            self.assertEqual(self.route_log, [])

    def test_private_or_unavailable_git_refuses_preflight(self):
        saved = self.stage_candidate()
        with SingleOwner(self.mutex):
            old = self.db.meta().copy()
            def absent(route):
                raise FileNotFoundError("simulated public source unavailable")
            with self.assertRaises(Exception):
                self.preflight(saved, reader=absent)
            self.assertEqual(self.db.meta(), old)
            self.assertEqual(self.route_log, [])


if __name__ == "__main__":
    unittest.main()
