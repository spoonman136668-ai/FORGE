import unittest
from private_recovery import verify,NotQualified,SCHEMA
def base():
 return dict(schema=SCHEMA,database_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",worker_bound_database_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
 original_schema_sha256="1"*64,restore_schema_sha256="1"*64,
 original_archive_digest_sha256="2"*64,restore_archive_digest_sha256="2"*64,
 original_seal_digest_sha256="3"*64,restore_seal_digest_sha256="3"*64,
 private_backup_sha256="4"*64,restored_file_sha256="5"*64,
 private_backup_created_before_migration=True,restore_tested_on_isolated_database=True,
 backup_private_not_public_artifact=True,restore_verifier_independent=True,
 all_six_originals_sealed_and_restored=True,source_reconciled_no_lease_reuse=True,
 owner_epoch=1,source_control="FORGE_NATIVE_NOT_CKB")
class TestNativeRecovery(unittest.TestCase):
 def test_even_independent_test_stub_cannot_install(self):
  r=verify(base(),lambda x:True)
  self.assertTrue(r["external_restoration_reviewed"])
  self.assertFalse(r["database_install_authorized"] or r["original_dispatch_authorized"] or r["dream_pareto_live"])
 def test_no_verifier_denied(self):
  with self.assertRaises(NotQualified):verify(base())
 def test_false_authority_and_bad_restore_denied(self):
  for k,v in [("restore_schema_sha256","f"*64),("restore_archive_digest_sha256","f"*64),
   ("restore_seal_digest_sha256","f"*64),("restore_tested_on_isolated_database",False),
   ("source_reconciled_no_lease_reuse",False),("private_backup_created_before_migration",False),
   ("database_id","bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
   ("source_control","CKB"),("owner_epoch",0),("backup_private_not_public_artifact",False)]:
   with self.subTest(k=k):
    a=base();a[k]=v
    with self.assertRaises(NotQualified):verify(a,lambda x:True)
 def test_independent_rejection_denied(self):
  with self.assertRaises(NotQualified):verify(base(),lambda x:False)
