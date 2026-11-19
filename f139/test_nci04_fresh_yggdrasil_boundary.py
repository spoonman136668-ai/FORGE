"""Synthetic read-only exact-Yggdrasil source and no-replay preflight tests."""
from __future__ import annotations

import base64
from dataclasses import replace
import hashlib
import json
import unittest
from unittest.mock import patch

from f139.nci04_native_contract import Candidate, canonical
from f139.nci04_owner_issue import NativeIssue
from f139.nci04_fresh_dev_exclusions import SCHEMA as EXCLUSION_SCHEMA
from f139.nci04_v59_owner_forward_readiness import (
    SOURCE, HEAD_SEQ, HEAD_SHA256,
)
from f139.nci04_fresh_yggdrasil_boundary import (
    ACCEPTED, AMALGAM_HEAD, AMALGAM_PR, LINEAGE_HEAD, LINEAGE_PR,
    LINEAGE_RECEIPT_BLOB, LINEAGE_RECEIPT_PATH,
    ACCEPTED_NATIVE_BLOB, ACCEPTED_NATIVE_PATH, RECEIPT_SCHEMA,
    FreshYggdrasilBoundaryDenied, _content,
    preflight_new_yggdrasil_development_issue,
    read_yggdrasil_research_boundary,
)

TARGET = "d" * 40
AFTER = "e" * 64
SHARED = "f" * 64


class YggdrasilBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.archive = {
            "schema": "yggdrasil.lineage01.research-artifact-custody-audit.v1",
            "status": "VERIFIED_ARCHIVED_DRAFT_EXPERIMENTAL_CHECKPOINT_ONLY",
            "git": {
                "accepted_main_sha": ACCEPTED,
                "research_amalgam_pr": AMALGAM_PR,
                "research_amalgam_head_sha": AMALGAM_HEAD,
            },
            "scientific_and_owner_limits": {
                "official_owner_checkpoint_identified": False,
                "accepted_model_training_continuity": "UNVERIFIED",
                "original_amalgam_transfer_result": "DEV_NO_GO",
                "authorized_original_source_first_use": False,
                "accepted_ref_changed": False,
                "model_merged_or_deployed": False,
            },
        }
        self.files = {
            ACCEPTED_NATIVE_PATH: b"def make_empty_native(): pass\n",
            LINEAGE_RECEIPT_PATH: canonical(self.archive),
        }
        self.prs = {
            number: {
                "number": number, "state": "open", "draft": True,
                "merged_at": None,
                "head": {
                    "sha": head, "repo": {"full_name": "spoonman136668-ai/Yggdrasil"},
                },
                "base": {
                    "repo": {"full_name": "spoonman136668-ai/Yggdrasil"},
                },
            }
            for number, head in (
                (AMALGAM_PR, AMALGAM_HEAD), (LINEAGE_PR, LINEAGE_HEAD)
            )
        }
        self.branch = {
            "name": "main", "protected": True, "commit": {"sha": ACCEPTED},
        }
        self.compares = {
            AMALGAM_HEAD: {
                "status": "ahead", "ahead_by": 325, "behind_by": 0,
                "merge_base_commit": {"sha": ACCEPTED},
            },
            LINEAGE_HEAD: {
                "status": "ahead", "ahead_by": 15, "behind_by": 0,
                "merge_base_commit": {"sha": ACCEPTED},
            },
        }
        # Testing read_yggdrasil_research_boundary's branch, PR, compare and
        # archive predicates with a stubbed _content. Actual Git blob SHA1,
        # base64 and byte-size readback are tested separately.
        self.reader = patch(
            "f139.nci04_fresh_yggdrasil_boundary._content",
            side_effect=lambda get, path, ref, blob: self.files[path])
        self.reader.start()
        self.addCleanup(self.reader.stop)

    def get(self, route):
        base = "repos/spoonman136668-ai/Yggdrasil/"
        self.assertTrue(route.startswith(base))
        relative = route[len(base):]
        if relative == "branches/main":
            return self.branch
        if relative.startswith("pulls/"):
            return self.prs[int(relative.split("/")[1])]
        if relative.startswith("compare/"):
            return self.compares[relative.split("...")[1]]
        raise AssertionError("unexpected source read")

    def test_verified_boundary_is_research_only(self):
        doc = read_yggdrasil_research_boundary(self.get)
        self.assertEqual(doc["schema"], RECEIPT_SCHEMA)
        self.assertEqual(doc["accepted_main_source_sha"], ACCEPTED)
        self.assertEqual(doc["amalgam_draft_head_sha"], AMALGAM_HEAD)
        self.assertEqual(doc["lineage_draft_head_sha"], LINEAGE_HEAD)
        self.assertEqual(doc["checkpoint_kind"], "DRAFT_EXPERIMENTAL_ONLY")
        self.assertEqual(doc["official_cumulative_owner_checkpoint"], "UNVERIFIED")
        for key in ("release_qualified", "model_continuation_authorized",
                    "owner_task_rebind_authorized", "checkpoint_imported",
                    "worker_dispatched", "new_canonical_learner",
                    "scientific_first_use"):
            self.assertIs(doc[key], False, key)
        self.assertEqual(doc["new_training_actions"], 0)
        self.assertEqual(doc, read_yggdrasil_research_boundary(self.get))

    def test_accepted_main_move_rejected(self):
        self.branch["commit"]["sha"] = "0" * 40
        with self.assertRaisesRegex(
                FreshYggdrasilBoundaryDenied, "ACCEPTED_MAIN_MOVED"):
            read_yggdrasil_research_boundary(self.get)

    def test_amalgam_or_lineage_merge_or_head_move_rejected(self):
        for number in (AMALGAM_PR, LINEAGE_PR):
            for change in ("merged_at", "head", "draft"):
                with self.subTest(number=number, change=change):
                    old = self.prs[number]
                    mutated = dict(old)
                    mutated[change] = (
                        "2026-11-19" if change == "merged_at" else
                        {"sha": "0" * 40, "repo": {"full_name":
                         "spoonman136668-ai/Yggdrasil"}}
                        if change == "head" else False)
                    self.prs[number] = mutated
                    try:
                        with self.assertRaisesRegex(
                                FreshYggdrasilBoundaryDenied,
                                "DRAFT_RESEARCH_OWNER_OR_HEAD_DRIFT"):
                            read_yggdrasil_research_boundary(self.get)
                    finally:
                        self.prs[number] = old

    def test_non_descendant_research_branch_rejected(self):
        original = self.compares[LINEAGE_HEAD]
        self.compares[LINEAGE_HEAD] = {
            **original, "behind_by": 1,
        }
        with self.assertRaisesRegex(
                FreshYggdrasilBoundaryDenied, "NOT_DESCENDANT"):
            read_yggdrasil_research_boundary(self.get)

    def test_archived_checkpoint_is_not_canonical_training_authority(self):
        for key, value in (
            ("official_owner_checkpoint_identified", True),
            ("accepted_model_training_continuity", "VERIFIED"),
            ("original_amalgam_transfer_result", "PASS"),
            ("authorized_original_source_first_use", True),
        ):
            with self.subTest(key=key):
                copy = json.loads(json.dumps(self.archive))
                copy["scientific_and_owner_limits"][key] = value
                self.files[LINEAGE_RECEIPT_PATH] = canonical(copy)
                with self.assertRaisesRegex(
                        FreshYggdrasilBoundaryDenied,
                        "DRAFT_ARCHIVE_MISCLASSIFIED_AS_ACCEPTED"):
                    read_yggdrasil_research_boundary(self.get)
        self.files[LINEAGE_RECEIPT_PATH] = canonical(self.archive)

    def test_actual_file_git_blob_sha1_and_base64_identity(self):
        body = b"archival read-only proof fixture\n"
        blob = hashlib.sha1(
            b"blob " + str(len(body)).encode("ascii") + b"\0" + body
        ).hexdigest()
        expected = {
            "type": "file", "sha": blob, "encoding": "base64",
            "size": len(body),
            "content": base64.b64encode(body).decode("ascii"),
        }
        with patch(
            "f139.nci04_fresh_yggdrasil_boundary._content", wraps=_content
        ):
            self.assertEqual(
                _content(lambda route: expected, "file.json", ACCEPTED, blob),
                body)
            with self.assertRaisesRegex(
                    FreshYggdrasilBoundaryDenied, "FILE_BYTES_OR_GIT_BLOB_DRIFT"):
                _content(
                    lambda route: {**expected, "content":
                        base64.b64encode(b"modified").decode("ascii")},
                    "file.json", ACCEPTED, blob)

    def make_issue(self):
        candidate = Candidate(
            intent_sha256="a" * 64, qualification_key="b" * 64,
            target_commit=ACCEPTED, target_tree_sha="c" * 40,
            path=ACCEPTED_NATIVE_PATH,
            before_sha256=SHARED, after_sha256=AFTER,
            after_bytes=b"x", lane="Yggdrasil")
        return NativeIssue(
            number=3001, issue_id=913001,
            ticket="f139-nci04-i3001-first",
            lane="Yggdrasil", source_sha=TARGET,
            issue_body_sha256="c" * 64,
            native_intent_sha256="a" * 64,
            qualification_key="b" * 64,
            intent_raw=b"{}",
            candidate=candidate)

    def history(self):
        return {
            "schema": EXCLUSION_SCHEMA, "source_sha": SOURCE,
            "original_head_seq": HEAD_SEQ,
            "original_head_sha256": HEAD_SHA256,
            "release_qualified": False,
            "fresh_activation_authorized": False,
            "old_issue_numbers": [1715],
            "old_issue_ids": [1715001],
            "old_tickets": ["old-ticket"],
            "old_native_candidate_identities": [],
            "old_source_after_sha256": ["9" * 64],
        }

    def inspect(self, issue=None, history=None, boundary=None, floor=3000):
        return preflight_new_yggdrasil_development_issue(
            self.make_issue() if issue is None else issue,
            controller_source_sha=TARGET,
            consumed_history=self.history() if history is None else history,
            research_boundary=(
                read_yggdrasil_research_boundary(self.get)
                if boundary is None else boundary),
            authenticated_remote_issue_floor=floor)

    def test_fresh_eligible_issue_still_has_no_activation_authority(self):
        proof = self.inspect()
        self.assertFalse(proof["owner_activation_authorized"])
        self.assertFalse(proof["worker_dispatch_authorized"])
        self.assertFalse(proof["new_canonical_learner"])
        self.assertEqual(proof["accepted_yggdrasil_main_sha"], ACCEPTED)

    def test_rejects_consumed_issue_ticket_and_candidate(self):
        old = self.history()
        old["old_issue_ids"] = [913001]
        with self.assertRaisesRegex(
                FreshYggdrasilBoundaryDenied, "OLD_WORK"):
            self.inspect(history=old)
        old = self.history()
        old["old_tickets"] = [self.make_issue().ticket]
        with self.assertRaisesRegex(
                FreshYggdrasilBoundaryDenied, "OLD_WORK"):
            self.inspect(history=old)
        old = self.history()
        old["old_source_after_sha256"] = [AFTER]
        with self.assertRaisesRegex(
                FreshYggdrasilBoundaryDenied, "OLD_WORK"):
            self.inspect(history=old)

    def test_old_floor_is_not_new_issue_authority(self):
        for floor in (None, 1700, 3001):
            with self.subTest(floor=floor):
                with self.assertRaisesRegex(
                        FreshYggdrasilBoundaryDenied,
                        "FLOOR|OLD_WORK"):
                    self.inspect(floor=floor)

    def test_cannot_target_amalgam_checkpoint_branch_or_other_lane(self):
        issue = self.make_issue()
        for variant in (
            replace(issue, candidate=replace(
                issue.candidate, target_commit=AMALGAM_HEAD)),
            replace(issue, candidate=replace(
                issue.candidate, path=LINEAGE_RECEIPT_PATH)),
            replace(issue, lane="Wingless"),
        ):
            with self.assertRaisesRegex(
                    FreshYggdrasilBoundaryDenied,
                    "NOT_A_NEW_ACCEPTED_BASELINE"):
                self.inspect(issue=variant)

    def test_modified_boundary_flags_are_rejected(self):
        original = read_yggdrasil_research_boundary(self.get)
        for name, value in (
            ("model_continuation_authorized", True),
            ("release_qualified", True),
            ("official_cumulative_owner_checkpoint", "VERIFIED"),
            ("accepted_main_source_sha", "0" * 40),
        ):
            bad = dict(original)
            bad[name] = value
            with self.subTest(name=name):
                with self.assertRaisesRegex(
                        FreshYggdrasilBoundaryDenied,
                        "RESEARCH_BOUNDARY_NOT_AUTHENTICATED"):
                    self.inspect(boundary=bad)


if __name__ == "__main__":
    unittest.main()
