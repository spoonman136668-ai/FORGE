"""F139 NCI04 isolated native executor source-bound tests; no real foreign code run."""
import base64
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from f139.nci04_native_contract import SCHEMA, digest, parse_intent, NativeContractError
from f139.nci04_native_worker import stage_candidate, verify_fixed_commands, COMMANDS

CONTROLLER = "a" * 40
BEFORE = b"package cognition\n"
AFTER = b"package cognition\n// native candidate isolated change\n"


def git(repo, *argv):
    result = subprocess.run(["git", "-C", str(repo), *argv],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            check=True, timeout=15)
    return result.stdout.decode().strip()


class NativeWorkerTests(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.addCleanup(self.t.cleanup)
        self.base = Path(self.t.name)
        self.repo = self.base / "real"
        self.repo.mkdir()
        git(self.repo, "init", "-q")
        git(self.repo, "config", "user.name", "nci04-fixture")
        git(self.repo, "config", "user.email", "fixture@example.invalid")
        (self.repo / "cognition").mkdir()
        (self.repo / "cognition" / "sample.go").write_bytes(BEFORE)
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-qm", "source")
        self.sha = git(self.repo, "rev-parse", "HEAD")
        self.tree = git(self.repo, "rev-parse", "HEAD^{tree}")
        self.sandbox = self.base / "sandbox"
        self.sandbox.mkdir()

    def intent(self, **overrides):
        obj = {
            "schema": SCHEMA,
            "controller_source_sha": CONTROLLER,
            "lane": "Wingless",
            "target_repository": "spoonman136668-ai/Wingless",
            "target_commit": self.sha,
            "target_tree_sha": self.tree,
            "dependency_sha256": "d" * 64,
            "qualification_harness_sha256": "e" * 64,
            "training_config_sha256": "f" * 64,
            "toolchain_identity": "go1.25.0",
            "suite_identity_sha256": "1" * 64,
            "path": "cognition/sample.go",
            "before_sha256": digest(BEFORE),
            "after_sha256": digest(AFTER),
            "after_base64": base64.b64encode(AFTER).decode(),
            "worker_mode": "isolated-candidate-only",
            "scientific_first_use": False,
            "paid_api_calls": 0,
            "accepted_ref_mutations": 0,
            "optimizer_policy_mutations": 0,
            "protected_holdouts_accessed": 0,
        }
        obj.update(overrides)
        raw = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()
        return parse_intent(raw, protected_main=CONTROLLER,
                            target_commit=self.sha, target_tree_sha=self.tree)

    def test_materialize_into_disjoint_sandbox_never_modify_source(self):
        stage = stage_candidate(self.intent(), self.repo, self.sandbox)
        self.assertEqual((stage / "checkout" / "cognition" / "sample.go").read_bytes(), AFTER)
        self.assertEqual((self.repo / "cognition" / "sample.go").read_bytes(), BEFORE)
        self.assertEqual(git(self.repo, "status", "--porcelain"), "")

    def test_yggdrasil_staged_git_history_has_no_original_remote(self):
        after=b"def local_state():\n    return 1\n"
        candidate=self.intent(
            lane="Yggdrasil",
            target_repository="spoonman136668-ai/Yggdrasil",
            toolchain_identity="python3.11.11",
            path="yggdrasil/online_state.py",
            before_sha256=digest(b""),
            after_sha256=digest(after),
            after_base64=base64.b64encode(after).decode(),
        )
        stage=stage_candidate(candidate,self.repo,self.sandbox)
        root=stage / "checkout"
        self.assertEqual(git(root,"rev-parse","HEAD"),self.sha)
        self.assertEqual(git(root,"rev-parse","HEAD^{tree}"),self.tree)
        self.assertEqual(git(root,"remote"),"")
        self.assertEqual((root / "yggdrasil/online_state.py").read_bytes(),after)
        self.assertEqual(git(self.repo,"status","--porcelain"),"")
        self.assertFalse((self.repo / "yggdrasil").exists())

    def test_dirty_checkout_rejected_before_staging(self):
        (self.repo / "cognition" / "sample.go").write_bytes(b"unexpected")
        with self.assertRaisesRegex(NativeContractError, "CHECKOUT_DIRTY"):
            stage_candidate(self.intent(), self.repo, self.sandbox)
        self.assertEqual(list(self.sandbox.iterdir()), [])

    def test_wrong_checkout_sha_and_tree_rejected(self):
        candidate = self.intent()
        (self.repo / "extra.txt").write_text("new")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-qm", "not source")
        with self.assertRaisesRegex(NativeContractError, "CHECKOUT_COMMIT_DRIFT"):
            stage_candidate(candidate, self.repo, self.sandbox)

    def test_preimage_hash_mismatch_no_partial_outputs(self):
        bad = self.intent(before_sha256="2" * 64)
        with self.assertRaisesRegex(NativeContractError, "ORIGINAL_BYTES_DRIFT"):
            stage_candidate(bad, self.repo, self.sandbox)
        self.assertEqual(list(self.sandbox.iterdir()), [])
        self.assertEqual((self.repo / "cognition" / "sample.go").read_bytes(), BEFORE)

    def test_symlink_in_checkout_fails_closed(self):
        target = self.base / "outside"
        target.write_text("sensitive")
        try:
            (self.repo / "cognition" / "external").symlink_to(target)
        except OSError:
            self.skipTest("user does not have Windows symlink creation privilege")
        with self.assertRaisesRegex(NativeContractError, "CHECKOUT_DIRTY|CHECKOUT_SYMLINK_REJECTED"):
            stage_candidate(self.intent(), self.repo, self.sandbox)
        self.assertEqual(target.read_text(), "sensitive")

    def test_staging_inside_source_not_allowed(self):
        with self.assertRaisesRegex(NativeContractError, "SANDBOX_NOT_DISJOINT"):
            stage_candidate(self.intent(), self.repo, self.repo / "cognition")

    def test_only_fixed_commands_no_secrets_and_full_regression(self):
        candidate = self.intent()
        stage = stage_candidate(candidate, self.repo, self.sandbox)
        calls = []
        def fake_run(argv, **kw):
            calls.append((argv, kw))
            return subprocess.CompletedProcess(argv, 0, b"ok\n")
        with patch.dict("os.environ", {"F139_WORKER_HMAC_KEY": "sentinel",
                                       "GH_TOKEN": "token", "OPENAI_API_KEY": "api"}):
            proof = verify_fixed_commands(candidate, stage, runner=fake_run)
        self.assertTrue(proof["qualification_complete"])
        self.assertEqual(len(calls), 4)
        self.assertEqual([tuple(x[0]) for x in calls], list(COMMANDS["Wingless"]))
        self.assertIn(("go", "test", "-count=1", "./..."), COMMANDS["Wingless"])
        for _, kw in calls:
            self.assertNotIn("F139_WORKER_HMAC_KEY", kw["env"])
            self.assertNotIn("GH_TOKEN", kw["env"])
            self.assertNotIn("OPENAI_API_KEY", kw["env"])
            self.assertEqual(kw["env"]["GOPROXY"], "off")
        self.assertIsNone(proof["child_peak_rss_bytes"])
        self.assertFalse(proof["unattended_controller_dispatch_verified"])

    def test_failure_preserved_no_build_or_false_acceptance(self):
        candidate = self.intent()
        stage = stage_candidate(candidate, self.repo, self.sandbox)
        calls = []
        def fail_first(argv, **kw):
            calls.append(argv)
            return subprocess.CompletedProcess(argv, 1, b"native failure\n")
        report = verify_fixed_commands(candidate, stage, runner=fail_first)
        self.assertFalse(report["qualification_complete"])
        self.assertEqual(len(report["commands"]), 1)
        self.assertEqual(report["commands"][0]["outcome"], "TEST_FAILURE")
        self.assertEqual(report["commands"][0]["output_sha256"], digest(b"native failure\n"))
        self.assertEqual(len(calls), 1)


    def _staged_yggdrasil(self):
        after = b"def observe(state, evidence):\n    return state + evidence\n"
        candidate = self.intent(
            lane="Yggdrasil",
            target_repository="spoonman136668-ai/Yggdrasil",
            toolchain_identity="python3.11.11",
            path="yggdrasil/native_public_cells.py",
            before_sha256=digest(b""),
            after_sha256=digest(after),
            after_base64=base64.b64encode(after).decode(),
        )
        return candidate, stage_candidate(candidate, self.repo, self.sandbox)

    def test_ygg_zero_focused_tests_is_fail_closed_with_original_stdout(self):
        candidate, stage = self._staged_yggdrasil()
        calls = []
        actual = b"\n----------------------------------------------------------------------\nRan 0 tests in 0.000s\n\nOK\n"
        def run(argv, **kw):
            calls.append(tuple(argv))
            return subprocess.CompletedProcess(argv, 0, actual)
        receipt = verify_fixed_commands(candidate, stage, runner=run)
        self.assertFalse(receipt["qualification_complete"])
        self.assertEqual(calls, [COMMANDS["Yggdrasil"][0]])
        self.assertEqual(len(receipt["commands"]), 1)
        item = receipt["commands"][0]
        self.assertEqual(item["outcome"], "TEST_FAILURE")
        self.assertEqual(item["returncode"], 1)
        self.assertEqual(item["output_sha256"], digest(actual))
        self.assertEqual(item["output_bytes"], len(actual))
        self.assertIn("ZERO_OR_UNVERIFIED_TESTS", item["excerpt"])
        self.assertFalse(receipt["scientific_first_use"])
        self.assertEqual(git(self.repo, "status", "--porcelain"), "")

    def test_ygg_real_nonzero_unittest_counts_and_full_regression_accepted(self):
        candidate, stage = self._staged_yggdrasil()
        counts = [
            b"\nRan 2 tests in 0.004s\n\nOK\n",
            b"\nRan 35 tests in 0.016s\n\nOK\n",
            b"",
        ]
        seen = []
        def run(argv, **kw):
            seen.append(tuple(argv))
            return subprocess.CompletedProcess(argv, 0, counts[len(seen)-1])
        result = verify_fixed_commands(candidate, stage, runner=run)
        self.assertTrue(result["qualification_complete"])
        self.assertEqual(seen, list(COMMANDS["Yggdrasil"]))
        self.assertEqual(len(result["commands"]), 3)
        self.assertEqual(
            [z["output_sha256"] for z in result["commands"]],
            [digest(raw) for raw in counts],
        )
        self.assertEqual(result["paid_model_calls"], 0)

    def test_ygg_missing_or_ambiguous_test_counts_fail_closed(self):
        for output in (
            b"OK\n",
            b"Ran 1 test in 0.010s\nRan 1 test in 0.020s\nOK\n",
            b"Ran 0 tests in 0.001s\nOK\n",
        ):
            with self.subTest(output=output):
                candidate, stage = self._staged_yggdrasil()
                def run(argv, **kw):
                    return subprocess.CompletedProcess(argv, 0, output)
                result = verify_fixed_commands(candidate, stage, runner=run)
                self.assertFalse(result["qualification_complete"])
                self.assertEqual(len(result["commands"]), 1)
                self.assertEqual(result["commands"][0]["returncode"], 1)
                self.assertEqual(result["commands"][0]["output_sha256"], digest(output))


if __name__ == "__main__":
    unittest.main()
