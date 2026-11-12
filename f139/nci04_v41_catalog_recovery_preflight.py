"""Read-only V40-owner -> catalog-repair successor admission; never installs.

This module is deliberately NOT a source-transition schema, CLI, scheduler,
controller, worker, or release permission. Future original-owner source
promotion must independently qualify cold-copy, original lease and task,
production binary, exact approval, rollback, and post-install native receipts.
"""
import json
import re

from f139.local_controller import Database, SingleOwner
from f139.nci04_native_contract import canonical, digest
from f139.nci04_owner_ledger import verify_native_activation
from f139 import nci04_v40_source_transition as v40
from f139 import nci04_partial_publication_custody as partial
from f139 import nci04_ref_only_publication_custody as ref_only

REPO = "spoonman136668-ai/FORGE"
OWNER_SOURCE = "2c7caad5a4502d4b874a11d57207a35cf033eb08"
MERGED_REPAIR = "7fb1bb9e0fe9439a6a7da8b66c6b0ef7acdc7595"
REPAIR_CONTROLLER_BLOB = "5e050403726a7eebf3bcd46b949a1735c929a79c"
REPAIR_NEGATIVE_TEST_BLOB = "04e8f19889d58cde67c8394daab32da630d15ff3"
OBSERVED_SEQ = 1826
OBSERVED_HEAD = "71fd4554315093d74f5a9968b4766191413cfd18d6b1ce81863f8451d379d769"
ELIGIBLE_LABEL = "f139-native-development-eligible"
SCHEMA = "forge.f139.v41.catalog-repair.readonly-custody.v1"
SHA40 = re.compile(r"[a-f0-9]{40}\Z")


class V41ReadOnlyDenied(ValueError):
    pass


def need(ok, reason):
    if not ok:
        raise V41ReadOnlyDenied("F139_V41_READONLY_" + reason)


def _sha(value):
    return type(value) is str and SHA40.fullmatch(value) is not None


def source_preflight(get, target):
    """Bounded, authenticated GET-only evidence for this exact live incident.

    The caller must supply the existing GitHub native repository GET transport.
    This is data verification, never a capability to fetch arbitrary URLs.
    """
    need(callable(get) and _sha(target) and target != OWNER_SOURCE,
         "EXACT_PROTECTED_TARGET_REQUIRED")
    prefix = "repos/" + REPO + "/"
    def read(route):
        need(type(route) is str and route.startswith(prefix), "ROUTE_SCOPE_DENIED")
        result = get(route)
        need(type(result) is dict, "REMOTE_OBJECT_UNAVAILABLE")
        return result

    main = read(prefix + "branches/main")
    need(main.get("protected") is True and
         main.get("commit", {}).get("sha") == target, "PROTECTED_MAIN_DRIFT")
    ahead = read(prefix + "compare/" + OWNER_SOURCE + "..." + target + "?per_page=1")
    need(ahead.get("status") == "ahead" and type(ahead.get("behind_by")) is int
         and ahead["behind_by"] == 0 and
         type(ahead.get("ahead_by")) is int and ahead["ahead_by"] >= 39 and
         ahead.get("merge_base_commit", {}).get("sha") == OWNER_SOURCE,
         "OWNER_ANCESTRY_DRIFT")
    repair = read(prefix + "git/commits/" + MERGED_REPAIR)
    need(repair.get("sha") == MERGED_REPAIR
         and type(repair.get("tree")) is dict and
         _sha(repair["tree"].get("sha")), "MERGED_REPAIR_NOT_VERIFIED")
    repair_ancestry = read(prefix + "compare/" + MERGED_REPAIR + "..." + target + "?per_page=1")
    need(repair_ancestry.get("status") in ("ahead", "identical") and
         repair_ancestry.get("behind_by") == 0 and
         repair_ancestry.get("merge_base_commit", {}).get("sha") == MERGED_REPAIR,
         "REPAIR_NOT_IN_PROTECTED_TARGET")
    # Fix blobs are anchored at their immutable merge, not at a later
    # successor that must update runtime source-transition guards itself.
    for path, expected in (
        ("f139/local_controller.py", REPAIR_CONTROLLER_BLOB),
        ("f139/test_nci04_native_successor_catalog.py", REPAIR_NEGATIVE_TEST_BLOB),
    ):
        item = read(prefix + "contents/" + path + "?ref=" + MERGED_REPAIR)
        need(item.get("type") == "file" and item.get("sha") == expected,
             "REPAIR_SOURCE_BLOB_DRIFT")

    owner = read(prefix + "issues/807")
    need(owner.get("state") == "open" and
         owner.get("user", {}).get("login") == "spoonman136668-ai",
         "ORIGINAL_OWNER_ISSUE_DRIFT")
    try:
        policy = json.loads(owner.get("body"))
    except (TypeError, ValueError) as exc:
        raise V41ReadOnlyDenied("F139_V41_READONLY_OWNER_POLICY_JSON") from exc
    need(type(policy) is dict and
         policy.get("schema") == "forge.f139.native-autonomy-feed-owner-policy.v1"
         and policy.get("enabled") is True and
         policy.get("source_sha") == OWNER_SOURCE and
         policy.get("lanes") == ["Wingless", "Yggdrasil"] and
         policy.get("max_issue_creations_per_cycle") == 2 and
         policy.get("require_owner_authored_pr") is True and
         policy.get("require_single_head_commit_delta") is True and
         policy.get("require_single_allowed_source_file") is True and
         policy.get("scientific_first_use") is False and
         policy.get("new_controller") is False and
         policy.get("new_scheduler") is False and
         policy.get("new_queue") is False and
         policy.get("paid_model_calls") == 0 and
         policy.get("accepted_ref_mutations") == 0,
         "ORIGINAL_TWO_LANE_POLICY_DRIFT")
    release = read(prefix + "branches/f139-owner-release-" + OWNER_SOURCE)
    need(release.get("protected") is True and
         release.get("commit", {}).get("sha") == OWNER_SOURCE,
         "ORIGINAL_IMMUTABLE_RELEASE_DRIFT")
    seen = set()
    counts = []
    for page in (1, 2, 3):
        # 200 exact live eligible issues: page 3 is the empty sentinel.
        rows = get(prefix + "issues?state=open&labels=" + ELIGIBLE_LABEL +
                   "&per_page=100&page=" + str(page))
        need(type(rows) is list, "ELIGIBLE_ISSUE_PAGE_MISSING")
        counts.append(len(rows))
        need(len(rows) == (0 if page == 3 else 100), "ELIGIBLE_CATALOG_DRIFT")
        for issue in rows:
            need(type(issue) is dict and type(issue.get("number")) is int
                 and issue["number"] > 0 and
                 type(issue.get("id")) is int and issue["id"] > 0
                 and issue["id"] not in seen and issue.get("state") == "open"
                 and not issue.get("pull_request")
                 and type(issue.get("labels")) is list
                 and ELIGIBLE_LABEL in [v.get("name") for v in issue["labels"] if type(v) is dict],
                 "ELIGIBLE_ISSUE_IDENTITY_OR_DUPLICATE")
            seen.add(issue["id"])
    final = read(prefix + "branches/main")
    final_owner = read(prefix + "issues/807")
    need(final.get("protected") is True and final.get("commit", {}).get("sha") == target
         and final_owner.get("body") == owner["body"],
         "POSTREAD_SOURCE_OR_POLICY_DRIFT")
    return dict(schema=SCHEMA, target_source_sha=target, original_source_sha=OWNER_SOURCE,
                original_release_verified=True, merged_catalog_repair_verified=True,
                issues_per_page=counts, unique_eligible_issues=len(seen),
                provider_reads_only=True, remote_writes=0,
                source_transition_authorized=False, scientific_first_use=False,
                hybrid_admission=False)


def original_ledger_preflight(db):
    """Cold original-owner ledger proof; never use fixtures as acceptance."""
    need(type(db) is Database and getattr(db, "_readonly_opened", False) is True
         and db.conn.execute("PRAGMA query_only").fetchone()[0] == 1
         and SingleOwner.held(db.filename.with_suffix(".lock")),
         "ORIGINAL_READONLY_MUTEX_REQUIRED")
    db.verify()
    before = db.meta().copy()
    need(before["source_sha"] == OWNER_SOURCE and before["enabled"] == 1
         and before["legacy_suspended"] == 1 and before["head_seq"] >= OBSERVED_SEQ
         and db.ready() is None and not db.actives()
         and verify_native_activation(db), "ORIGINAL_OWNER_NOT_IDLE_OR_AUTHENTIC")
    frozen = db.conn.execute("SELECT sha FROM events WHERE seq=?", (OBSERVED_SEQ,)).fetchone()
    need(frozen is not None and frozen["sha"] == OBSERVED_HEAD,
         "OBSERVED_LEDGER_PREFIX_DRIFT")
    transitions = [dict(row) for row in db.conn.execute(
        "SELECT seq,sha,payload FROM events WHERE kind='SOURCE_TRANSITION_ADMITTED' ORDER BY seq")]
    need(bool(transitions) and
         json.loads(transitions[-1]["payload"]).get("schema") == v40.SCHEMA,
         "UNIQUE_V40_PREDECESSOR_REQUIRED")
    seals = [row for row in transitions
             if json.loads(row["payload"]).get("schema") == v40.SCHEMA]
    need(len(seals) == 1 and
         json.loads(seals[0]["payload"]).get("to_source_sha") == OWNER_SOURCE and
         json.loads(seals[0]["payload"]).get("from_source_sha") == v40.FROM_V39 and
         json.loads(seals[0]["payload"]).get("qualified_worker_blob") ==
             v40.QUALIFIED_WORKER_BLOB, "V40_PREDECESSOR_SEAL_DRIFT")
    tasks = [dict(row) for row in db.conn.execute(
        "SELECT ticket,stage,source_sha,run_id,evidence_sha,evidence_dir "
        "FROM tasks ORDER BY ticket")]
    counts = {stage: sum(t["stage"] == stage for t in tasks)
              for stage in ("VERIFIED", "QUARANTINED")}
    need(len(tasks) == sum(counts.values()) and
         counts["VERIFIED"] >= 153 and counts["QUARANTINED"] == 56,
         "SPENT_ORIGINAL_TASK_HISTORY_DRIFT")
    attempted, authenticated = partial._publication_prefix(db, before["head_seq"] + 1)
    need(len(attempted) >= 168 and len(authenticated) >= 166
         and set(attempted) - set(authenticated) ==
             {partial.IDENTITY, ref_only.IDENTITY},
         "TWO_EXACT_CONSUMED_NEGATIVES_REQUIRED")
    need(partial.validate_original(db, partial.SEQ + 1) == partial.custody_packet()
         and ref_only.validate_original(db, ref_only.SEQ + 1) == ref_only.custody_packet(),
         "NEGATIVE_PREFIX_CUSTODY_DRIFT")
    reasoner = db.conn.execute(
        "SELECT COUNT(*) AS n FROM events WHERE kind='FREE_REASONER_ATTEMPTED'").fetchone()["n"]
    need(reasoner == 8 and db.meta() == before, "SPENT_CALLS_OR_HEAD_DRIFT")
    return dict(schema=SCHEMA, source_sha=OWNER_SOURCE,
                original_head_seq=before["head_seq"],
                original_head_sha256=before["head_hash"],
                observed_frozen_prefix_sha256=OBSERVED_HEAD,
                v40_transition_sha256=seals[0]["sha"],
                terminal_tasks_sha256=digest(canonical(tasks)),
                verified_historical_tasks=counts["VERIFIED"],
                quarantined_historical_tasks=counts["QUARANTINED"],
                attempted_model_publications=len(attempted),
                authenticated_model_publications=len(authenticated),
                unrepeatable_failed_attempts=2,
                spent_free_reasoner_calls=reasoner,
                owner_mutations=0, new_dispatches=0,
                source_transition_authorized=False, live_migration_enabled=False,
                scientific_first_use=False, hybrid_admission=False)
