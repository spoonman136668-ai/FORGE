"""Isolated orchestration checks; never inspect the real owner or database."""
import unittest
import subprocess
import contextlib
import io
import json
from unittest.mock import patch
from f139 import h53_original_owner_audit as audit

class AuditTests(unittest.TestCase):
    def fixture_audit(self, error=None):
        with patch.object(audit.os, 'name', 'nt'), \
             patch.object(audit, 'verify_checkout', return_value='a'*40), \
             patch.object(audit.pathlib.Path, 'read_text', return_value='{}'), \
             patch.dict(audit.os.environ, {k:'fixture' for k in (
                 'GITHUB_EVENT_PATH','GITHUB_ACTOR','GITHUB_REPOSITORY',
                 'GITHUB_REF','GITHUB_RUN_ATTEMPT','RUNNER_NAME')}), \
             patch.object(audit.guard, 'event_guard'), \
             patch.object(audit.authority, 'verify_authority', return_value={}), \
             patch.object(audit.owner, 'inspect_original', return_value={
                 'database':'fixture.sqlite','repository_root':'.',
                 'source_sha':audit.guard.SOURCE}), \
             patch.object(audit.native, 'verify_native', return_value={'native_cold_verify':'PASS'}), \
             patch.object(audit.native.witness, 'scheduler_observation', return_value={'last_result':0}, side_effect=error) as scheduler:
            result = audit.audit()
        scheduler.assert_called_once_with()
        return result

    def test_readonly_receipt_includes_scheduler_and_no_autonomy_claim(self):
        result = self.fixture_audit()
        self.assertEqual(result['audit_status'], 'PASS')
        self.assertEqual(result['scheduler'], {'last_result':0})
        self.assertFalse(result['unattended_cycle_verified'])
        self.assertFalse(result['scientific_first_use_authorized'])
        self.assertEqual(result['original_database_writes'], 0)
        self.assertEqual(result['owner_task_mutations'], 0)

    def test_scheduler_failure_preserves_native_receipt_and_failure_exit(self):
        errors = [
            subprocess.CalledProcessError(1, ['pwsh'], stderr='x'*3000),
            subprocess.TimeoutExpired(['pwsh'], 45, stderr=b'timed out'),
            ValueError('invalid scheduler JSON'),
            RuntimeError('F139_H53_OWNER_TASK_DRIFT'),
        ]
        for error in errors:
            with self.subTest(error=type(error).__name__):
                result = self.fixture_audit(error)
                self.assertEqual(result['audit_status'], 'INCOMPLETE')
                self.assertEqual(result['ledger']['native_cold_verify'], 'PASS')
                self.assertEqual(result['scheduler']['status'], 'UNVERIFIED')
                self.assertLessEqual(len(result['scheduler']['stderr_tail']), 2048)
                self.assertFalse(result['unattended_cycle_verified'])
                output = io.StringIO()
                with patch.object(audit, 'audit', return_value=result), contextlib.redirect_stdout(output):
                    with self.assertRaises(SystemExit) as caught:
                        audit.main()
                self.assertEqual(caught.exception.code, 1)
                self.assertEqual(json.loads(output.getvalue()), result)

if __name__ == '__main__':
    unittest.main()
