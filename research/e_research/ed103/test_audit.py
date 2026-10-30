import importlib.util
import json
import unittest
from pathlib import Path
spec = importlib.util.spec_from_file_location('ed103', str(Path(__file__).with_name('audit.py')))
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)


def complete():
    return {'status': 'FROZEN_APPROVED', 'source': {'commit_sha': c.COMMIT, 'memory_blob': c.BLOB, 'runtime_receipt_uri': 'not_verified'},
            'freeze': {'approval_ref': 'unverified', 'reviewer_ref': 'unverified', 'split_registry_sha256': '0'*64},
            'budget': {'episodes': 100, 'environment_steps': 1000, 'cpu_seconds': 100.0, 'peak_rss_bytes': 10000, 'train_updates': 5},
            'interface': dict.fromkeys(['observations', 'actions', 'reset_policy', 'termination_policy'], 'unverified'),
            'witness': {'independent_run_ref': 'unverified', 'original_logs_sha256': '0'*64},
            'holdout_access': 'PROHIBITED_UNTIL_INDEPENDENT_APPROVAL'}

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
    def test_complete_only_schema(self): self.assertEqual(c.audit(complete())['verdict'], 'SCHEMA_COMPLETE_REQUIRES_INDEPENDENT_VERIFICATION')

if __name__=='__main__': unittest.main()
