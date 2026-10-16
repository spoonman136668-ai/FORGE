"""FORGE-native D1 backup clearance, not a backup producer or install permit.

Accepts a real PRIVATE independently restored D1 archive inspection manifest.
A Time Travel bookmark, self-reported schema, or prior CI run is not a verified
restore. This code neither reads private data nor accesses a network.
"""
import re
SCHEMA="forge.native.d1.private-restorable-backup.v1"
HEX64=re.compile(r"[0-9a-f]{64}\Z")
UUID=re.compile(r"[a-f0-9]{8}-(?:[a-f0-9]{4}-){3}[a-f0-9]{12}\Z")
class NotQualified(ValueError):pass
def require(ok,why):
 if not ok:raise NotQualified("FORGE_NATIVE_RECOVERY_"+why)
def verify(inspection, independent_verifier=None):
 require(type(inspection) is dict and inspection.get("schema")==SCHEMA,"SCHEMA_REQUIRED")
 require(independent_verifier is not None,"EXTERNAL_VERIFIER_REQUIRED")
 for f in ("database_id","worker_bound_database_id"):
  require(isinstance(inspection.get(f),str) and UUID.fullmatch(inspection[f]),"DATABASE_ID_REQUIRED")
 require(inspection["database_id"]==inspection["worker_bound_database_id"],"DATABASE_DRIFT")
 for f in ("original_schema_sha256","restore_schema_sha256","original_archive_digest_sha256","restore_archive_digest_sha256","original_seal_digest_sha256","restore_seal_digest_sha256","private_backup_sha256","restored_file_sha256"):
  require(isinstance(inspection.get(f),str) and HEX64.fullmatch(inspection[f]),"MISSING_PRIVATE_DIGEST")
 require(inspection["original_schema_sha256"]==inspection["restore_schema_sha256"],"SCHEMA_RESTORE_DRIFT")
 require(inspection["original_archive_digest_sha256"]==inspection["restore_archive_digest_sha256"],"ARCHIVE_RESTORE_DRIFT")
 require(inspection["original_seal_digest_sha256"]==inspection["restore_seal_digest_sha256"],"SEAL_RESTORE_DRIFT")
 for f in ("private_backup_created_before_migration","restore_tested_on_isolated_database","backup_private_not_public_artifact","restore_verifier_independent","all_six_originals_sealed_and_restored","source_reconciled_no_lease_reuse"):
  require(inspection.get(f) is True,"RECOVERY_OR_OWNER_NOT_QUALIFIED_"+f.upper())
 require(isinstance(inspection.get("owner_epoch"),int) and not isinstance(inspection["owner_epoch"],bool) and inspection["owner_epoch"]>0,"OWNER_EPOCH_MISSING")
 require(inspection.get("source_control")=="FORGE_NATIVE_NOT_CKB","OWNER_SOURCE_UNTRUSTED")
 # Caller claims are never enough. Trust must validate the private backup
 # and restored bytes using an existing independently authorized verifier.
 require(independent_verifier(inspection) is True,"INDEPENDENT_RESTORE_REVIEW_REQUIRED")
 return {"schema":"forge.native.d1.recovery-review.v1","external_restoration_reviewed":True,
         "separate_migration_approval_required":True,"database_install_authorized":False,
         "original_dispatch_authorized":False,"dream_pareto_live":False,
         "status":"PRIVATE_RESTORE_CONTRACT_PASSED_NOT_AN_EXECUTION_PERMIT"}
