import json, unittest
from recovery_intake import inspect_private_recovery_bytes,Denied
from test_private_recovery import base
class TestRecoveryIntake(unittest.TestCase):
 def test_rejects_self_attestation_without_independent_verifier(self):
  raw=json.dumps(base()).encode()
  with self.assertRaises(Denied):inspect_private_recovery_bytes(raw)
 def test_nonexecuting_fixture(self):
  raw=json.dumps(base()).encode()
  review=inspect_private_recovery_bytes(raw,lambda d:True)
  self.assertTrue(review["recovery_independently_reviewed"])
  for flag in ("cloudflare_schema_changed","cloudflare_firstuse_claim_consumed","original_experiment_started","dream_pareto_activated"):
   self.assertFalse(review[flag])
 def test_rejects_duplicate_fields_and_mismatched_restoration(self):
  with self.assertRaises(Denied):inspect_private_recovery_bytes(b'{"schema":"x","schema":"y"}',lambda d:True)
  d=base();d["restore_archive_digest_sha256"]="f"*64
  with self.assertRaises(Denied):inspect_private_recovery_bytes(json.dumps(d).encode(),lambda d:True)
