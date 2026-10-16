import pathlib
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import check as f


class Isolation(unittest.TestCase):
    def test_rejects_actual_private_repo_route_in_new_implementation(self):
        name = "spoonman136668-ai/" + "ckb-plane"
        for path in ("service/new.py", ".github/workflows/test.yml", "new.go",
                     "worker/x.mjs", "scripts/a.ps1", "config/rules.json"):
            with self.subTest(path=path):
                patch = (f"diff --git a/{path} b/{path}\n"
                         f"+++ b/{path}\n@@ -0,0 +1 @@\n"
                         f"+gh api repos/{name}/actions/runs\n")
                self.assertEqual(f.audit_patch(patch),
                                 [(path, "PROHIBITED_PRIVATE_REPO_DEPENDENCY")])

    def test_accepts_separation_policy_and_existing_schema(self):
        name = "spoonman136668-ai/" + "ckb-plane"
        patch = ("diff --git a/docs/ADR.md b/docs/ADR.md\n"
                 "+++ b/docs/ADR.md\n@@ -0,0 +1 @@\n"
                 "+Do not depend on " + name + "\n"
                 "diff --git a/worker/safe.py b/worker/safe.py\n"
                 "+++ b/worker/safe.py\n@@ -0,0 +1 @@\n"
                 "+owner = 'FORGE'; ckb_plane_role='governance-only'\n")
        self.assertEqual(f.audit_patch(patch), [])

    def test_rejects_simple_split_literals(self):
        name = "spoonman136668-ai/" + "ckb-plane"
        pieces = (name, name.replace("ckb-plane", "' + 'ckb-plane"),
                  name.replace("-", "\\u002d"), name.upper())
        for raw in pieces:
            with self.subTest(raw=raw):
                self.assertTrue(f.unsafe_line("git = '" + raw + "'"))

    def test_deleted_lines_are_not_new_dependencies(self):
        name = "spoonman136668-ai/" + "ckb-plane"
        self.assertEqual(f.audit_patch("diff --git a/a.py b/a.py\n"
                         "+++ b/a.py\n@@ -1 +0,0 @@\n-" + name + "\n"), [])

    def test_fail_closed_on_unbound_added_source(self):
        with self.assertRaises(f.GateError):
            f.audit_patch("diff --git a/x.py b/x.py\n+danger\n")

    def test_policy_requires_all_three_sources(self):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            for p in ("AGENTS.md", "README.md",
                      "docs/ADR-0002-MIND-PALACE-ONLY-NO-CKB-DEPENDENCY.md"):
                (root / p).parent.mkdir(parents=True, exist_ok=True)
                (root / p).write_text("not the policy", encoding="utf-8")
            with self.assertRaises(f.GateError):
                f.verify_policy_files(root)

    def test_repository_audit_rejects_broken_git_parent(self):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            with mock.patch.object(f, "verify_policy_files"):
                with mock.patch.object(f, "run_git", side_effect=["f"*40, "f"*40]):
                    with self.assertRaises(f.GateError):
                        f.audit_repo(root)


if __name__ == "__main__":
    unittest.main()
