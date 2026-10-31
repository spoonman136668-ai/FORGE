import importlib.util
import json
import unittest
from pathlib import Path
spec = importlib.util.spec_from_file_location('ed103', str(Path(__file__).with_name('audit.py')))
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)


def complete():
    """Structurally plausible SYNTHETIC values; no authenticity implied."""
    return {
        'status': 'FROZEN_APPROVED',
        'source': {
            'commit_sha': c.COMMIT, 'memory_blob': c.BLOB,
            'runtime_receipt_uri': 'https://github.com/example/repo/actions/runs/123456',
        },
        'freeze': {
            'approval_ref': 'scientific-protocol-review-123',
            'reviewer_ref': 'independent-reviewer-123',
            'split_registry_sha256': 'a' * 64,
        },
        'budget': {
            'episodes': 100, 'environment_steps': 1000,
            'cpu_seconds': 100.0, 'peak_rss_bytes': 10000, 'train_updates': 5,
        },
        'interface': {
            'observations': 'public-image-direction-mission',
            'actions': 'public-seven-actions',
            'reset_policy': 'per-seed-cold-reset',
            'termination_policy': 'source-terminated-or-truncated',
        },
        'witness': {
            'independent_run_ref': 'https://github.com/example/repo/actions/runs/654321',
            'original_logs_sha256': 'b' * 64,
        },
        'holdout_access': 'PROHIBITED_UNTIL_INDEPENDENT_APPROVAL',
    }


class Checks(unittest.TestCase):
    def test_nonobject_rejected(self): self.assertEqual(c.audit([])['verdict'], 'NOT_QUALIFIED')
    def test_prospective_rejected(self): self.assertIn('status_not_frozen_approved', c.audit({'status':'PROSPECTIVE_NOT_AUTHORIZED_OR_FROZEN'})['reasons'])
    def test_missing_budget_rejected(self): self.assertIn('missing_section_budget', c.audit({})['reasons'])
    def test_bad_source_rejected(self): self.assertIn('unverified_source_commit', c.audit(complete() | {'source': {'commit_sha': 'wrong'}})['reasons'])
    def test_nonfinite_rejected(self):
        for v in (float('nan'),float('inf'),float('-inf')):
            with self.subTest(v=v):
                m=complete();m['budget']['cpu_seconds']=v
                self.assertIn('invalid_budget_cpu_seconds',c.audit(m)['reasons'])
    def test_fractional_counts_rejected(self):
        m=complete();m['budget']['episodes']=1.5
        self.assertIn('invalid_budget_episodes',c.audit(m)['reasons'])
    def test_bool_rejected(self):
        m=complete();m['budget']['train_updates']=True
        self.assertIn('invalid_budget_train_updates',c.audit(m)['reasons'])
    def test_bad_digest_rejected(self):
        m=complete();m['freeze']['split_registry_sha256']='fake'
        self.assertIn('invalid_digest_freeze.split_registry_sha256',c.audit(m)['reasons'])

    def test_placeholder_references_rejected(self):
        for section, field in (
            ('source', 'runtime_receipt_uri'),
            ('freeze', 'approval_ref'),
            ('freeze', 'reviewer_ref'),
            ('witness', 'independent_run_ref'),
        ):
            with self.subTest(section=section, field=field):
                m = complete(); m[section][field] = 'nOt_Verified'
                result = c.audit(m)
                self.assertEqual(result['verdict'], 'NOT_QUALIFIED')
                self.assertIn('placeholder_' + section + '.' + field, result['reasons'])

    def test_nonstring_reference_rejected(self):
        m = complete(); m['freeze']['approval_ref'] = 42
        self.assertIn('placeholder_freeze.approval_ref', c.audit(m)['reasons'])

    def test_placeholder_observation_interface_rejected(self):
        m = complete(); m['interface']['observations'] = 'TBD'
        self.assertIn('placeholder_interface.observations', c.audit(m)['reasons'])

    def test_zero_digests_rejected(self):
        for section, field in (
            ('freeze', 'split_registry_sha256'),
            ('witness', 'original_logs_sha256'),
        ):
            with self.subTest(section=section):
                m = complete(); m[section][field] = '0' * 64
                self.assertIn('invalid_digest_' + section + '.' + field, c.audit(m)['reasons'])

    def test_zero_is_not_synthetic_approval(self):
        m = complete(); m['freeze']['approval_ref'] = '000000'
        self.assertEqual(c.audit(m)['verdict'], 'NOT_QUALIFIED')

    def test_synthetic_full_manifest_only_requires_verification(self):
        # A syntactically plausible but fabricated record must NEVER equal PASS.
        result = c.audit(complete())
        self.assertEqual(result['verdict'], 'SCHEMA_COMPLETE_REQUIRES_INDEPENDENT_VERIFICATION')

if __name__=='__main__': unittest.main()
