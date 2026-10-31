"""Bounded GitHub CLI transport policy for the original F139 owner client."""
import subprocess
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from local_controller import F139Error, GitHub


class GitHubCommandTransportTests(unittest.TestCase):
    ROUTE = "repos/spoonman136668-ai/FORGE/branches/main"

    def invoke(self, args, responses):
        with patch("local_controller.shutil.which", return_value="gh"), \
             patch("local_controller.subprocess.run", side_effect=responses) as run, \
             patch("local_controller.time.sleep") as sleep:
            result = None
            error = None
            try:
                result = GitHub._command(args)
            except F139Error as exc:
                error = str(exc)
            return result, error, run, sleep

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

    def test_failure_classification_does_not_echo_raw_stderr(self):
        failed = SimpleNamespace(
            returncode=1, stdout=b"", stderr=b"HTTP 403 secret-token=DO_NOT_LEAK"
        )
        result, error, run, sleep = self.invoke([self.ROUTE], [failed])
        self.assertIsNone(result)
        self.assertEqual(error, "F139_GITHUB_API_AUTH")
        self.assertNotIn("DO_NOT_LEAK", error)
        self.assertEqual(run.call_count, 1)


if __name__ == "__main__":
    unittest.main()
