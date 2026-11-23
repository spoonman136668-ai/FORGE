"""Publication across uninstalled main changes; isolated SQLite/fake Git only."""
from __future__ import annotations

import subprocess
import unittest
from unittest.mock import patch

from f139.local_controller import SingleOwner
from f139.nci04_v19_original_publication_preflight_no_write import ShadowDenied
import test_nci04_v19_original_publication_preflight_no_write as preflight_fixture
import test_nci04_v19_original_publication_once as writer_fixture


class OriginalPublicationReleasePinTests(unittest.TestCase):
    def setUp(self):
        self.base = preflight_fixture.OriginalDraftPreflightTests(
            "test_exact_original_candidate_compiles_native_draft_no_write")
        self.base.setUp()
        self.addCleanup(self.base.doCleanups)
        self.db = self.base.db
        self.mutex = self.base.mutex
        self.owner_source = self.base.owner_source

    def advanced_main_get(self, route):
        repo = "repos/spoonman136668-ai/FORGE/"
        if route == repo + "branches/main":
            return {"protected": True, "commit": {"sha": "e" * 40}}
        if route == repo + "branches/f139-owner-release-" + self.owner_source:
            return {"name": "f139-owner-release-" + self.owner_source,
                    "commit": {"sha": self.owner_source}}
        if route == (repo + "compare/" + self.owner_source + "..." + "e" * 40
                     + "?per_page=1&page=2"):
            return {"status": "ahead", "ahead_by": 101, "behind_by": 0,
                    "total_commits": 101,
                    "merge_base_commit": {"sha": self.owner_source}}
        return self.base.original_get(route)

    def clean_original_git(self, args, **kwargs):
        self.assertEqual(args[:2], ["git", "-C"])
        if args[3:] == ["rev-parse", "HEAD"]:
            output = (self.owner_source + "\n").encode()
        elif args[3:] == ["status", "--porcelain", "--untracked-files=all"]:
            output = b""
        else:
            raise AssertionError("Not a read-only original-source check: " + str(args))
        return subprocess.CompletedProcess(args, 0, stdout=output, stderr=b"")

    def test_pinned_original_draft_survives_uninstalled_main_advance(self):
        saved = self.base.stage_candidate()
        with SingleOwner(self.mutex), patch(
                "f139.local_controller.subprocess.run", self.clean_original_git):
            before = self.db.meta().copy()
            receipt = self.base.preflight(saved, getter=self.advanced_main_get)
            self.assertEqual(receipt["disposition"],
                             "SOURCE_AND_ORIGINAL_PUBLICATION_PREFLIGHT_ONLY")
            self.assertEqual(receipt["original_owner_source_sha"], self.owner_source)
            self.assertFalse(receipt["publication_authorized"])
            self.assertEqual(receipt["original_write_calls"], 0)
            self.assertEqual(self.db.meta(), before)

    def test_advanced_main_cannot_hide_dirty_or_replaced_original_checkout(self):
        saved = self.base.stage_candidate()
        for dirty in (False, True):
            def git(args, **kwargs):
                result = self.clean_original_git(args, **kwargs)
                if dirty and args[3] == "status":
                    result.stdout = b" M f139/local_controller.py\n"
                if not dirty and args[3] == "rev-parse":
                    result.stdout = b"f" * 40 + b"\n"
                return result
            with self.subTest(dirty=dirty), SingleOwner(self.mutex), patch(
                    "f139.local_controller.subprocess.run", git):
                before = self.db.meta().copy()
                with self.assertRaisesRegex(ShadowDenied, "ORIGINAL_RELEASE_PIN"):
                    self.base.preflight(saved, getter=self.advanced_main_get)
                self.assertEqual(self.db.meta(), before)

    def test_advanced_main_requires_exact_worker_pin_and_forward_ancestry(self):
        saved = self.base.stage_candidate()
        for defect in ("worker", "ancestry"):
            def getter(route):
                doc = self.advanced_main_get(route)
                if defect == "worker" and "/branches/f139-owner-release-" in route:
                    doc["commit"]["sha"] = "e" * 40
                if defect == "ancestry" and "/compare/" in route:
                    doc["status"] = "diverged"
                    doc["behind_by"] = 1
                return doc
            with self.subTest(defect=defect), SingleOwner(self.mutex), patch(
                    "f139.local_controller.subprocess.run", self.clean_original_git):
                before = self.db.meta().copy()
                with self.assertRaisesRegex(ShadowDenied, "ORIGINAL_RELEASE_PIN"):
                    self.base.preflight(saved, getter=getter)
                self.assertEqual(self.db.meta(), before)

    def test_owner_policy_revocation_during_release_proof_denies_publication(self):
        saved = self.base.stage_candidate()
        policy_reads = 0
        def getter(route):
            nonlocal policy_reads
            if route.endswith("/issues/807"):
                policy_reads += 1
                if policy_reads > 1:
                    self.base.policy_enabled = False
            return self.advanced_main_get(route)
        with SingleOwner(self.mutex), patch(
                "f139.local_controller.subprocess.run", self.clean_original_git):
            before = self.db.meta().copy()
            with self.assertRaisesRegex(ShadowDenied, "ORIGINAL_RELEASE_PIN"):
                self.base.preflight(saved, getter=getter)
            self.assertEqual(self.db.meta(), before)

    def test_main_movement_during_release_proof_denies_publication(self):
        saved = self.base.stage_candidate()
        comparisons = 0
        def getter(route):
            nonlocal comparisons
            doc = self.advanced_main_get(route)
            if "/compare/" in route:
                comparisons += 1
            if route.endswith("/branches/main") and comparisons >= 2:
                doc["commit"]["sha"] = "f" * 40
            return doc
        with SingleOwner(self.mutex), patch(
                "f139.local_controller.subprocess.run", self.clean_original_git):
            before = self.db.meta().copy()
            with self.assertRaisesRegex(ShadowDenied, "ORIGINAL_RELEASE_PIN"):
                self.base.preflight(saved, getter=getter)
            self.assertEqual(self.db.meta(), before)

    def test_publication_still_commits_before_fake_write_and_cannot_replay(self):
        stage = writer_fixture.OriginalV19OnceWriterTests(
            "test_fake_only_success_attempt_precedes_remote_and_cold_verifies")
        stage.setUp()
        self.addCleanup(stage.doCleanups)
        saved = stage.candidate()
        with SingleOwner(stage.mutex), patch(
                "f139.local_controller.subprocess.run", self.clean_original_git), patch(
                "f139.nci04_v19_original_publication_once._write_draft",
                side_effect=stage.fake_authenticated_write):
            result = stage.writer(saved, getter=self.advanced_main_get)
            self.assertEqual(result["disposition"], "MODEL_DRAFT_AUTHENTICATED")
            self.assertEqual(stage.count("MODEL_DRAFT_ATTEMPTED"), 1)
            self.assertEqual(stage.count("MODEL_DRAFT_AUTHENTICATED"), 1)
            self.assertEqual(len(stage.remote_calls), 1)
            with self.assertRaisesRegex(ShadowDenied, "VALIDATION_ALREADY_CONSUMED"):
                stage.writer(saved, getter=self.advanced_main_get)
            self.assertEqual(len(stage.remote_calls), 1)
