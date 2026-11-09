"""Exact workflow engineering admission only; no GitHub writes or owner access."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from scripts import check_rar_g145_pr_scope as guard


class HybridWorkflowReleaseScopeTests(unittest.TestCase):
    def setUp(self):
        self.head, self.base = "c" * 40, "b" * 40
        self.request = {
            "number": 1642, "author_association": "OWNER",
            "user": {"login": "spoonman136668-ai"},
            "head": {"sha": self.head, "ref": guard.HYBRID_RELEASE_BRANCH,
                     "repo": {"full_name": guard.REPO}},
            "base": {"sha": self.base, "ref": "main",
                     "repo": {"full_name": guard.REPO}},
        }
        self.reads = {
            ("merge-base", self.base, self.head): self.base,
            ("merge-base", guard.HYBRID_RELEASE_ANCHOR, self.base): guard.HYBRID_RELEASE_ANCHOR,
            ("diff", "--no-renames", "--name-only", self.base, self.head): guard.HYBRID_WORKER_PATH,
            ("ls-tree", self.base, "--", guard.HYBRID_WORKER_PATH): self.entry(guard.HYBRID_WORKER_BEFORE),
            ("ls-tree", self.head, "--", guard.HYBRID_WORKER_PATH): self.entry(guard.HYBRID_WORKER_AFTER),
        }

    def entry(self, blob, mode="100644"):
        return mode + " blob " + blob + "\t" + guard.HYBRID_WORKER_PATH

    def admit(self, *, request=None, branch=None, number=1642, reads=None):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "event.json"
            path.write_text(json.dumps({"number": number, "pull_request":
                self.request if request is None else request}), encoding="utf-8")
            env = {"GITHUB_EVENT_PATH": str(path), "GITHUB_EVENT_NAME": "pull_request",
                   "GITHUB_HEAD_REF": branch or guard.HYBRID_RELEASE_BRANCH,
                   "GITHUB_BASE_REF": "main"}
            with patch.dict(os.environ, env):
                table = self.reads if reads is None else reads
                return guard.admit_original_pr(self.head, lambda *args: table[args])

    def test_only_exact_original_worker_transition_qualifies(self):
        self.assertEqual(self.admit(), "EXACT_PR1642_HYBRID_WORKER_BLOB_QUALIFICATION_ONLY")
        guard.negative_controls()  # Also runs inside both full Go qualifiers.

    def test_foreign_pr_owner_or_event_identity_denied(self):
        for field, value in (("number", 1643), ("number", True),
                             ("user", {"login": "other"}), ("user", None),
                             ("author_association", "CONTRIBUTOR")):
            request = dict(self.request, **{field: value})
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                self.admit(request=request)
        with self.assertRaises(ValueError):
            self.admit(number=1643)
        for side in ("head", "base"):
            request = copy.deepcopy(self.request)
            request[side]["repo"]["full_name"] = "other/FORGE"
            with self.subTest(side=side), self.assertRaises(ValueError):
                self.admit(request=request)

    def test_wrong_branch_does_not_gain_workflow_permission(self):
        request = copy.deepcopy(self.request)
        request["head"]["ref"] = "release/unapproved-copy"
        with self.assertRaisesRegex(ValueError, "GENERIC_PR_CHANGED_OR_UNRELATED_HARNESS"):
            self.admit(request=request, branch=request["head"]["ref"])
        self.assertFalse(guard.generic_paths_safe([guard.HYBRID_WORKER_PATH]))
        self.assertFalse(guard.generic_paths_safe([".github/workflows/other.yml"]))
        self.assertFalse(guard.generic_paths_safe(["scripts/check_rar_g145_pr_scope.py"]))

    def test_new_blob_mode_old_blob_and_replay_denied(self):
        for ref, entry in ((self.head, self.entry("f" * 40)),
                           (self.head, self.entry(guard.HYBRID_WORKER_AFTER, "100755")),
                           (self.base, self.entry("f" * 40)),
                           (self.base, self.entry(guard.HYBRID_WORKER_AFTER))):
            reads = dict(self.reads)
            reads[("ls-tree", ref, "--", guard.HYBRID_WORKER_PATH)] = entry
            with self.subTest(ref=ref, entry=entry), self.assertRaisesRegex(ValueError, "EXACT_SOURCE_REQUIRED"):
                self.admit(reads=reads)

    def test_extra_file_rename_delete_or_empty_delta_denied(self):
        for changed in ("", "docs/instead.md", guard.HYBRID_WORKER_PATH + "\nother.py",
                        guard.HYBRID_WORKER_PATH + "\n.github/workflows/qualify.yml",
                        guard.HYBRID_WORKER_PATH + "\n" + guard.HYBRID_WORKER_PATH):
            reads = dict(self.reads)
            reads[("diff", "--no-renames", "--name-only", self.base, self.head)] = changed
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                self.admit(reads=reads)

    def test_stale_unrelated_base_and_missing_source_fail_closed(self):
        for key in (("merge-base", self.base, self.head),
                    ("merge-base", guard.HYBRID_RELEASE_ANCHOR, self.base)):
            reads = dict(self.reads)
            reads[key] = "f" * 40
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.admit(reads=reads)
        def unavailable(*args):
            raise subprocess.CalledProcessError(1, "git")
        with self.assertRaisesRegex(ValueError, "SOURCE_UNAVAILABLE"):
            guard.admit_hybrid_workflow_release(self.head, self.base, self.request, unavailable)

    def test_unchanged_generic_source_admission_still_works(self):
        request = copy.deepcopy(self.request)
        request["head"]["ref"] = "engineering/ordinary-source"
        reads = dict(self.reads)
        reads[("diff", "--no-renames", "--name-only", self.base, self.head)] = "f139/example.py"
        self.assertEqual(self.admit(request=request, branch=request["head"]["ref"], reads=reads),
                         "EXACT_MAIN_ANCESTOR_GENERIC_SOURCE_PR")

    def test_cache_adapters_require_the_exact_authenticated_release_modes(self):
        root = Path(guard.__file__).parent
        def load(name):
            spec = importlib.util.spec_from_file_location(name, root / (name + ".py"))
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module
        with patch.dict(sys.modules, {"check_rar_g145_pr_scope": guard}):
            cache = load("check_rar_g148_go_cache")
            with patch.dict(sys.modules, {"check_rar_g148_go_cache": cache}):
                dynamic = load("check_rar_g156_dynamic_base_cache")
        governance = "engineering/f139-exact-worker-release-scope-20261109"
        frozen = "FROZEN_G141_G144_OR_G145_HARNESS_DEVELOPMENT"
        release = "EXACT_PR1642_HYBRID_WORKER_BLOB_QUALIFICATION_ONLY"
        for branch, admission in ((governance, frozen), (guard.HYBRID_RELEASE_BRANCH, release)):
            env = {"GITHUB_ACTIONS": "true", "GITHUB_REPOSITORY": guard.REPO,
                   "RUNNER_OS": "Windows", "G148_HEAD": self.head, "RUNNER_TEMP": "unused",
                   "GITHUB_EVENT_NAME": "pull_request", "GITHUB_BASE_REF": "main",
                   "GITHUB_HEAD_REF": branch}
            with patch.dict(os.environ, env), patch.object(cache.sys, "platform", "win32"), \
                    patch.object(cache, "stable"), patch.object(cache, "admit_original_pr", return_value=admission):
                self.assertEqual(cache.event_mode(self.head), "pr")
                with patch.object(dynamic, "admit_original_pr", return_value=admission):
                    dynamic._release_scope(guard.HYBRID_RELEASE_ANCHOR,
                        "4dd3ad8fcd4ab039192994ebfa679ced30af6b1a", self.head)
                for denied in ("EXACT_MAIN_ANCESTOR_GENERIC_SOURCE_PR", "untrusted"):
                    with patch.object(cache, "admit_original_pr", return_value=denied), self.assertRaises(ValueError):
                        cache.event_mode(self.head)
                    with patch.object(dynamic, "admit_original_pr", return_value=denied), self.assertRaises(ValueError):
                        dynamic._release_scope(self.base, "d" * 40, self.head)


if __name__ == "__main__":
    unittest.main()
