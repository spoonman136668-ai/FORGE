"""D2K original-HMAC admission and credential-free job-bound negative controls."""
import hashlib
import json
from pathlib import Path
import re
import unittest

from f139.d2k_job_claim import SCHEMA, FIELDS, authorize, digest, verify_claim
from f139.test_issue_diagnostic import authorized
from f139.verify_ticket import Untrusted

WORKFLOW = Path(__file__).resolve().parents[1] / ".github/workflows/forge-f139-development-worker.yml"


class D2KJobIsolationTests(unittest.TestCase):
    def test_signed_original_bound_to_separate_diagnostic_job(self):
        original = authorized()
        claim = authorize(original)
        payload = {"schema": SCHEMA, **{name: original[name] for name in FIELDS}}
        expected = hashlib.sha256(
            (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()
        ).hexdigest()
        self.assertEqual(claim, expected)
        self.assertEqual(digest(original), claim)
        self.assertTrue(verify_claim(dict(original, key=""), {
            "GITHUB_JOB": "d2k-execute", "F139_D2K_AUTHORIZATION_SHA256": claim,
        }))

    def test_missing_job_claim_and_credentials_fail_closed(self):
        original = authorized()
        claim = authorize(original)
        for variant in (
            {"GITHUB_JOB": "execute"},
            {"F139_D2K_AUTHORIZATION_SHA256": "0"*64},
            {"F139_D2K_AUTHORIZATION_SHA256": ""},
            {"F139_WORKER_HMAC_KEY": "test"},
            {"GH_TOKEN": "test"}, {"GITHUB_TOKEN": "test"},
            {"OPENAI_API_KEY": "test"},
        ):
            env = {"GITHUB_JOB": "d2k-execute",
                   "F139_D2K_AUTHORIZATION_SHA256": claim, **variant}
            with self.subTest(variant=variant):
                with self.assertRaises(Untrusted):
                    verify_claim(dict(original, key=""), env)

    def test_original_signed_issue_is_not_reusable_for_new_job_identity(self):
        original = authorized()
        claim = authorize(original)
        for key, value in (
            ("issue_number", "1402"), ("target_package", "./dreamrsi"),
            ("run_id", "12346"), ("head_sha", "a"*40),
            ("signature", "0"*64), ("lane", "Wingless"),
        ):
            changed = dict(original, key="")
            changed[key] = value
            with self.subTest(field=key):
                with self.assertRaises(Untrusted):
                    verify_claim(changed, {
                        "GITHUB_JOB": "d2k-execute",
                        "F139_D2K_AUTHORIZATION_SHA256": claim,
                    })
        with self.assertRaises(Untrusted):
            authorize(dict(original, signature="0"*64))

    def test_workflow_authentication_is_never_in_same_vm_as_d2k_go(self):
        raw = WORKFLOW.read_text(encoding="utf-8")
        fields = re.split(r"(?m)^  ([a-z][a-z0-9-]*):\s*$", raw)
        jobs = {fields[i]:fields[i+1] for i in range(1, len(fields)-1, 2)}
        for key in ("execute", "d2k-admit", "d2k-execute", "d2k-receipt"):
            self.assertIn(key, jobs)
        self.assertIn("!startsWith(inputs.ticket, 'f139-d2k-')", jobs["execute"])
        self.assertIn("needs: d2k-admit", jobs["d2k-execute"])
        self.assertIn("needs.d2k-admit.result == 'success'", jobs["d2k-execute"])
        self.assertIn("needs.d2k-admit.outputs.authorization", jobs["d2k-execute"])
        self.assertIn("needs.d2k-execute.result == 'success'", jobs["d2k-receipt"])
        self.assertNotIn("secrets.F139_WORKER_HMAC_KEY", jobs["d2k-execute"])
        self.assertNotIn("F139_WORKER_HMAC_KEY:", jobs["d2k-execute"].split("steps:")[0])
        for restricted in ("d2k-admit", "d2k-receipt"):
            self.assertNotIn("secrets.F139_WORKER_HMAC_KEY", jobs[restricted].split("steps:")[0])
            self.assertIn("F139_WORKER_HMAC_KEY: $" + "{{ secrets.F139_WORKER_HMAC_KEY }}", jobs[restricted])
            self.assertNotIn("go test", jobs[restricted])
            self.assertNotIn("f139.issue_diagnostic --output", jobs[restricted])
        self.assertNotIn("f139.verify_ticket --diagnostic", jobs["d2k-execute"])
        self.assertIn("f139.verify_ticket --diagnostic", jobs["d2k-receipt"])
        self.assertIn("forge-f139-dev-receipt-", jobs["d2k-receipt"])
        self.assertIn("forge-f139-cpu-development-", jobs["d2k-execute"])


if __name__ == "__main__":
    unittest.main()
