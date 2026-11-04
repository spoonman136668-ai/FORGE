import json
import subprocess
import unittest
from scripts.f139_owner_github_readonly_probe import probe, ROUTES, OWNER_API_STDOUT_LIMIT


class OwnerReadOnlyProbeTests(unittest.TestCase):
    def run_probe(self, stdout=b"", stderr=b"", code=1, exception=None):
        calls = []
        def runner(argv, **kwargs):
            calls.append((argv, kwargs))
            if exception:
                raise exception
            return subprocess.CompletedProcess(argv, code, stdout, stderr)
        report = probe(environment={"PATH": "safe", "APPDATA": "owner-config",
                                    "GH_TOKEN": "job-secret", "GITHUB_TOKEN": "secret",
                                    "F139_WORKER_HMAC_KEY": "hmac-secret"}, runner=runner)
        self.assertEqual(len(calls), len(ROUTES))
        for (argv, kwargs), route in zip(calls, ROUTES):
            self.assertEqual(argv, ["gh", "api", "--hostname", "github.com",
                                    "--method", "GET", "--include", route])
            self.assertEqual(kwargs["timeout"], 20)
            self.assertEqual(kwargs["env"]["APPDATA"], "owner-config")
            self.assertNotIn("GH_TOKEN", kwargs["env"])
            self.assertNotIn("GITHUB_TOKEN", kwargs["env"])
            self.assertNotIn("F139_WORKER_HMAC_KEY", kwargs["env"])
        encoded = json.dumps(report)
        for secret in ("job-secret", "hmac-secret", "RAW_SECRET_MARKER"):
            self.assertNotIn(secret, encoded)
        self.assertFalse(report["controller_inherited_environment_verified"])
        self.assertEqual(report["dispatches"], 0)
        return report["reads"][0]

    def test_read_success_does_not_export_body(self):
        row = self.run_probe(b"HTTP/2.0 200 OK\r\nx-ratelimit-remaining: 42\r\n\r\nRAW_SECRET_MARKER", code=0)
        self.assertEqual(row["classification"], "READ_OK")
        self.assertEqual(row["rate_limit_remaining"], 42)

    def test_unauthorized_and_forbidden_are_distinct(self):
        for status, expected in ((401, "AUTHENTICATION_REJECTED"), (403, "FORBIDDEN_OR_RATE_LIMITED"), (429, "RATE_LIMITED"), (404, "HTTP_FAILURE")):
            with self.subTest(status=status):
                row = self.run_probe(stderr=f"gh: rejected RAW_SECRET_MARKER (HTTP {status})".encode())
                self.assertEqual(row["classification"], expected)

    def test_rate_limit_exhaustion(self):
        self.assertEqual(self.run_probe(b"HTTP/2.0 403 Forbidden\r\nx-ratelimit-remaining: 0\r\n")["classification"], "RATE_LIMITED")

    def test_no_auth_and_unknown_failure(self):
        self.assertEqual(self.run_probe(stderr=b"run gh auth login")["classification"], "NO_CLI_AUTHENTICATION")
        self.assertEqual(self.run_probe(stderr=b"RAW_SECRET_MARKER")["classification"], "CLI_OR_TRANSPORT_FAILURE")

    def test_timeout_has_no_retry_or_exception_leak(self):
        error = subprocess.TimeoutExpired("RAW_SECRET_MARKER", 20)
        self.assertEqual(self.run_probe(exception=error)["classification"], "READ_TIMEOUT")

    def test_original_stdout_bound_is_measured_without_exporting_body(self):
        from f139.local_controller import MAX_ZIP_BYTES
        self.assertEqual(OWNER_API_STDOUT_LIMIT, MAX_ZIP_BYTES + 100000)
        row = self.run_probe(b"HTTP/2.0 200 OK\r\n\r\n" + b"x" * OWNER_API_STDOUT_LIMIT, code=0)
        self.assertTrue(row["original_stdout_limit_exceeded"])
        self.assertEqual(row["response_body_bytes"], OWNER_API_STDOUT_LIMIT)
        self.assertEqual(row["classification"], "READ_OK")

    def test_missing_cli_is_explicit(self):
        self.assertEqual(self.run_probe(exception=FileNotFoundError("RAW_SECRET_MARKER"))["classification"], "CLI_NOT_FOUND")


if __name__ == "__main__":
    unittest.main()
