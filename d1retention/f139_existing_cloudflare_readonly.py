"""F139: live observation of the EXISTING FORGE Cloudflare Worker and D1.

Bounded, read-only SQL SELECT and authenticated provider metadata calls.
No mutation, remote migration, private-data export, signer or science permit.
Reuses the previously verified October 15 R39/F62 provider client exactly.
"""
import datetime
import hashlib
import json
import os
import sys

import install_remote as cf
import r18c_witness as witness

SCHEMA = "forge.f139.existing-cloudflare-fsa-readonly-observation.v1"
OCTOBER_15_SOURCE = "d6997b8f2953958ea542d472d8d4187694ef20cd"

# Only metadata of specifically known first-use objects. No user data or
# scientific source, secrets, private signer identities, rows or bookmarks.
KNOWN = (
    "forge_original_preuse_claims",
    "forge_original_preuse_claims_update_immutable",
    "forge_original_preuse_claims_delete_immutable",
    "forge_original_preuse_claims_insert_monotonic",
    "authority_state", "original_firstuse",
    "close_global_slot_after_firstuse",
    "no_update_original_firstuse", "no_delete_original_firstuse",
    "no_replace_original_firstuse",
)
LEGACY = frozenset(KNOWN[:4])
CURRENT = frozenset(KNOWN[4:])
class Drift(Exception):
    pass

def check(ok, msg):
    if not ok:
        raise Drift(msg)

def audit(api):
    db = cf.single_deployed_database(api)
    original_names, foreign_sha = cf.schema_snapshot(api, db)
    check(original_names == cf.EXPECTED_OBJECTS, "ARCHIVE_NAMESPACE_DRIFT")
    counts = {}
    for table in ("forge_research_originals", "forge_research_seals"):
        rows = cf.sql_query(api, db, "SELECT COUNT(*) AS n FROM " + table)
        check(len(rows) == 1 and type(rows[0].get("n")) is int
              and rows[0]["n"] == 6, "ARCHIVED_ORIGINAL_OR_SEAL_COUNT_DRIFT")
        counts[table] = rows[0]["n"]
    # Bounded constant list -- never accept untrusted names or arbitrary SQL.
    quoted = ",".join("'" + name + "'" for name in KNOWN)
    rows = cf.sql_query(api, db,
        "SELECT type,name FROM sqlite_master WHERE name IN ("
        + quoted + ") ORDER BY name LIMIT 32")
    check(len(rows) <= len(KNOWN), "FSA_METADATA_INCOMPLETE")
    observed = set()
    for row in rows:
        check(type(row.get("name")) is str and row["name"] in KNOWN
              and row.get("type") in ("table", "trigger")
              and row["name"] not in observed, "FSA_METADATA_INVALID")
        observed.add(row["name"])
    check(isinstance(cf.recovery_bookmark(api, db), str),
          "D1_TIME_TRAVEL_BOOKMARK_NOT_READABLE")
    return {
        "schema": SCHEMA,
        "source_snapshot_commit": OCTOBER_15_SOURCE,
        "observed_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "existing_worker_d1_binding_provider_authenticated": True,
        "database_identity_sha256": hashlib.sha256(db.encode()).hexdigest(),
        "archived_originals_count": counts["forge_research_originals"],
        "archived_seals_count": counts["forge_research_seals"],
        "archive_namespace_intact": True,
        "october_15_foreign_schema_unchanged": foreign_sha == witness.BASELINE_SCHEMA_SHA256,
        "observed_known_firstuse_objects": sorted(observed),
        "historical_f61_f62_preuse_objects_present": sorted(LEGACY.intersection(observed)),
        "f139_pending_reservation_objects_present": sorted(CURRENT.intersection(observed)),
        "d1_time_travel_bookmark_readable": True,
        "independent_private_backup_verified": False,
        "independent_fsa_signer_witness_verified": False,
        "complete_all_lane_firstuse_ledger_verified": False,
        "f139_start_receipt_authorized": False,
        "d1_writes_performed": 0,
        "worker_dispatch_performed": False,
        "disposition": "READONLY_LIVE_FSA_CUSTODY_INVENTORY_NO_SCIENCE_PERMISSION",
    }

def main():
    api = cf.Cloudflare(os.environ.get("CLOUDFLARE_ACCOUNT_ID", ""),
                        os.environ.get("CLOUDFLARE_API_TOKEN", ""))
    print(json.dumps(audit(api), sort_keys=True, separators=(",", ":")))

if __name__ == "__main__":
    try:
        main()
    except (cf.InstallBlocked, Drift) as error:
        # Print class only; never leak provider response, token, IDs or records.
        print("F139_EXISTING_D1_READONLY_STOP=" + type(error).__name__, file=sys.stderr)
        raise SystemExit(1)
