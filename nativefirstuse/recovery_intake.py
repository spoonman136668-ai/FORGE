"""FORGE-native private recovery evidence intake (non-executing).

No Cloudflare write, no backup export to GitHub, no CKB-plane integration.
Makes pending external recovery obligations machine-readable without treating
caller attestations or synthetic tests as private restored-byte evidence.
"""
from __future__ import annotations
import json, hashlib, pathlib
from private_recovery import SCHEMA,verify,NotQualified

REPORT_SCHEMA="forge.native.d1.private-recovery-evidence-intake.v1"
class Denied(ValueError):pass

def inspect_private_recovery_bytes(raw:bytes, independently_trusted_verifier=None):
 if type(raw) is not bytes or not 0<len(raw)<=32768:raise Denied("RECOVERY_INPUT_SIZE")
 try:
  text=raw.decode("utf-8")
  doc=json.loads(text,object_pairs_hook=_unique)
 except (UnicodeError,ValueError,TypeError) as exc:raise Denied("RECOVERY_MALFORMED") from exc
 if type(doc) is not dict or doc.get("schema")!=SCHEMA:raise Denied("RECOVERY_SCHEMA")
 if independently_trusted_verifier is None:raise Denied("NO_INDEPENDENT_PRIVATE_RESTORE_VERIFIER")
 try:review=verify(doc,independently_trusted_verifier)
 except (NotQualified,ValueError,TypeError) as exc:raise Denied("RECOVERY_NOT_QUALIFIED") from exc
 return {"schema":REPORT_SCHEMA,
  "private_manifest_digest_sha256":hashlib.sha256(raw).hexdigest(),
  "recovery_independently_reviewed":review["external_restoration_reviewed"],
  "separate_migration_approval_required":True,
  "cloudflare_schema_changed":False,
  "cloudflare_firstuse_claim_consumed":False,
  "original_experiment_started":False,
  "dream_pareto_activated":False,
  "status":"PRIVATE_RESTORE_REVIEWED_SEPARATE_OPERATIONAL_GATE_REQUIRED"}

def _unique(pairs):
 d={}
 for k,v in pairs:
  if k in d:raise Denied("DUPLICATE_FIELD")
  d[k]=v
 return d

def main():
 raise SystemExit("NO_CLI_LIVE_RECOVERY_AVAILABLE: source-only intake; private operator-controlled verifier required")
if __name__=="__main__":main()
