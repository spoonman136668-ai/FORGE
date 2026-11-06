"""Bounded GitHub CLI transport policy for the original F139 owner client."""
import io
import json
import subprocess
import unittest
from contextlib import redirect_stderr
from types import SimpleNamespace
from unittest.mock import patch

from local_controller import F139Error, GitHub


class GitHubCommandTransportTests(unittest.TestCase):
    ROUTE = "repos/spoonman136668-ai/FORGE/branches/main"

    def invoke(self, args, responses, command=None):
        with patch("local_controller.shutil.which", return_value="gh"), \
             patch("local_controller.subprocess.run", side_effect=responses) as run, \
             patch("local_controller.time.sleep") as sleep:
            result = None
            error = None
            try:
                result = (command or GitHub._command)(args)
            except F139Error as exc:
                error = str(exc)
            return result, error, run, sleep

    def test_windows_connectex_retries_only_transient_gets(self):
        messages = (
            b'Get "https://api.github.com/private": dial tcp 140.82.112.6:443: connectex: A connection attempt failed because the connected party did not properly respond',
            b'connectex: No connection could be made because the target machine actively refused it',
            b'connectex: An existing connection was forcibly closed by the remote host',
        )
        ok = SimpleNamespace(returncode=0, stdout=b'{}', stderr=b'')
        for message in messages:
            failure = SimpleNamespace(returncode=1, stdout=b'', stderr=message)
            with self.subTest(message=message):
                value, error, run, sleep = self.invoke([self.ROUTE], [failure, ok])
                self.assertEqual((value, error), (b'{}', None))
                self.assertEqual(run.call_count, 2)
                self.assertEqual([c.args[0] for c in sleep.call_args_list], [1])
                capture = io.StringIO()
                with redirect_stderr(capture):
                    value, error, run, sleep = self.invoke([self.ROUTE], [failure]*3)
                self.assertEqual(error, 'F139_GITHUB_API_TRANSIENT')
                self.assertEqual(run.call_count, 3)
                self.assertEqual([c.args[0] for c in sleep.call_args_list], [1, 2])
                report = json.loads(capture.getvalue().split('=', 1)[1])
                self.assertEqual(report['attempts'], 3)
                self.assertIsNone(report['http_status'])
                self.assertNotIn('140.82', capture.getvalue())
                self.assertNotIn('/private', capture.getvalue())
                for status in (401, 403, 404, 422):
                    rejected = SimpleNamespace(returncode=1, stdout=b'',
                        stderr=('HTTP %d: '%status).encode()+message)
                    _, _, run, sleep = self.invoke([self.ROUTE], [rejected])
                    self.assertEqual(run.call_count, 1)
                    sleep.assert_not_called()
                for method in ('POST', 'PATCH', 'PUT', 'DELETE'):
                    _, _, run, sleep = self.invoke(['--method', method, self.ROUTE], [failure])
                    self.assertEqual(run.call_count, 1)
                    sleep.assert_not_called()
        unrelated = SimpleNamespace(returncode=1, stdout=b'', stderr=b'connectex: access denied')
        _, error, run, sleep = self.invoke([self.ROUTE], [unrelated])
        self.assertEqual(error, 'F139_GITHUB_API_FAILED')
        self.assertEqual(run.call_count, 1)
        sleep.assert_not_called()

    def test_installer_reads_share_transport_and_writes_remain_one_shot(self):
        from pathlib import Path
        source = (Path(__file__).resolve().parents[1]/'.github/workflows/f139-v38-original-owner-release.yml').read_text()
        installer = source.split('  install-v39:',1)[1].split('  recover-pretransition-v38:',1)[0]
        calls = [line.strip() for line in installer.splitlines() if '& gh api ' in line]
        self.assertEqual(len(calls), 3)
        self.assertTrue(all(' -X PATCH ' in line for line in calls))
        self.assertIn('GitHub._command([sys.argv[1]])', installer)
        self.assertIn('F139_V39_READ_ROUTE_DENIED', installer)
        self.assertIn("$localOwner=[string](Read-V39GitHub 'user').login", installer)
        self.assertIn('F139_V39_POLICY_READ_TRANSPORT_FALLBACK=READ_ONLY', installer)

    @unittest.skipUnless(__import__('os').name == 'nt', 'Windows PowerShell helper execution')
    def test_installer_bounded_read_helper_parses_executes_and_denies_foreign_routes(self):
        from pathlib import Path
        import textwrap
        source = (Path(__file__).resolve().parents[1]/'.github/workflows/f139-v38-original-owner-release.yml').read_text()
        helper = 'function Read-V39GitHub'+source.split('function Read-V39GitHub',1)[1].split('          $main=',1)[0]
        helper = '\n'.join(line[10:] if line.startswith('          ') else line for line in helper.splitlines())
        script = textwrap.dedent("""
            $ErrorActionPreference='Stop'; Set-StrictMode -Version Latest
            $global:calls=0; $global:lastRoute=''; $global:LASTEXITCODE=0
            function python {
              $global:calls++; $global:lastRoute=$args[-1]
              if($global:lastRoute -eq 'user') {'{"login":"spoonman136668-ai"}'}
              else {'{"ok":true}'}
              $global:LASTEXITCODE=0
            }
        """) + helper + textwrap.dedent("""
            $v=Read-V39GitHub 'https://api.github.com/repos/spoonman136668-ai/FORGE/actions/runs/123/jobs'
            if(-not $v.ok -or $global:lastRoute -cne 'repos/spoonman136668-ai/FORGE/actions/runs/123/jobs'){throw 'ROUTE_OR_JSON_DRIFT'}
            if((Read-V39GitHub 'user').login -cne 'spoonman136668-ai'){throw 'IDENTITY_DRIFT'}
            foreach($bad in @('https://evil.test/path','repos/other/FORGE/issues','--method')) {
              try {Read-V39GitHub $bad;throw 'UNEXPECTED_ACCEPTANCE'}
              catch {if($_.Exception.Message -cne 'F139_V39_READ_ROUTE_DENIED'){throw}}
            }
            if($global:calls -ne 2){throw 'DENIED_ROUTE_EXECUTED'}
            function python {$global:LASTEXITCODE=1}
            try {Read-V39GitHub 'user';throw 'UNEXPECTED_ACCEPTANCE'}
            catch {if($_.Exception.Message -cne 'F139_V39_BOUNDED_READ_UNAVAILABLE'){throw}}
            exit 0
        """)
        result=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',script],
                              capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def test_read_only_get_retries_timeout_then_succeeds(self):
        ok = SimpleNamespace(returncode=0, stdout=b'{"ok":true}', stderr=b"")
        result, error, run, sleep = self.invoke(
            [self.ROUTE], [subprocess.TimeoutExpired(["gh", "api"], 40), ok]
        )
        self.assertEqual(result, b'{"ok":true}')
        self.assertIsNone(error)
        self.assertEqual(run.call_count, 2)
        self.assertEqual([c.args[0] for c in sleep.call_args_list], [1])

    def test_read_only_get_retries_server_error_then_succeeds(self):
        failed = SimpleNamespace(
            returncode=1, stdout=b"", stderr=b"gh: HTTP 503: Service Unavailable"
        )
        ok = SimpleNamespace(returncode=0, stdout=b'{"ok":true}', stderr=b"")
        result, error, run, sleep = self.invoke([self.ROUTE], [failed, ok])
        self.assertEqual(result, b'{"ok":true}')
        self.assertIsNone(error)
        self.assertEqual(run.call_count, 2)
        self.assertEqual([c.args[0] for c in sleep.call_args_list], [1])

    def test_read_only_get_stops_after_three_rate_limited_attempts(self):
        failed = SimpleNamespace(
            returncode=1, stdout=b"", stderr=b"HTTP 429: API rate limit exceeded"
        )
        result, error, run, sleep = self.invoke(
            [self.ROUTE], [failed, failed, failed]
        )
        self.assertIsNone(result)
        self.assertEqual(error, "F139_GITHUB_API_RATE_LIMIT")
        self.assertEqual(run.call_count, 3)
        self.assertEqual([c.args[0] for c in sleep.call_args_list], [1, 2])

    def test_authentication_failure_is_not_retried(self):
        failed = SimpleNamespace(
            returncode=1, stdout=b"", stderr=b"HTTP 403: Resource not accessible"
        )
        result, error, run, sleep = self.invoke([self.ROUTE], [failed])
        self.assertIsNone(result)
        self.assertEqual(error, "F139_GITHUB_API_AUTH")
        self.assertEqual(run.call_count, 1)
        sleep.assert_not_called()

    def test_post_timeout_is_never_retried(self):
        args = [
            "--method", "POST", "repos/spoonman136668-ai/FORGE/issues",
            "-f", "title=bounded test",
        ]
        result, error, run, sleep = self.invoke(
            args, [subprocess.TimeoutExpired(["gh", "api"], 40)]
        )
        self.assertIsNone(result)
        self.assertEqual(error, "F139_GITHUB_API_TIMEOUT")
        self.assertEqual(run.call_count, 1)
        sleep.assert_not_called()

    def test_post_server_error_is_never_retried(self):
        args = [
            "--method", "POST", "repos/spoonman136668-ai/FORGE/issues",
            "-f", "title=bounded test",
        ]
        failed = SimpleNamespace(
            returncode=1, stdout=b"", stderr=b"HTTP 502: Bad Gateway"
        )
        result, error, run, sleep = self.invoke(args, [failed])
        self.assertIsNone(result)
        self.assertEqual(error, "F139_GITHUB_API_TRANSIENT")
        self.assertEqual(run.call_count, 1)
        sleep.assert_not_called()

    def test_patch_put_and_delete_timeouts_are_never_retried(self):
        for method in ("PATCH", "PUT", "DELETE"):
            with self.subTest(method=method):
                args = [
                    "--method", method,
                    "repos/spoonman136668-ai/FORGE/issues/1",
                    "-f", "title=bounded test",
                ]
                result, error, run, sleep = self.invoke(
                    args, [subprocess.TimeoutExpired(["gh", "api"], 40)]
                )
                self.assertIsNone(result)
                self.assertEqual(error, "F139_GITHUB_API_TIMEOUT")
                self.assertEqual(run.call_count, 1)
                sleep.assert_not_called()

    def test_get_with_extra_cli_options_is_not_retryable(self):
        args = ["--paginate", self.ROUTE]
        result, error, run, sleep = self.invoke(
            args, [subprocess.TimeoutExpired(["gh", "api"], 40)]
        )
        self.assertIsNone(result)
        self.assertEqual(error, "F139_GITHUB_API_TIMEOUT")
        self.assertEqual(run.call_count, 1)
        sleep.assert_not_called()

    def test_failure_classification_does_not_echo_raw_stderr(self):
        failed = SimpleNamespace(
            returncode=1, stdout=b"", stderr=b"HTTP 403 secret-token=DO_NOT_LEAK"
        )
        result, error, run, sleep = self.invoke([self.ROUTE], [failed])
        self.assertIsNone(result)
        self.assertEqual(error, "F139_GITHUB_API_AUTH")
        self.assertNotIn("DO_NOT_LEAK", error)
        self.assertEqual(run.call_count, 1)

    def test_definite_http_rejections_override_transient_words(self):
        cases = (
            (401, "API rate limit exceeded", "AUTH"),
            (401, "connection reset", "AUTH"),
            (403, "connection reset", "AUTH"),
            (403, "missing rate limit permission", "AUTH"),
            (404, "API rate limit exceeded", "FAILED"),
            (404, "connection reset", "FAILED"),
            (422, "temporary failure", "FAILED"),
        )
        for status, text, expected in cases:
            with self.subTest(status=status, text=text):
                failed = SimpleNamespace(returncode=1, stdout=b"",
                    stderr=f"HTTP {status}: {text}; DO_NOT_LEAK".encode())
                result, error, run, sleep = self.invoke([self.ROUTE], [failed] * 3)
                self.assertIsNone(result)
                self.assertEqual(error, "F139_GITHUB_API_" + expected)
                self.assertEqual(run.call_count, 1)
                sleep.assert_not_called()
                self.assertNotIn("DO_NOT_LEAK", error)

    def test_explicit_403_rate_limit_keeps_bounded_read_recovery(self):
        for text in ("API rate limit exceeded", "secondary rate limit"):
            with self.subTest(text=text):
                failed = SimpleNamespace(returncode=1, stdout=b"",
                    stderr=f"HTTP 403: {text}".encode())
                ok = SimpleNamespace(returncode=0, stdout=b"{}", stderr=b"")
                result, error, run, sleep = self.invoke([self.ROUTE], [failed, ok])
                self.assertEqual(result, b"{}")
                self.assertIsNone(error)
                self.assertEqual(run.call_count, 2)
                self.assertEqual([c.args[0] for c in sleep.call_args_list], [1])

    def test_terminal_http_failure_identifies_route_without_opaque_data(self):
        route = ("repos/spoonman136668-ai/Yggdrasil/git/commits/" +
                 "a" * 40 + "?access_token=DO_NOT_LEAK_ROUTE")
        failed = SimpleNamespace(
            returncode=1, stdout=b"NEVER_ECHO_STDOUT",
            stderr=b"HTTP 404: missing; DO_NOT_LEAK_STDERR")
        capture = io.StringIO()
        with redirect_stderr(capture):
            result, error, run, sleep = self.invoke([route], [failed])
        self.assertIsNone(result)
        self.assertEqual(error, "F139_GITHUB_API_FAILED")
        self.assertEqual(run.call_count, 1)
        sleep.assert_not_called()
        lines = capture.getvalue().splitlines()
        self.assertEqual(len(lines), 1)
        self.assertTrue(lines[0].startswith("F139_GITHUB_READ_TERMINAL="))
        report = json.loads(lines[0].split("=", 1)[1])
        self.assertEqual(report["schema"],
                         "forge.f139.github-read-terminal-diagnostic.v1")
        self.assertEqual(report["repository"], "Yggdrasil")
        self.assertEqual(report["route_family"], "COMMIT_IDENTITY")
        self.assertEqual(report["failure"], "GITHUB_API_FAILED")
        self.assertEqual(report["http_status"], 404)
        self.assertEqual(report["exit_code"], 1)
        self.assertEqual(report["attempts"], 1)
        self.assertTrue(report["read_only"])
        self.assertFalse(report["raw_route_or_output_retained"])
        for secret in ("DO_NOT_LEAK_ROUTE", "DO_NOT_LEAK_STDERR",
                       "NEVER_ECHO_STDOUT", "a" * 40):
            self.assertNotIn(secret, capture.getvalue())

    def test_terminal_unknown_cli_error_preserves_exact_failure_and_family(self):
        route = ("repos/spoonman136668-ai/FORGE/actions/workflows/" +
                 "private-id/runs?token=DO_NOT_LEAK")
        failed = SimpleNamespace(
            returncode=4, stdout=b"", stderr=b"secret=DO_NOT_LEAK")
        capture = io.StringIO()
        with redirect_stderr(capture):
            result, error, run, sleep = self.invoke([route], [failed])
        report = json.loads(capture.getvalue().split("=", 1)[1])
        self.assertIsNone(result)
        self.assertEqual(error, "F139_GITHUB_API_FAILED")
        self.assertEqual(run.call_count, 1)
        sleep.assert_not_called()
        self.assertEqual(report["repository"], "FORGE")
        self.assertEqual(report["route_family"], "WORKFLOW_RUNS")
        self.assertIsNone(report["http_status"])
        self.assertEqual(report["exit_code"], 4)
        self.assertNotIn("DO_NOT_LEAK", capture.getvalue())
        self.assertNotIn("private-id", capture.getvalue())

    def test_terminal_timeout_logs_once_after_original_read_retry_budget(self):
        timeout = subprocess.TimeoutExpired(["gh", "api"], 40)
        capture = io.StringIO()
        with redirect_stderr(capture):
            result, error, run, sleep = self.invoke(
                [self.ROUTE], [timeout] * 3)
        self.assertIsNone(result)
        self.assertEqual(error, "F139_GITHUB_API_TIMEOUT")
        self.assertEqual(run.call_count, 3)
        self.assertEqual([c.args[0] for c in sleep.call_args_list], [1, 2])
        lines = capture.getvalue().splitlines()
        self.assertEqual(len(lines), 1)
        report = json.loads(lines[0].split("=", 1)[1])
        self.assertEqual(report["route_family"], "BRANCH")
        self.assertEqual(report["failure"], "GITHUB_API_TIMEOUT")
        self.assertEqual(report["attempts"], 3)
        self.assertIsNone(report["http_status"])

    def test_successful_recovery_or_write_never_emits_read_diagnostic(self):
        failed = SimpleNamespace(
            returncode=1, stdout=b"", stderr=b"HTTP 503")
        success = SimpleNamespace(returncode=0, stdout=b"{}", stderr=b"")
        capture = io.StringIO()
        with redirect_stderr(capture):
            result, error, read, _ = self.invoke(
                [self.ROUTE], [failed, success])
            _, post_error, write, _ = self.invoke(
                ["--method", "POST", self.ROUTE], [failed])
        self.assertEqual(result, b"{}")
        self.assertIsNone(error)
        self.assertEqual(post_error, "F139_GITHUB_API_TRANSIENT")
        self.assertEqual(read.call_count, 2)
        self.assertEqual(write.call_count, 1)
        self.assertEqual(capture.getvalue(), "")

    def test_frozen_engine_before_after_comparison(self):
        """Exercise real FORGE functions; faults are synthetic, not live evidence."""
        import ast
        import copy
        import hashlib
        import json
        import os
        from pathlib import Path
        import local_controller as controller

        root = Path(__file__).resolve().parents[1]
        baseline = "80ae30719bcd9f179da4aa4e8f14dc36fd15818e"
        previous = "556d61f795cab1a042d26b46bbc1087dd436f52d"
        def source_at(commit):
            return subprocess.check_output(
                ["git", "show", commit + ":f139/local_controller.py"], cwd=root)
        def function(raw):
            cls = next(x for x in ast.parse(raw).body
                       if isinstance(x, ast.ClassDef) and x.name == "GitHub")
            node = copy.deepcopy(next(x for x in cls.body
                if isinstance(x, ast.FunctionDef) and x.name == "_command"))
            node.decorator_list = []
            return node
        def load(raw):
            node = function(raw)
            namespace = {name: getattr(controller, name) for name in
                ("require", "F139Error", "shutil", "subprocess", "time", "re", "MAX_ZIP_BYTES")}
            exec(compile(ast.Module(body=[node], type_ignores=[]),
                         "<pinned-forge-transport>", "exec"), namespace)
            return namespace["_command"]
        candidate_source = Path(controller.__file__).read_bytes()
        head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root,
                                       text=True).strip()
        clean = candidate_source.replace(b"\r\n", b"\n") == source_at("HEAD").replace(b"\r\n", b"\n")
        if os.environ.get("GITHUB_ACTIONS") == "true":
            self.assertTrue(clean, "candidate function source drift")
        sources = {"single_attempt": source_at(baseline),
                   "prior_retry": source_at(previous),
                   "status_first_retry": candidate_source}
        ok = SimpleNamespace(returncode=0, stdout=b"{}", stderr=b"")
        def fail(text):
            return SimpleNamespace(returncode=1, stdout=b"", stderr=text.encode())
        recoveries = [subprocess.TimeoutExpired(["gh", "api"], 40),
                      fail("HTTP 503"), fail("HTTP 429"), fail("connection reset")]
        rejections = [fail(text) for text in (
            "HTTP 401: API rate limit exceeded", "HTTP 401: connection reset",
            "HTTP 403: connection reset", "HTTP 403: missing rate limit permission",
            "HTTP 404: API rate limit exceeded", "HTTP 404: connection reset",
            "HTTP 422: temporary failure")]
        metrics = {}
        for name, raw in sources.items():
            command = load(raw)
            row = dict(recovered_reads=0, terminal_read_extra_calls=0,
                       mutation_extra_calls=0, total_calls=0)
            for failure in recoveries:
                result, error, run, sleep = self.invoke([self.ROUTE], [failure, ok], command)
                row["recovered_reads"] += int(result == b"{}" and error is None)
                row["total_calls"] += run.call_count
                self.assertLessEqual(run.call_count, 3)
                self.assertLessEqual(sum(c.args[0] for c in sleep.call_args_list), 3)
            for failure in rejections:
                result, error, run, sleep = self.invoke([self.ROUTE], [failure] * 3, command)
                self.assertIsNone(result)
                self.assertIsNotNone(error)
                row["terminal_read_extra_calls"] += run.call_count - 1
                row["total_calls"] += run.call_count
            for method in ("POST", "PATCH", "PUT", "DELETE"):
                for failure in (subprocess.TimeoutExpired(["gh", "api"], 40), fail("HTTP 503")):
                    result, error, run, sleep = self.invoke(
                        ["--method", method, self.ROUTE], [failure] * 3, command)
                    self.assertIsNone(result)
                    self.assertIsNotNone(error)
                    row["mutation_extra_calls"] += run.call_count - 1
                    row["total_calls"] += run.call_count
                    sleep.assert_not_called()
            result, error, run, sleep = self.invoke([self.ROUTE], [ok], command)
            self.assertEqual(result, b"{}")
            self.assertEqual(run.call_count, 1)
            row["total_calls"] += run.call_count
            metrics[name] = row
        self.assertEqual(metrics["single_attempt"]["recovered_reads"], 0)
        self.assertEqual(metrics["prior_retry"]["recovered_reads"], 4)
        self.assertEqual(metrics["prior_retry"]["terminal_read_extra_calls"], 14)
        self.assertEqual(metrics["status_first_retry"], dict(
            recovered_reads=4, terminal_read_extra_calls=0,
            mutation_extra_calls=0, total_calls=24))
        self.assertTrue(all(row["mutation_extra_calls"] == 0 for row in metrics.values()))
        def function_hash(raw):
            node = function(raw)
            lines = raw.replace(b"\r\n", b"\n").splitlines(keepends=True)
            return hashlib.sha256(b"".join(lines[node.lineno - 1:node.end_lineno])).hexdigest()
        receipt = {"schema": "forge.engine.transport-development.v1",
            "baseline_sha": baseline, "previous_sha": previous,
            "candidate_sha": head if clean else None,
            "candidate_source_clean": clean, "fault_injection_only": True,
            "autonomous_self_improvement_proven": False, "promotion_authority": False,
            "line_endings_normalized": True,
            "harness_sha256": hashlib.sha256(Path(__file__).read_bytes().replace(b"\r\n", b"\n")).hexdigest(),
            "function_sha256": {name: function_hash(raw) for name, raw in sources.items()},
            "metrics": metrics}
        print("FORGE_ENGINE_TRANSPORT_DEV_COMPARISON=" + json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    unittest.main()
