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


    def _qualified_fixture(self, root):
        fixed = {
            "AGENTS.md": "FORGE MUST NOT connect to or depend on CKB-plane",
            "README.md": "FORGE must not connect to or depend on CKB-plane",
            "docs/ADR-0002-MIND-PALACE-ONLY-NO-CKB-DEPENDENCY.md":
                "FORGE must not connect to CKB-plane",
            "cmd/forge-ckb-s14-history/main.go":
                "const FORGE_CKB_LEGACY_COMMAND_RETIRED = true\\n"
                "func run() error {return errRetired}\\n",
            "cmd/forge-ckb-custody/main.go":
                "const FORGE_CKB_CUSTODY_COMMAND_RETIRED = true\\n"
                "func run(_ []string, _ io.Writer) error {return errRetired}\\n",
            "cmd/forge-ckb-s14-reconcile/main.go":
                "const FORGE_CKB_S14_RECONCILE_COMMAND_RETIRED = true\\n"
                "func run(_ context.Context, _ []string, _ io.Writer, _ string) error {return errRetired}\\n",
            "cmd/forge-cutover-audit/main.go":
                "const FORGE_CKB_CUTOVER_AUDIT_COMMAND_RETIRED = true\\n"
                "func run(_ []string, _ io.Writer, _ uint64) error {return errRetired}\\n",
            ".github/workflows/safe.yml": "on: [pull_request]\\njobs: {}\\n",
        }
        for path, data in fixed.items():
            p = root / path
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(data, encoding="utf-8")

    def test_retired_legacy_workflow_can_never_reenter_main(self):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            self._qualified_fixture(root)
            f.verify_policy_files(root)
            legacy = root / ".github/workflows/forge-ckb-s14-readonly-history.yml"
            legacy.write_text("on: workflow_dispatch\\n", encoding="utf-8")
            with self.assertRaisesRegex(f.GateError, "LEGACY_CKB_WORKFLOW_NOT_RETIRED"):
                f.verify_policy_files(root)

    def test_any_workflow_direct_private_route_is_blocked(self):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            self._qualified_fixture(root)
            workflow = root / ".github/workflows/safe.yml"
            workflow.write_text(
                "run: gh api repos/spoonman136668-ai/" +
                "ckb-plane/actions/runs\\n", encoding="utf-8")
            with self.assertRaisesRegex(f.GateError, "ACTIVE_PRIVATE_REPO_WORKFLOW"):
                f.verify_policy_files(root)

    def test_legacy_cli_cannot_become_live_client(self):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            self._qualified_fixture(root)
            cli = root / "cmd/forge-ckb-s14-history/main.go"
            cli.write_text("func run() { ckbhistory.New(\"token\") }",
                           encoding="utf-8")
            with self.assertRaisesRegex(f.GateError, "LEGACY_CKB_COMMAND_NOT_FAIL_CLOSED"):
                f.verify_policy_files(root)


    def test_local_custody_command_must_stay_retired(self):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            self._qualified_fixture(root)
            f.verify_policy_files(root)
            cli = root / "cmd/forge-ckb-custody/main.go"
            cli.write_text(
                "const FORGE_CKB_CUSTODY_COMMAND_RETIRED = true\\n"
                "func run(_ []string, _ io.Writer) error {\\n"
                "    _ = os.ReadFile(\"/sensitive/controller-state\")\\n"
                "    return errRetired\\n}\\n", encoding="utf-8")
            with self.assertRaisesRegex(f.GateError,
                                        "LEGACY_CUSTODY_COMMAND_NOT_FAIL_CLOSED"):
                f.verify_policy_files(root)

    def test_local_custody_retirement_sentinel_cannot_be_removed(self):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            self._qualified_fixture(root)
            (root / "cmd/forge-ckb-custody/main.go").unlink()
            with self.assertRaisesRegex(f.GateError,
                                        "MISSING_RETIRED_CUSTODY_SENTINEL"):
                f.verify_policy_files(root)

    def test_local_custody_cannot_import_legacy_library(self):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            self._qualified_fixture(root)
            cli = root / "cmd/forge-ckb-custody/main.go"
            cli.write_text(
                "const FORGE_CKB_CUSTODY_COMMAND_RETIRED = true\\n"
                "func run(_ []string, _ io.Writer) error {\\n"
                "    ckbcustody.Inspect(\"/sensitive/state\")\\n"
                "    return errRetired\\n}\\n", encoding="utf-8")
            with self.assertRaisesRegex(f.GateError,
                                        "LEGACY_CUSTODY_COMMAND_NOT_FAIL_CLOSED"):
                f.verify_policy_files(root)

    def test_reconciliation_command_cannot_reenable_private_client(self):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            self._qualified_fixture(root)
            f.verify_policy_files(root)
            cli = root / "cmd/forge-ckb-s14-reconcile/main.go"
            cli.write_text(
                "const FORGE_CKB_S14_RECONCILE_COMMAND_RETIRED = true\\n"
                "func run(_ context.Context, _ []string, _ io.Writer, _ string) error {\\n"
                "    _ = ckbhistory.New(\\\"synthetic-secret\\\")\\n"
                "    return errRetired\\n}\\n", encoding="utf-8")
            with self.assertRaisesRegex(f.GateError,
                                        "LEGACY_RECONCILIATION_COMMAND_NOT_FAIL_CLOSED"):
                f.verify_policy_files(root)

    def test_reconciliation_command_cannot_open_local_state(self):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            self._qualified_fixture(root)
            cli = root / "cmd/forge-ckb-s14-reconcile/main.go"
            cli.write_text(
                "const FORGE_CKB_S14_RECONCILE_COMMAND_RETIRED = true\\n"
                "func run(_ context.Context, _ []string, _ io.Writer, _ string) error {\\n"
                "    _, _ = os.ReadFile(\\\"/private/state\\\")\\n"
                "    return errRetired\\n}\\n", encoding="utf-8")
            with self.assertRaisesRegex(f.GateError,
                                        "LEGACY_RECONCILIATION_COMMAND_NOT_FAIL_CLOSED"):
                f.verify_policy_files(root)

    def test_reconciliation_retirement_sentinel_is_mandatory(self):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            self._qualified_fixture(root)
            cli = root / "cmd/forge-ckb-s14-reconcile/main.go"
            cli.unlink()
            with self.assertRaisesRegex(f.GateError,
                                        "MISSING_RETIRED_RECONCILIATION_SENTINEL"):
                f.verify_policy_files(root)


    def test_legacy_cutover_command_cannot_read_private_controller(self):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            self._qualified_fixture(root)
            f.verify_policy_files(root)
            cli = root / "cmd/forge-cutover-audit/main.go"
            cli.write_text(
                "const FORGE_CKB_CUTOVER_AUDIT_COMMAND_RETIRED = true\\n"
                "func run(_ []string, _ io.Writer, _ uint64) error {\\n"
                "  _ = ckbhistory.New(os.Getenv(\\\"GH_TOKEN\\\"))\\n"
                "  return errRetired\\n}\\n", encoding="utf-8")
            with self.assertRaisesRegex(f.GateError,
                                        "LEGACY_CUTOVER_COMMAND_NOT_FAIL_CLOSED"):
                f.verify_policy_files(root)

    def test_legacy_cutover_command_cannot_read_local_ledger(self):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            self._qualified_fixture(root)
            cli = root / "cmd/forge-cutover-audit/main.go"
            cli.write_text(
                "const FORGE_CKB_CUTOVER_AUDIT_COMMAND_RETIRED = true\\n"
                "func run(_ []string, _ io.Writer, _ uint64) error {\\n"
                "  _ = os.ReadFile(\\\"/private/ckb-state\\\")\\n"
                "  return errRetired\\n}\\n", encoding="utf-8")
            with self.assertRaisesRegex(f.GateError,
                                        "LEGACY_CUTOVER_COMMAND_NOT_FAIL_CLOSED"):
                f.verify_policy_files(root)

    def test_legacy_cutover_retirement_must_remain_present(self):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            self._qualified_fixture(root)
            (root / "cmd/forge-cutover-audit/main.go").unlink()
            with self.assertRaisesRegex(f.GateError,
                                        "MISSING_RETIRED_CUTOVER_SENTINEL"):
                f.verify_policy_files(root)



if __name__ == "__main__":
    unittest.main()
