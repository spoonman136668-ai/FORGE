"""H73 original owner read-only request/response integration, never publisher.

Authentic frozen Yggdrasil original source bytes are reassembled from pinned
two-recipe fixtures, but all owner SQLite and API activity is in synthetic local
fixtures. This cannot authenticate a running owner or authorize science/dispatch.
"""
from __future__ import annotations

import hashlib
import importlib
import unittest
from pathlib import Path

from f139.nci04_model_free_grammar import method_for
from f139.nci04_model_free_owner_response_shadow import encode_owner_response_shadow
from f139.nci04_model_owner_bridge import OwnerModelDenied, owner_request, owner_response
from f139.test_nci04_genuine_yggdrasil_fixture import FIXTURES, ORIGINAL_SHA256
from f139.test_nci04_model_free_grammar import META
from f139.test_nci04_model_owner_publication import OwnerModelPublicationTests
from test_nci04_owner_ledger import MAIN


class OriginalOwnerSessionModelFreeShadowTests(unittest.TestCase):
    """Exercise original read-only session path without calling publish_model_once."""

    def setUp(self):
        owner = OwnerModelPublicationTests(
            "test_original_owner_single_model_draft_publication_and_no_dispatch")
        owner.setUp()
        self.addCleanup(owner.doCleanups)
        self.db = owner.db
        self.provider = owner.provider
        self.steering = owner.steering

        originals = []
        for name, prior, declared_sha in FIXTURES:
            raw = Path(importlib.import_module(name).__file__).read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(), declared_sha)
            self.assertEqual(len(raw), 7439)
            originals.append((prior, raw))
        first = dict(originals)[1]
        self.original = first.replace(method_for(1).encode("ascii"), b"", 1)
        self.assertEqual(len(self.original), 6067)
        self.assertEqual(hashlib.sha256(self.original).hexdigest(),
                         ORIGINAL_SHA256)
        # Reuse original-owner mock provider, NOT live GitHub; its returned
        # source bytes and target SHA/tree are pinned to a genuine Git fixture.
        self.provider.parent_data = self.original
        self.provider.parent = "5e74f8db85b2f5839c42148c0dfba69a88b1a2c9"
        self.provider.tree = "180008502f6bdfe5a06c3d0d6f47f941dd01f20b"
        self.assertEqual(self.provider.source, MAIN)
        self.assertEqual(self.provider.write_calls, [])
        self.assertEqual(self.db.meta()["source_sha"], MAIN)

    def request(self, witness=lambda: True):
        return owner_request(
            self.db, self.provider.get, self.steering.get,
            source_sha=MAIN, lane="Yggdrasil",
            target_commit=self.provider.parent,
            path=self.provider.path, owner_witness=witness)

    def response(self, snapshot):
        return encode_owner_response_shadow(
            controller_source_sha=MAIN,
            target_commit=self.provider.parent,
            target_tree_sha=self.provider.tree,
            frozen_source_sha256=ORIGINAL_SHA256,
            original=self.original,
            metadata=META,
            complete_history=[],
            owner_history_sha256=snapshot["session"]["history_sha256"],
            owner_consumed_candidates=snapshot["consumed_candidates"],
            owner_consumed_after_hashes=snapshot["consumed_after_hashes"])

    def test_original_readonly_owner_request_response_compiles_finite_candidate(self):
        old = dict(self.db.meta())
        prepared = self.request()
        self.assertEqual(prepared["before"], self.original)
        self.assertEqual(prepared["session"]["target_tree_sha"],
                         self.provider.tree)
        response = self.response(prepared)
        self.assertEqual(len(response["selected"]), 1)
        item = response["selected"][0]
        outcome = owner_response(
            self.db, self.provider.get, self.steering.get,
            session=prepared["session"],
            raw_response=item["model_response_bytes"],
            owner_witness=lambda: True)
        self.assertEqual(outcome["record"]["candidate_identity"],
                         item["owner_candidate_identity"])
        self.assertEqual(outcome["record"]["after_sha256"],
                         item["after_sha256"])
        self.assertEqual(outcome["proposal"]["eligible"], False)
        self.assertEqual(outcome["proposal"]["owner_issue_required"], True)
        self.assertIs(outcome["proposal"]["dispatch_authorized"], False)
        self.assertIs(outcome["publication_authorized"], False)
        self.assertIs(outcome["scientific_first_use"], False)
        self.assertIs(outcome["worker_dispatched"], False)
        self.assertEqual(self.db.meta(), old)
        self.assertEqual(self.provider.write_calls, [])

    def test_original_owner_epoch_event_change_invalidates_shadow_response(self):
        prepared = self.request()
        shadow = self.response(prepared)
        old = dict(self.db.meta())
        with self.db.transaction():
            self.db.event("H73_SYNTHETIC_STALE_OWNER_EVENT", {"negative": True})
        self.assertNotEqual(self.db.meta()["head_hash"], old["head_hash"])
        with self.assertRaisesRegex(OwnerModelDenied, "SESSION_STALE"):
            owner_response(self.db, self.provider.get, self.steering.get,
                           session=prepared["session"],
                           raw_response=shadow["selected"][0]["model_response_bytes"],
                           owner_witness=lambda: True)
        self.assertEqual(self.provider.write_calls, [])
        self.db.verify()

    def test_changed_original_blob_denies_shadow_and_prevents_publication(self):
        prepared = self.request()
        shadow = self.response(prepared)
        self.provider.parent_data = self.original + b"\n# stale source\n"
        with self.assertRaisesRegex(OwnerModelDenied, "SESSION_STALE"):
            owner_response(self.db, self.provider.get, self.steering.get,
                           session=prepared["session"],
                           raw_response=shadow["selected"][0]["model_response_bytes"],
                           owner_witness=lambda: True)
        self.assertEqual(self.provider.write_calls, [])

    def test_missing_original_single_owner_witness_denies_no_mutation(self):
        old = dict(self.db.meta())
        with self.assertRaisesRegex(OwnerModelDenied, "WITNESS_REQUIRED"):
            self.request(witness=lambda: False)
        prepared = self.request()
        shadow = self.response(prepared)
        with self.assertRaisesRegex(OwnerModelDenied, "WITNESS_REQUIRED"):
            owner_response(self.db, self.provider.get, self.steering.get,
                           session=prepared["session"],
                           raw_response=shadow["selected"][0]["model_response_bytes"],
                           owner_witness=lambda: False)
        self.assertEqual(self.provider.write_calls, [])
        self.assertEqual(self.db.meta(), old)


if __name__ == "__main__":
    unittest.main()
