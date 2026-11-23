"""R14 source-only output custody; no live controller or research dispatch.

Normal FORGE execution uses the real existing signed receipt verifier. These
focused tests check the frozen verifier's outcome, byte and size constraints.
"""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from f139.nci04_native_worker import (
    _bounded_capture, verify_fixed_commands, MAX_CAPTURE_BYTES,
    MAX_EXCERPT_BYTES, COMMANDS,
)
from f139.nci04_native_contract import Candidate, digest


class BoundedNativeOutputTests(unittest.TestCase):
    def capture(self, script, *, timeout=5):
        with tempfile.TemporaryDirectory() as root:
            return _bounded_capture([sys.executable, "-c", script],
                                    cwd=Path(root), env=os.environ.copy(),
                                    timeout_seconds=timeout)

    def test_short_native_output(self):
        self.assertEqual(self.capture("import sys;sys.stdout.buffer.write(b'ok\\n')"),
                         (b"ok\n", 0, "PASS"))

    def test_oversized_output_is_actually_bounded(self):
        data, code, outcome = self.capture(
            "import sys;sys.stdout.buffer.write(b'Z'*1000100);sys.stdout.flush()")
        self.assertEqual((len(data), outcome), (MAX_CAPTURE_BYTES, "OUTPUT_LIMIT"))
        self.assertEqual(data[:4], b"ZZZZ")
        self.assertIsInstance(code, int)

    def test_timeout_terminates_process(self):
        self.assertEqual(self.capture("import time;time.sleep(2)", timeout=0.05),
                         (b"", -1, "TIMEOUT"))

    @unittest.skipIf(sys.platform == "win32", "POSIX process-group fixture")
    def test_descendant_held_pipe_does_not_block_overflow_custody(self):
        """Real child inherits stdout and outlives original overproducer."""
        script = (
            "import sys,subprocess;"
            "subprocess.Popen([sys.executable,'-c','import time;time.sleep(15)'],"
            "stdout=sys.stdout,stderr=sys.stderr);"
            "sys.stdout.buffer.write(b'Q'*1000010);sys.stdout.flush()"
        )
        import time
        started = time.monotonic()
        data, code, outcome = self.capture(script, timeout=12)
        self.assertEqual((len(data), code, outcome),
                         (MAX_CAPTURE_BYTES, -1, "OUTPUT_LIMIT"))
        self.assertLess(time.monotonic()-started, 8)

    @unittest.skipIf(sys.platform == "win32", "POSIX process-group fixture")
    def test_orphaned_output_pipe_becomes_explicit_negative(self):
        script = (
            "import sys,subprocess;"
            "subprocess.Popen([sys.executable,'-c','import time;time.sleep(15)'],"
            "stdout=sys.stdout,stderr=sys.stderr);"
            "sys.stdout.write('parent complete\\n');sys.stdout.flush()"
        )
        data, code, outcome = self.capture(script, timeout=12)
        self.assertEqual((code, outcome), (-1, "ORPHANED_OUTPUT"))
        self.assertIn(b"parent complete", data)

    def test_orphaned_output_negative_matches_signed_schema(self):
        with patch("f139.nci04_native_worker._bounded_capture",
                   return_value=(b"parent left a pipe open", -1, "ORPHANED_OUTPUT")):
            with tempfile.TemporaryDirectory() as d:
                root = Path(d)
                (root / "checkout").mkdir()
                c = Candidate("i"*64, "q"*64, "a"*40, "b"*40,
                              "cognition/native.go", "d"*64, "e"*64,
                              b"x", "Wingless")
                report = verify_fixed_commands(c, root, timeout_seconds=15)
        self.assert_provider_can_validate(report)
        self.assertFalse(report["qualification_complete"])
        self.assertEqual(report["commands"][0]["returncode"], 1)
        self.assertIn("F139_NATIVE_ORPHANED_STDOUT_PIPE:",
                      report["commands"][0]["excerpt"])

    def report(self, fake_run):
        with tempfile.TemporaryDirectory() as d:
            stage = Path(d)
            (stage / "checkout").mkdir()
            c = Candidate("i"*64, "q"*64, "a"*40, "b"*40,
                          "cognition/native.go", "d"*64, "e"*64, b"x", "Wingless")
            return verify_fixed_commands(c, stage, runner=fake_run)

    def assert_provider_can_validate(self, report):
        """Checks exact F139 signed-native receipt command and report bounds."""
        self.assertLessEqual(len(json.dumps(report, sort_keys=True, separators=(",", ":")).encode()), 64000)
        for command in report["commands"]:
            self.assertIn(command["outcome"], ("PASS", "TEST_FAILURE", "TIMEOUT"))
            self.assertLessEqual(len(command["excerpt"].encode("utf-8")), 4096)
            if command["outcome"] == "PASS":
                self.assertEqual(command["returncode"], 0)
            elif command["outcome"] == "TIMEOUT":
                self.assertEqual(command["returncode"], -1)
            else:
                self.assertGreater(command["returncode"], 0)

    def test_overflow_retained_as_signed_schema_compatible_negative(self):
        def huge(argv, **kwargs):
            return subprocess.CompletedProcess(argv, 0, b"X" * (MAX_CAPTURE_BYTES + 10))
        report = self.report(huge)
        self.assert_provider_can_validate(report)
        self.assertFalse(report["qualification_complete"])
        self.assertEqual(len(report["commands"]), 1)
        item = report["commands"][0]
        self.assertEqual((item["outcome"], item["returncode"], item["output_bytes"]),
                         ("TEST_FAILURE", 1, MAX_CAPTURE_BYTES))
        self.assertTrue(item["excerpt"].startswith("F139_NATIVE_OUTPUT_LIMIT:"))
        self.assertEqual(item["output_sha256"], digest(b"X" * MAX_CAPTURE_BYTES))

    @unittest.skipIf(sys.platform == "win32", "POSIX executable fixture")
    def test_actual_native_command_path_retains_overflow_negative(self):
        """Exercise real Popen + fixed commands rather than only injected mocks."""
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "checkout").mkdir()
            bindir = root / "tools"
            bindir.mkdir()
            go = bindir / "go"
            go.write_text("#!" + sys.executable + "\nimport sys\nsys.stdout.buffer.write(b'R'*1000042)\n")
            go.chmod(0o755)
            c = Candidate("i"*64, "q"*64, "a"*40, "b"*40,
                          "cognition/native.go", "d"*64, "e"*64, b"x", "Wingless")
            with patch.dict(os.environ, {"PATH": str(bindir)}):
                report = verify_fixed_commands(c, root, timeout_seconds=15)
            self.assert_provider_can_validate(report)
            self.assertFalse(report["qualification_complete"])
            self.assertEqual(report["commands"][0]["returncode"], 1)
            self.assertEqual(report["commands"][0]["outcome"], "TEST_FAILURE")
            self.assertTrue(report["commands"][0]["excerpt"].startswith(
                "F139_NATIVE_OUTPUT_LIMIT:"))
            self.assertEqual(report["commands"][0]["output_bytes"], MAX_CAPTURE_BYTES)

    @unittest.skipIf(sys.platform == "win32", "POSIX source-bound command fixture")
    def test_real_fixed_native_descendant_overflow_is_custodied_negative(self):
        """Full fixed-command report survives a child-held output pipe."""
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "checkout").mkdir()
            tools = root / "tools"
            tools.mkdir()
            executable = tools / "go"
            executable.write_text(
                "#!" + sys.executable + "\n"
                "import sys,subprocess\n"
                "subprocess.Popen([sys.executable,'-c','import time;time.sleep(15)'],"
                "stdout=sys.stdout,stderr=sys.stderr)\n"
                "sys.stdout.buffer.write(b'V'*1000099)\n"
                "sys.stdout.flush()\n"
            )
            executable.chmod(0o755)
            c = Candidate("i"*64, "q"*64, "a"*40, "b"*40,
                          "cognition/native.go", "d"*64, "e"*64,
                          b"x", "Wingless")
            with patch.dict(os.environ, {"PATH": str(tools)}):
                report = verify_fixed_commands(c, root, timeout_seconds=15)
            self.assert_provider_can_validate(report)
            self.assertEqual(len(report["commands"]), 1)
            self.assertFalse(report["qualification_complete"])
            command = report["commands"][0]
            self.assertEqual((command["returncode"], command["outcome"]),
                             (1, "TEST_FAILURE"))
            self.assertEqual(command["output_bytes"], MAX_CAPTURE_BYTES)
            self.assertIn("F139_NATIVE_OUTPUT_LIMIT:", command["excerpt"])
            self.assertEqual(command["output_sha256"],
                             digest(b"V" * MAX_CAPTURE_BYTES))

    @unittest.skipIf(sys.platform == "win32", "POSIX signal-returncode test")
    def test_negative_os_returncode_is_signed_schema_compatible(self):
        report = self.report(lambda argv, **kwargs: subprocess.CompletedProcess(argv, -9, b"killed"))
        self.assert_provider_can_validate(report)
        self.assertEqual(report["commands"][0]["returncode"], 1)
        self.assertIn("native_returncode=-9", report["commands"][0]["excerpt"])

    def test_all_four_long_commands_fit_provider_max_receipt(self):
        def noisy(argv, **kwargs):
            return subprocess.CompletedProcess(argv, 0, b"a" * (MAX_CAPTURE_BYTES - 1))
        report = self.report(noisy)
        self.assert_provider_can_validate(report)
        self.assertTrue(report["qualification_complete"])
        self.assertEqual(len(report["commands"]), len(COMMANDS["Wingless"]))
        for command in report["commands"]:
            self.assertLessEqual(len(command["excerpt"].encode()), MAX_EXCERPT_BYTES)

    def test_malformed_utf8_excerpt_remains_within_signed_bound(self):
        report = self.report(lambda argv, **kw: subprocess.CompletedProcess(argv, 1, b"\xff"*5000))
        self.assert_provider_can_validate(report)
        self.assertFalse(report["qualification_complete"])

    def test_first_native_failure_stops_following_commands(self):
        calls = []
        def fail(argv, **kw):
            calls.append(argv)
            return subprocess.CompletedProcess(argv, 2, b"failed")
        report = self.report(fail)
        self.assert_provider_can_validate(report)
        self.assertEqual(len(calls), 1)
        self.assertEqual(report["commands"][0]["returncode"], 2)
        self.assertEqual(report["commands"][0]["output_sha256"], digest(b"failed"))

    def test_runner_environment_still_excludes_secrets(self):
        def inspect(argv, **kw):
            self.assertNotIn("F139_WORKER_HMAC_KEY", kw["env"])
            self.assertNotIn("GH_TOKEN", kw["env"])
            self.assertNotIn("OPENAI_API_KEY", kw["env"])
            self.assertEqual(kw["env"]["GOPROXY"], "off")
            return subprocess.CompletedProcess(argv, 0, b"ok")
        with patch.dict(os.environ, {"F139_WORKER_HMAC_KEY":"sentinel", "GH_TOKEN":"secret", "OPENAI_API_KEY":"secret"}):
            self.assert_provider_can_validate(self.report(inspect))

if __name__ == "__main__":
    unittest.main()
