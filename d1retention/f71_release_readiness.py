"""F71: authentic existing Worker/D1 deployment facts, never scientific admission.

The production Worker must not import the F70 synthetic claim function.
A readable D1 bookmark is not a private restorable backup. No export is
attempted: Cloudflare's D1 export can temporarily block live DB queries.
Only GETs and bounded SELECTs are permitted.
"""
from __future__ import annotations
import json
import os
import sys
import install_remote as cf
import r18c_witness as witness
import r34_live_worker_capabilities as versions

SCHEMA="forge.f71.real-deployment-firstuse-denial.v1"
NAMES={
    "forge_original_preuse_claims",
    "forge_original_preuse_claims_update_immutable",
    "forge_original_preuse_claims_delete_immutable",
    "forge_original_preuse_claims_insert_monotonic",
}
class Blocked(RuntimeError):
    pass

def require(value,code):
    if not value: raise Blocked("F71_"+code)

def inspect(api):
    """Inspect existing serving Worker & associated D1, no active release."""
    capability=versions.scan(api)
    require(capability.get("exact_single_live_version") is True and
            capability.get("d1_bindings")==1 and
            capability.get("scientific_execution_authorized") is False and
            capability.get("read_only") is True,
            "WORKER_BINDING_IDENTITY_INVALID")
    database=cf.single_deployed_database(api)
    owned,foreign=cf.schema_snapshot(api,database)
    require(owned==cf.EXPECTED_OBJECTS and
            foreign==witness.BASELINE_SCHEMA_SHA256,
            "PRESERVED_SIX_ARCHIVE_SCHEMA_CHANGED")
    for table in ("forge_research_originals","forge_research_seals"):
        row=cf.sql_query(api,database,"SELECT COUNT(*) AS n FROM "+table)
        require(len(row)==1 and type(row[0].get("n")) is int and
                row[0]["n"]==6,"SIX_ARCHIVED_ORIGINALS_CHANGED")
    listed=cf.sql_query(api,database,
      "SELECT name,type FROM sqlite_master WHERE name IN "
      "('forge_original_preuse_claims',"
      "'forge_original_preuse_claims_update_immutable',"
      "'forge_original_preuse_claims_delete_immutable',"
      "'forge_original_preuse_claims_insert_monotonic') ORDER BY name")
    observed={(row.get("name"),row.get("type")) for row in listed}
    require(len(observed)==len(listed) and len(observed)<=4,
            "FIRSTUSE_SCHEMA_RESULT_UNBOUNDED_OR_DUPLICATED")
    missing=NAMES-{name for name,_ in observed}
    # Partial deployment can be dangerous. Fail closed with a precise
    # reason and never call an INSERT or attempt an automatic repair.
    require(not observed or (
       len(observed)==4 and
       ("forge_original_preuse_claims","table") in observed and
       all((name,"trigger") in observed for name in NAMES if name!="forge_original_preuse_claims")),
       "PARTIAL_FIRSTUSE_SCHEMA_NEEDS_MANUAL_RECONCILIATION")
    bookmark=cf.recovery_bookmark(api,database)
    require(type(bookmark) is str and 20<=len(bookmark)<=160,
            "D1_RECOVERY_BOOKMARK_UNAVAILABLE")
    # Bookmark never emitted to logs/artifacts; no private backup exported.
    reasons=[
      "NO_INDEPENDENT_AUTHENTIC_CURRENT_SCIENCE_OWNER_EPOCH",
      "NO_COMPLETE_INDEPENDENT_TWO_LANE_CONSUMED_ACTIVE_UNCERTAIN_FIRSTUSE",
      "NO_PRIVATE_RESTORABLE_D1_BACKUP",
      "NO_WORKER_SIDE_VERIFIED_EXECUTION_PERMIT",
      "NO_PROTECTED_MAIN_SCIENCE_AUTHORIZATION",
    ]
    if missing:
        reasons.append("NO_ATOMIC_FIRSTUSE_TABLE_IN_SERVING_D1")
    report={
      "schema":SCHEMA,
      "existing_serving_worker_single_version_verified":True,
      "existing_cloudflare_d1_binding_verified":True,
      "six_historical_originals_and_seals_preserved":True,
      "real_d1_recovery_bookmark_readable":True,
      "private_restorable_backup_qualified":False,
      "firstuse_schema_complete_in_actual_serving_d1":not bool(missing),
      "immutable_and_monotonic_trigger_names_observed":len(observed)==4,
      "real_current_scientific_owner_independently_attested":False,
      "live_complete_two_lane_original_firstuse_custody":False,
      "real_prospective_original_budget_authorized":False,
      "worker_execution_permit_issued":False,
      "production_original_claim_insert_performed":False,
      "worker_or_scientific_controller_modified":False,
      "scientific_originals_dispatched":0,
      "owner_cutover_authorized":False,
      "deployment_release_blockers":sorted(reasons),
      "disposition":"BLOCKED_REAL_OWNER_COHORT_BACKUP_AND_WORKER_RELEASE_NOT_ESTABLISHED"
    }
    return report

if __name__=="__main__":
    try:
        c=cf.Cloudflare(os.environ.get("CLOUDFLARE_ACCOUNT_ID",""),
                        os.environ.get("CLOUDFLARE_API_TOKEN",""))
        print(json.dumps(inspect(c),sort_keys=True,separators=(",",":")))
        print("F71_CURRENT_WORKER_AND_D1=OBSERVED_ONLY")
        print("F71_OWNER_CUSTODY_AND_ORIGINAL_RELEASE=DENIED")
    except (Blocked,cf.InstallBlocked,ValueError,TypeError) as exc:
        print("F71_LIVE_DEPLOYMENT_STATUS=BLOCKED",file=sys.stderr)
        print("F71_BLOCK_REASON="+type(exc).__name__,file=sys.stderr)
        raise SystemExit(1)
