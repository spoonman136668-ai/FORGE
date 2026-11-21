"""Fresh lifecycle in the existing SQLite ledger, not a second controller.

The release event must be installed by the separately authenticated native
Windows owner route. No release writer, scheduler or provider POST is defined
here. A committed START_RISK is permanently consumed even if POST acknowledgment
is lost. Only the original controller may call these primitives under its lock.
"""
from __future__ import annotations

import base64
import hmac
import hashlib
import json
from pathlib import Path

from f139.nci04_native_contract import canonical, digest, parse_intent
from f139.nci04_owner_issue import NativeIssue
from f139.nci04_fresh_native_intake import KIND, audit_admission_pair
from f139.nci04_fresh_worker_protocol import (
    SOURCE, TARGET, TARGET_TREE, FRESH_RUN, SHA40, SHA64, OS,
    make_claim, authenticate_provider, qualify_provider_terminal,
)
from f139.nci04_original_v3_terminal import inner_zip
from f139.local_controller import (
    Database, SingleOwner, LIMIT_PER_DAY, parse_time, store_evidence,
)

RELEASE_KIND = "FRESH_WORKER_RELEASE_AUTHENTICATED"
CUSTODY_KIND = "FRESH_WORKER_PROVIDER_CUSTODY"
RELEASE_SCHEMA = "forge.f139.fresh-worker-owner-release.v1"
CUSTODY_SCHEMA = "forge.f139.fresh-worker-provider-custody.v1"
RELEASE_DOMAIN = b"FORGE-F139-FRESH-WORKER-OWNER-RELEASE-V1\0"
RELEASE_FIELDS = frozenset({
    "schema", "admission_source_sha", "activation_run_id", "initial_ready_sha256",
    "worker_release_sha", "worker_release_tree", "owner_run_id", "owner_comment_id",
    "original_rebind_run_id", "task_name", "development_only",
    "scientific_first_use", "model_continuation_authorized", "paid_model_calls",
    "owner_signature",
})


class FreshLifecycleDenied(ValueError):
    pass


def need(ok, reason):
    if not ok:
        raise FreshLifecycleDenied("F139_FRESH_LIFECYCLE_" + reason)


def sha(pattern, value):
    return type(value) is str and pattern.fullmatch(value) is not None


def pos(value):
    return type(value) is int and 0 < value < 2**63


def read_event(row):
    return json.loads(row["payload"])


def check_release(release, initial_head, activation):
    need(type(release) is dict and set(release) == RELEASE_FIELDS
         and release["schema"] == RELEASE_SCHEMA
         and release["admission_source_sha"] == activation["source_sha"] == SOURCE
         and release["activation_run_id"] == activation["owner_run_id"] == FRESH_RUN
         and release["initial_ready_sha256"] == initial_head
         and sha(SHA64, initial_head)
         and sha(SHA40, release["worker_release_sha"])
         and release["worker_release_sha"] != SOURCE
         and sha(SHA40, release["worker_release_tree"])
         and pos(release["owner_run_id"]) and pos(release["owner_comment_id"])
         and release["original_rebind_run_id"] == 44852932511
         and release["task_name"] == "FORGE-F139-UnifiedController"
         and release["development_only"] is True
         and release["scientific_first_use"] is False
         and release["model_continuation_authorized"] is False
         and type(release["paid_model_calls"]) is int
         and release["paid_model_calls"] == 0
         and sha(SHA64, release["owner_signature"]),
         "RELEASE_RECORD_INVALID")


def verify_release_signature(release, key):
    need(type(key) is str and 32 <= len(key) <= 4096, "OWNER_KEY_INVALID")
    unsigned = {k: v for k, v in release.items() if k != "owner_signature"}
    sig = hmac.new(key.encode("utf-8"), RELEASE_DOMAIN + canonical(unsigned),
                   hashlib.sha256).hexdigest()
    need(hmac.compare_digest(sig, release["owner_signature"]),
         "RELEASE_SIGNATURE_INVALID")


def frozen_issue(record):
    raw = base64.b64decode(record["native_intent_base64"], validate=True)
    c = parse_intent(raw, protected_main=SOURCE, target_commit=TARGET,
                     target_tree_sha=TARGET_TREE)
    need(record["source_sha"] == SOURCE and record["native_target_tree"] == TARGET_TREE
         and record["ticket"] == "f139-nci04-i" + str(record["issue_number"])
         + "-" + SOURCE[:12] + "-" + c.intent_sha256[:8],
         "FROZEN_ADMISSION_SOURCE_INVALID")
    return NativeIssue(record["issue_number"], record["issue_id"], record["ticket"],
                       record["lane"], SOURCE, record["issue_body_sha256"],
                       record["native_intent_sha256"], record["qualification_key"],
                       raw, c)


def committed_claim(entry, release):
    issue = frozen_issue(entry["record"])
    a, c = entry["admission"], entry["claim"]
    return make_claim(issue, release_sha=release["worker_release_sha"],
                      release_tree=release["worker_release_tree"],
                      admission_seq=a["seq"], admission_sha=a["sha"],
                      claim_seq=c["seq"], claim_sha=c["sha"]), issue.intent_raw


def audit_archives(db, entry, release, custody):
    from f139.nci04_fresh_worker_protocol import admission_for_run
    claim, raw = committed_claim(entry, release)
    ticket = entry["record"]["ticket"]
    need(type(custody) is dict and set(custody) == {
        "schema", "ticket", "run_id", "claim_sha256", "worker_release_sha",
        "evidence_dir", "evidence_manifest_sha256", "authorize_job_id",
        "provider_platforms", "development_qualified", "scientific_first_use",
        "paid_model_calls", "accepted_ref_mutations",
    } and custody["schema"] == CUSTODY_SCHEMA and custody["ticket"] == ticket
         and pos(custody["run_id"]) and pos(custody["authorize_job_id"])
         and custody["claim_sha256"] == digest(canonical(claim))
         and custody["worker_release_sha"] == release["worker_release_sha"]
         and custody["development_qualified"] is True
         and custody["scientific_first_use"] is False
         and type(custody["paid_model_calls"]) is int and custody["paid_model_calls"] == 0
         and type(custody["accepted_ref_mutations"]) is int
         and custody["accepted_ref_mutations"] == 0
         and type(custody["provider_platforms"]) is dict
         and set(custody["provider_platforms"]) == set(OS),
         "TERMINAL_CUSTODY_RECORD_INVALID")
    expected = db.filename.parent / "evidence" / ticket / str(custody["run_id"])
    folder = Path(custody["evidence_dir"])
    need(folder.resolve() == expected.resolve() and folder.is_dir()
         and not folder.is_symlink() and not folder.parent.is_symlink()
         and not folder.parent.parent.is_symlink()
         and not any(getattr(p, "is_junction", lambda: False)()
                     for p in (folder, folder.parent, folder.parent.parent))
         and {p.name for p in folder.iterdir()} ==
             {"ubuntu-latest.zip", "windows-latest.zip", "manifest.json"},
         "COLD_EVIDENCE_PATH_OR_INVENTORY_INVALID")
    manifest = {"schema": "forge.f139.windows-evidence-manifest.v1",
                "ticket": ticket, "run_id": custody["run_id"], "sha256": {},
                "scientific_originals": 0, "approved_science": False}
    for label in OS:
        proof = custody["provider_platforms"][label]
        need(type(proof) is dict and set(proof) ==
             {"job_id", "artifact_id", "outer_sha256", "receipt_sha256", "report_sha256"}
             and pos(proof["job_id"]) and pos(proof["artifact_id"])
             and all(sha(SHA64, proof[k]) for k in
                     ("outer_sha256", "receipt_sha256", "report_sha256")),
             "COLD_PROVIDER_PROOF_INVALID")
        path = folder / (label + ".zip")
        need(path.is_file() and not path.is_symlink()
             and 0 < path.stat().st_size < 2_000_000, "COLD_PROVIDER_ZIP_MISSING")
        data = path.read_bytes()
        need(digest(data) == proof["outer_sha256"], "COLD_PROVIDER_ZIP_DRIFT")
        admission = admission_for_run(claim, raw, commitment=custody["claim_sha256"],
                                      run_id=custody["run_id"], oslabel=label)
        actual = inner_zip(data, {"size_in_bytes": len(data),
                           "digest": "sha256:" + proof["outer_sha256"], "expired": False},
                           admission, fresh=True)
        need(actual == {k: proof[k] for k in ("receipt_sha256", "report_sha256")},
             "COLD_SIGNED_RECEIPT_DRIFT")
        manifest["sha256"][label] = proof["outer_sha256"]
    path = folder / "manifest.json"
    need(path.is_file() and not path.is_symlink()
         and path.stat().st_size <= 64000
         and path.read_bytes() == canonical(manifest)
         and digest(canonical(manifest)) == custody["evidence_manifest_sha256"],
         "COLD_EVIDENCE_MANIFEST_DRIFT")


def audit_execution_tail(db, activation, rows):
    """All events after activation must follow the one-lane finite state machine.

    This also independently binds mutable task rows and cold evidence to the
    append-only history. No positive runtime authority follows from this audit.
    """
    need(len(rows) >= 3 and rows[0]["seq"] == 3 and rows[1]["seq"] == 4
         and rows[2]["seq"] == 5 and rows[2]["kind"] == RELEASE_KIND,
         "RELEASE_MUST_FOLLOW_INITIAL_INTAKE")
    first = audit_admission_pair(db, activation, rows[:2])
    need(first["issue_number"] == 1849, "INITIAL_TICKET_REQUIRED")
    release = read_event(rows[2])
    check_release(release, rows[1]["sha"], activation)
    entries = [{"record": first, "admission": rows[0], "stage": "READY",
                "claim": None, "started_at": None, "custody": None}]
    seen_numbers = {first["issue_number"]}
    seen_ids = {first["issue_id"]}
    seen_after = {first["after_sha256"]}
    seen_intents = {first["native_intent_sha256"]}
    run_ids = set()
    starts = []
    i = 3
    while i < len(rows):
        e = entries[-1]
        row = rows[i]
        kind = row["kind"]
        doc = read_event(row)
        ticket = e["record"]["ticket"]
        if kind == "BEFORE_DISPATCH_INTENT":
            need(e["stage"] == "READY" and e["claim"] is None
                 and type(doc) is dict and set(doc) == {"ticket", "started_at", "starts"}
                 and doc["ticket"] == ticket and pos(doc["starts"]),
                 "DUPLICATE_OR_INVALID_CLAIM")
            t = parse_time(doc["started_at"])
            need(not starts or t >= starts[-1], "CLOCK_MOVED_BACKWARD")
            need(sum(0 <= (t - earlier).total_seconds() < 600 for earlier in starts) < 2,
                 "ROLLING_START_BUDGET_DRIFT")
            need(sum(s.date() == t.date() for s in starts) + 1 == doc["starts"]
                 and doc["starts"] <= LIMIT_PER_DAY,
                 "START_COUNTER_OR_BUDGET_DRIFT")
            starts.append(t)
            e.update(stage="START_RISK", claim=row, started_at=doc["started_at"])
            committed_claim(e, release)
        elif kind == "DISPATCH_POST_RETURNED":
            need(e["stage"] == "START_RISK" and doc == {"ticket": ticket},
                 "POST_ACK_WITHOUT_UNIQUE_CLAIM")
            e["stage"] = "WAIT_PROVIDER"
        elif kind == "PROVIDER_VERIFIED_TERMINAL":
            need(e["stage"] in ("START_RISK", "WAIT_PROVIDER")
                 and i + 1 < len(rows) and rows[i + 1]["kind"] == CUSTODY_KIND,
                 "TERMINAL_WITHOUT_CUSTODY")
            custody = read_event(rows[i + 1])
            audit_archives(db, e, release, custody)
            need(doc == {"ticket": ticket, "run_id": custody["run_id"],
                         "evidence_sha": custody["evidence_manifest_sha256"]}
                 and custody["run_id"] not in run_ids,
                 "TERMINAL_IDENTITY_OR_RUN_REUSE")
            run_ids.add(custody["run_id"])
            e.update(stage="VERIFIED", custody=custody)
            i += 1
        elif kind == KIND:
            need(e["stage"] == "VERIFIED" and i + 1 < len(rows),
                 "SUCCESSOR_WITHOUT_POSITIVE_TERMINAL")
            r = audit_admission_pair(db, activation, rows[i:i + 2])
            need(r["issue_number"] > max(seen_numbers)
                 and r["issue_id"] not in seen_ids
                 and r["after_sha256"] not in seen_after
                 and r["native_intent_sha256"] not in seen_intents,
                 "SUCCESSOR_REUSES_CONSUMED_IDENTITY")
            frozen_issue(r)
            seen_numbers.add(r["issue_number"])
            seen_ids.add(r["issue_id"])
            seen_after.add(r["after_sha256"])
            seen_intents.add(r["native_intent_sha256"])
            entries.append({"record": r, "admission": row, "stage": "READY",
                            "claim": None, "started_at": None, "custody": None})
            i += 1
        else:
            raise FreshLifecycleDenied("F139_FRESH_LIFECYCLE_UNKNOWN_EVENT")
        i += 1
    tasks = {r["ticket"]: dict(r) for r in db.conn.execute("SELECT * FROM tasks")}
    need(set(tasks) == {e["record"]["ticket"] for e in entries},
         "COLD_TASK_INVENTORY_DRIFT")
    for e in entries:
        r = e["record"]
        task = tasks[r["ticket"]]
        c = e["custody"]
        need(task["source_sha"] == r["source_sha"] == SOURCE
             and task["lane"] == "Yggdrasil" and task["stage"] == e["stage"]
             and task["manifest_sha"] == r["manifest_sha256"]
             and task["started_at"] == e["started_at"]
             and task["run_id"] == (c["run_id"] if c else None)
             and task["evidence_dir"] == (c["evidence_dir"] if c else None)
             and task["evidence_sha"] == (c["evidence_manifest_sha256"] if c else None)
             and task["quarantine_reason"] is None
             and (task["completed_at"] is not None) == (c is not None),
             "COLD_TASK_ROW_DRIFT")
        if c:
            need(parse_time(task["completed_at"]) >= parse_time(task["started_at"]),
                 "TERMINAL_CLOCK_DRIFT")
    meta = db.meta()
    need(meta["starts"] == (sum(s.date() == starts[-1].date() for s in starts)
                             if starts else 0)
         and (not starts or meta["day"] == starts[-1].date().isoformat()),
         "COLD_META_COUNTER_DRIFT")
    return release, entries


def read_lifecycle(db, key):
    from f139.nci04_fresh_native_activation import audit_fresh_native_activation
    need(type(db) is Database and SingleOwner.held(db.filename.with_suffix(".lock")),
         "EXISTING_OWNER_LOCK_REQUIRED")
    db.verify()
    activation = audit_fresh_native_activation(db)
    need(activation is not None and db.meta()["head_seq"] >= 5,
         "NATIVE_RELEASE_NOT_INSTALLED")
    rows = list(db.conn.execute("SELECT * FROM events WHERE seq>=3 ORDER BY seq"))
    release, entries = audit_execution_tail(db, activation, rows)
    verify_release_signature(release, key)
    return release, entries


def reserve_claim(db, api, key, *, now):
    """Reserve one real claim; never POST or redo a spent START_RISK."""
    release, entries = read_lifecycle(db, key)
    entry = entries[-1]
    need(entry["stage"] == "READY", "CLAIM_ALREADY_SPENT")
    issue = frozen_issue(entry["record"])
    # Calculate the exact next event, not a synthetic sequence or digest.
    # This prediction is NEVER signed or sent; use it only for GET preflight.
    parse_time(now)
    m = db.meta()
    starts = (m["starts"] if m["day"] == now[:10] else 0) + 1
    event = {"seq": m["head_seq"] + 1, "prior_sha": m["head_hash"],
             "kind": "BEFORE_DISPATCH_INTENT",
             "payload": {"ticket": issue.ticket, "started_at": now, "starts": starts}}
    preview = make_claim(issue, release_sha=release["worker_release_sha"],
                         release_tree=release["worker_release_tree"],
                         admission_seq=entry["admission"]["seq"],
                         admission_sha=entry["admission"]["sha"],
                         claim_seq=event["seq"], claim_sha=digest(canonical(event)))
    authenticate_provider(preview, issue.intent_raw, api.get)
    db.claim(issue.ticket, now)
    release, entries = read_lifecycle(db, key)
    actual, raw = committed_claim(entries[-1], release)
    need(actual == preview, "COMMITTED_CLAIM_DIFFERS_FROM_PREFLIGHT")
    return actual, raw


def acknowledge_post(db, key, *, ticket):
    """Only call after the one original POST returned. No retry on failure."""
    _, entries = read_lifecycle(db, key)
    need(entries[-1]["stage"] == "START_RISK"
         and entries[-1]["record"]["ticket"] == ticket,
         "UNMATCHED_POST_ACK")
    db.dispatch_observed(ticket)
    db.verify()


def settle_provider(db, api, key, *, run_id, now):
    """GET-only settlement, including recovery after a lost POST acknowledgement."""
    release, entries = read_lifecycle(db, key)
    e = entries[-1]
    need(e["stage"] in ("START_RISK", "WAIT_PROVIDER"),
         "NO_UNSETTLED_CLAIM")
    claim, raw = committed_claim(e, release)
    # Lookup exact ticket/ref history before accepting the provider run.
    run = api.candidates_for_source(claim["ticket"], e["started_at"],
                                    release["worker_release_sha"])
    need(type(run) is dict and run.get("id") == run_id,
         "PROVIDER_RUN_NOT_UNIQUE_OR_NOT_VISIBLE")
    proof, archives, auth_job = qualify_provider_terminal(
        api, key, claim, raw, run_id=run_id, started_at=e["started_at"])
    directory, manifest = store_evidence(db.filename.parent, claim["ticket"], run_id,
                                         archives)
    doc = {"schema": CUSTODY_SCHEMA, "ticket": claim["ticket"], "run_id": run_id,
           "claim_sha256": digest(canonical(claim)),
           "worker_release_sha": release["worker_release_sha"],
           "evidence_dir": directory, "evidence_manifest_sha256": manifest,
           "authorize_job_id": auth_job, "provider_platforms": proof,
           "development_qualified": True, "scientific_first_use": False,
           "paid_model_calls": 0, "accepted_ref_mutations": 0}
    with db.transaction():
        db.verify()
        need(parse_time(now) >= parse_time(e["started_at"]), "TERMINAL_CLOCK_DRIFT")
        q = db.conn.execute("UPDATE tasks SET stage='VERIFIED',run_id=?,"
                            "evidence_dir=?,evidence_sha=?,completed_at=? "
                            "WHERE ticket=? AND stage=? AND run_id IS NULL",
                            (run_id, directory, manifest, now, claim["ticket"], e["stage"]))
        need(q.rowcount == 1, "TERMINAL_CONCURRENT_OR_ALREADY_RECORDED")
        db.event("PROVIDER_VERIFIED_TERMINAL",
                 {"ticket": claim["ticket"], "run_id": run_id, "evidence_sha": manifest})
        db.event(CUSTODY_KIND, doc)
        db.verify()
    return doc
