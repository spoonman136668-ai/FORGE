"""Fresh lifecycle in the existing SQLite ledger, not a second controller.

The release event must be installed by the separately authenticated native
Windows owner route. The existing controller calls this route under its lock.
No scheduler or second controller is defined here. A committed START_RISK is permanently consumed even if POST acknowledgment
is lost. Only the original controller may call these primitives under its lock.
"""
from __future__ import annotations

import base64
import hmac
import hashlib
import json
import os
import shutil
import subprocess
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
    canonical as ledger_canonical,
)

RELEASE_KIND = "FRESH_WORKER_RELEASE_AUTHENTICATED"
CUSTODY_KIND = "FRESH_WORKER_PROVIDER_CUSTODY"
NEGATIVE_KIND = "FRESH_WORKER_PROVIDER_NEGATIVE"
PUBLISH_KIND = "FRESH_SUCCESSOR_PUBLICATION_ATTEMPTED"
# V2 is strictly additional DEV grammar admission; previous V1 receipts are
# immutable and remain parseable by the cold owner chain.
PUBLISH_SCHEMA_STRUCTURED = "forge.f139.fresh-owner-structured-publication-attempt.v2"
PUBLISH_STRUCTURED_RECIPES = frozenset(
    [f"support-{n}-v2" for n in (2, 4, 8, 16)] +
    [f"symmetric-prior-{n}-v2" for n in (2, 4, 8, 16)]
)
PUBLISH_SCHEMA_HYPOTHESIS_V3 = "forge.f139.fresh-owner-hypothesis-publication-attempt.v3"
PUBLISH_HYPOTHESIS_V3_RECIPES = frozenset(
    f"ygg-{est}-{sup}-{tie}-v1"
    for est in ("jeffreys", "asymmetric_loss", "se_margin", "lcb_15")
    for sup in ("min1", "min4", "min8", "balanced2x")
    for tie in ("abstain", "least_observed")
)

PUBLISH_SCHEMA = "forge.f139.fresh-owner-publication-attempt.v1"
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
         and path.read_bytes() == ledger_canonical(manifest)
         and digest(ledger_canonical(manifest)) == custody["evidence_manifest_sha256"],
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
            need(e["stage"] == "START_RISK" and not e.get("negative") and doc == {"ticket": ticket},
                 "POST_ACK_WITHOUT_UNIQUE_CLAIM")
            e["stage"] = "WAIT_PROVIDER"
        elif kind == NEGATIVE_KIND:
            need(e["stage"] in ("START_RISK", "WAIT_PROVIDER") and not e.get("negative"),
                 "NEGATIVE_WITHOUT_UNIQUE_CONSUMED_CLAIM")
            claim, _ = committed_claim(e, release)
            audit_negative_record(doc, claim)
            need(doc["run_id"] not in run_ids, "NEGATIVE_RUN_REUSED")
            run_ids.add(doc["run_id"])
            e["negative"] = doc
        elif kind == "PROVIDER_VERIFIED_TERMINAL":
            need(e["stage"] in ("START_RISK", "WAIT_PROVIDER") and not e.get("negative")
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
        elif kind == PUBLISH_KIND:
            need(e["stage"] == "VERIFIED"
                 and e.get("publication_attempt") is None
                 and type(doc) is dict
                 and set(doc) == {
                     "schema", "ticket", "source_sha", "target_sha", "recipe",
                     "mechanism_sha256", "after_sha256", "intent_sha256",
                     "issue_body_sha256", "scientific_first_use", "paid_model_calls",
                 }
                 and type(doc["recipe"]) is str
                 and (
                     (doc["schema"] == PUBLISH_SCHEMA
                      and doc["recipe"] in {
                          "least-observed-local-arm-v1", "laplace-local-evidence-v1",
                      })
                     or (doc["schema"] == PUBLISH_SCHEMA_STRUCTURED
                         and doc["recipe"] in PUBLISH_STRUCTURED_RECIPES)
                     or (doc["schema"] == PUBLISH_SCHEMA_HYPOTHESIS_V3
                         and doc["recipe"] in PUBLISH_HYPOTHESIS_V3_RECIPES)
                 )
                 and doc["ticket"] == ticket
                 and doc["source_sha"] == SOURCE and doc["target_sha"] == TARGET
                 and all(sha(SHA64, doc[k]) for k in (
                     "mechanism_sha256", "after_sha256", "intent_sha256",
                     "issue_body_sha256",
                 ))
                 and doc["after_sha256"] not in seen_after
                 and doc["intent_sha256"] not in seen_intents
                 and doc["scientific_first_use"] is False
                 and type(doc["paid_model_calls"]) is int
                 and doc["paid_model_calls"] == 0,
                 "PUBLICATION_ATTEMPT_INVALID_OR_REPLAY")
            e["publication_attempt"] = doc
        elif kind == KIND:
            need(e["stage"] == "VERIFIED" and i + 1 < len(rows),
                 "SUCCESSOR_WITHOUT_POSITIVE_TERMINAL")
            r = audit_admission_pair(db, activation, rows[i:i + 2])
            need(r["issue_number"] > max(seen_numbers)
                 and r["issue_id"] not in seen_ids
                 and r["after_sha256"] not in seen_after
                 and r["native_intent_sha256"] not in seen_intents,
                 "SUCCESSOR_REUSES_CONSUMED_IDENTITY")
            publication = e.get("publication_attempt")
            if publication is not None:
                need(r["after_sha256"] == publication["after_sha256"]
                     and r["native_intent_sha256"] == publication["intent_sha256"]
                     and r["issue_body_sha256"] == publication["issue_body_sha256"],
                     "PUBLISHED_SUCCESSOR_IDENTITY_DRIFT")
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
                         claim_seq=event["seq"], claim_sha=digest(ledger_canonical(event)))
    authenticate_provider(preview, issue.intent_raw, api.native_repo_get)
    db.claim(issue.ticket, now)
    release, entries = read_lifecycle(db, key)
    actual, raw = committed_claim(entries[-1], release)
    need(actual == preview, "COMMITTED_CLAIM_DIFFERS_FROM_PREFLIGHT")
    return actual, raw


def acknowledge_post(db, key, *, ticket):
    """Only call after the one original POST returned. No retry on failure."""
    _, entries = read_lifecycle(db, key)
    need(entries[-1]["stage"] == "START_RISK" and not entries[-1].get("negative")
         and entries[-1]["record"]["ticket"] == ticket,
         "UNMATCHED_POST_ACK")
    db.dispatch_observed(ticket)
    db.verify()


def settle_provider(db, api, key, *, run_id, now):
    """GET-only settlement, including recovery after a lost POST acknowledgement."""
    release, entries = read_lifecycle(db, key)
    e = entries[-1]
    need(e["stage"] in ("START_RISK", "WAIT_PROVIDER") and not e.get("negative"),
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


def admit_next_successor(db, api, key):
    """Admit at most one independently eligible owner issue after a terminal.

    The original immutable epoch/source, research boundary and exclusions
    remain sealed. The current authorized executable release is separate.
    No issue publication, worker POST, accepted-ref change or model access.
    A missing eligible issue is an idle result, never a fabricated successor.
    """
    from f139.nci04_fresh_native_owner_route import _sealed_json
    from f139.nci04_fresh_native_intake import SCHEMA as INTAKE_SCHEMA
    from f139.nci04_fresh_native_activation import audit_fresh_native_activation
    from f139.nci04_fresh_dev_exclusions import candidate_violates_frozen_exclusions
    from f139.nci04_fresh_yggdrasil_boundary import preflight_new_yggdrasil_development_issue
    from f139.nci04_owner_issue import inspect_owner_issue, LABEL, OWNER
    from f139.nci04_fresh_worker_protocol import REPO, PREFIX
    release, entries = read_lifecycle(db, key)
    if entries[-1]["stage"] != "VERIFIED":
        raise FreshLifecycleDenied("F139_FRESH_LIFECYCLE_SUCCESSOR_BEFORE_TERMINAL")
    activation = audit_fresh_native_activation(db)
    root = db.filename.parent
    consumed, consumed_bytes = _sealed_json(root / "consumed-development-identities.json")
    boundary, boundary_bytes = _sealed_json(root / "yggdrasil-research-lineage.json")
    floor, floor_bytes = _sealed_json(root / "remote-issue-cutover-floor.json")
    need(digest(consumed_bytes) == activation["consumed_exclusions_sha256"]
         and digest(boundary_bytes) == activation["yggdrasil_research_boundary_sha256"]
         and digest(floor_bytes) == activation["remote_cutover_receipt_sha256"]
         and floor.get("target_forge_source_sha") == SOURCE
         and floor.get("remote_cutover_issue_number_floor") == activation["remote_issue_number_floor"]
         and floor.get("remote_cutover_issue_provider_verified") is True
         and floor.get("worker_dispatch_authorized") is False,
         "SUCCESSOR_SEALED_PROVENANCE_DRIFT")
    cutoff = parse_time(floor["remote_cutover_issue_created_at"])
    used = [e["record"] for e in entries]
    number_floor = max(r["issue_number"] for r in used)
    seen_numbers, seen_ids = set(), set()
    records = []
    for page in range(1, 34):
        docs = api.get("repos/" + REPO + "/issues?state=open&labels="
                       + LABEL + "&per_page=100&page=" + str(page))
        need(type(docs) is list and len(docs) <= 100, "SUCCESSOR_CATALOG_INVALID")
        if page == 33:
            need(not docs, "SUCCESSOR_CATALOG_TRUNCATED")
            break
        for doc in docs:
            need(type(doc) is dict and pos(doc.get("number")) and pos(doc.get("id"))
                 and doc["number"] not in seen_numbers and doc["id"] not in seen_ids,
                 "SUCCESSOR_CATALOG_IDENTITY_DRIFT")
            seen_numbers.add(doc["number"])
            seen_ids.add(doc["id"])
            if (doc["number"] <= number_floor or "pull_request" in doc
                    or doc.get("user", {}).get("login") != OWNER
                    or doc.get("author_association") != "OWNER"):
                continue
            try:
                body = json.loads(doc.get("body", ""))
            except (ValueError, TypeError):
                continue
            if (type(body) is dict and body.get("source_sha") == SOURCE
                    and body.get("lane") == "Yggdrasil"):
                records.append(doc)
        if len(docs) < 100:
            break
    for doc in sorted(records, key=lambda x: x["number"]):
        route = "repos/" + REPO + "/issues/" + str(doc["number"])
        current = api.get(route)
        need(current.get("id") == doc["id"] and current.get("body") == doc.get("body")
             and current.get("number") == doc["number"]
             and current.get("url") == "https://api.github.com/" + route
             and current.get("repository_url") == "https://api.github.com/repos/" + REPO
             and parse_time(current["created_at"]) >= cutoff,
             "SUCCESSOR_ISSUE_IDENTITY_DRIFT")
        native = inspect_owner_issue(current, protected_main=SOURCE,
                                     authenticated_target_commit=TARGET,
                                     authenticated_target_tree=TARGET_TREE)
        publication = entries[-1].get("publication_attempt")
        if publication is not None and (
                native.candidate.after_sha256 != publication["after_sha256"]
                or native.native_intent_sha256 != publication["intent_sha256"]
                or native.issue_body_sha256 != publication["issue_body_sha256"]):
            # Never switch to an unrelated issue after a consumed POST attempt.
            continue
        if (native.issue_id in {r["issue_id"] for r in used}
                or native.candidate.after_sha256 in {r["after_sha256"] for r in used}
                or native.native_intent_sha256 in {r["native_intent_sha256"] for r in used}
                or candidate_violates_frozen_exclusions(
                    consumed, issue_number=native.number, issue_id=native.issue_id,
                    ticket=native.ticket, lane=native.lane,
                    target_commit=native.candidate.target_commit, path=native.candidate.path,
                    after_sha256=native.candidate.after_sha256,
                    authenticated_remote_issue_floor=activation["remote_issue_number_floor"])):
            continue
        preflight_new_yggdrasil_development_issue(
            native, controller_source_sha=SOURCE, consumed_history=consumed,
            research_boundary=boundary,
            authenticated_remote_issue_floor=activation["remote_issue_number_floor"])
        # GET-only release/target proof: never fabricate a future claim hash.
        # The actual claim is created only after this admission transaction.
        m = db.meta()
        base = "repos/" + REPO
        branch_route = base + "/branches/" + PREFIX + release["worker_release_sha"]
        original_route = base + "/branches/" + PREFIX + SOURCE
        target_route = "repos/spoonman136668-ai/Yggdrasil/branches/main"
        b, old, target = (api.native_repo_get(r) for r in
                          (branch_route, original_route, target_route))
        commit = api.native_repo_get(base + "/git/commits/" + release["worker_release_sha"])
        native_commit = api.native_repo_get(
            "repos/spoonman136668-ai/Yggdrasil/git/commits/" + TARGET)
        need(b.get("protected") is True and b.get("name") == PREFIX + release["worker_release_sha"]
             and b.get("commit", {}).get("sha") == release["worker_release_sha"]
             and old.get("protected") is True and old.get("name") == PREFIX + SOURCE
             and old.get("commit", {}).get("sha") == SOURCE
             and commit.get("sha") == release["worker_release_sha"]
             and commit.get("tree", {}).get("sha") == release["worker_release_tree"]
             and target.get("protected") is True and target.get("name") == "main"
             and target.get("commit", {}).get("sha") == TARGET
             and native_commit.get("sha") == TARGET
             and native_commit.get("tree", {}).get("sha") == TARGET_TREE,
             "SUCCESSOR_RELEASE_OR_TARGET_DRIFT")
        need(api.native_repo_get(branch_route) == b
             and api.native_repo_get(original_route) == old
             and api.native_repo_get(target_route) == target,
             "SUCCESSOR_PROVIDER_READBACK_DRIFT")
        head = db.conn.execute("SELECT sha FROM events WHERE seq=2").fetchone()["sha"]
        record = {
            "schema": INTAKE_SCHEMA, "owner_run_id": activation["owner_run_id"],
            "source_sha": SOURCE, "activation_sha256": head,
            "ticket": native.ticket, "lane": native.lane, "issue_number": native.number,
            "issue_id": native.issue_id, "issue_body_sha256": native.issue_body_sha256,
            "native_intent_sha256": native.native_intent_sha256,
            "qualification_key": native.qualification_key,
            "native_target_commit": native.candidate.target_commit,
            "native_target_tree": native.candidate.target_tree_sha,
            "native_path": native.candidate.path, "before_sha256": native.candidate.before_sha256,
            "after_sha256": native.candidate.after_sha256,
            "native_intent_base64": base64.b64encode(native.intent_raw).decode("ascii"),
            "remote_issue_number_floor": activation["remote_issue_number_floor"],
            "scientific_first_use": False, "paid_model_calls": 0,
            "worker_dispatch_authorized": False, "model_continuation_authorized": False,
        }
        record["manifest_sha256"] = digest(canonical(record))
        with db.transaction():
            db.verify()
            need(db.meta()["head_hash"] == m["head_hash"] and db.ready() is None
                 and not db.actives() and api.get(route) == current,
                 "SUCCESSOR_HEAD_OR_PROVIDER_CHANGED")
            db.event(KIND, record)
            db.conn.execute(
                "INSERT INTO tasks(ticket,lane,source_sha,stage,manifest_sha) VALUES(?,?,?,'READY',?)",
                (native.ticket, native.lane, SOURCE, record["manifest_sha256"]))
            db.event("TASK_INTAKE", {"ticket": native.ticket, "lane": native.lane,
                                     "manifest_sha": record["manifest_sha256"]})
            db.verify()
        return record
    return None


OWNER_WORKFLOW = ".github/workflows/f139-fresh-original-owner-rebind.yml"
OWNER_RELEASE_PREFIX = "F139-FRESH-DEV-WORKER-RELEASE "
OWNER_RELEASE_JOB = "release-existing-fresh-task"


def authenticate_runtime_owner(db, api, release, key):
    """Require the installed original Windows task and completed native release.

    A local signed event, GitHub owner association, test pass, or caller-
    supplied key is insufficient alone. The live SID, actual task, immutable
    checkout, and separately executed original-owner workflow must all agree.
    """
    from f139.nci04_fresh_worker_protocol import REPO, PREFIX
    from f139.local_controller import legacy_windows_task_disabled
    from f139.nci04_autonomy_feed import inspect_policy
    from f139.nci04_v59_owner_forward_readiness import SOURCE as OLD_SOURCE
    need(os.name == "nt" and SingleOwner.held(db.filename.with_suffix(".lock"))
         and not os.environ.get("OPENAI_API_KEY")
         and not os.environ.get("CLOUDFLARE_API_TOKEN"),
         "NATIVE_WINDOWS_OWNER_REQUIRED")
    profile = os.environ.get("LOCALAPPDATA")
    need(bool(profile), "OWNER_PROFILE_MISSING")
    root = Path(profile) / "FORGE-F139"
    expected_db = root / ("f139-fresh-dev-" + str(FRESH_RUN)) / "state.sqlite"
    from f139.nci04_fresh_owner_source_forward import installed_forward_source
    owner_sha, owner_tree = installed_forward_source(db, api, release, key)
    expected_src = root / "release-candidates" / owner_sha
    actual_src = Path(__file__).resolve().parent.parent
    need(db.filename.resolve() == expected_db.resolve()
         and actual_src == expected_src.resolve()
         and not any(p.is_symlink() or getattr(p, "is_junction", lambda: False)()
                     for p in (expected_db, expected_db.parent, expected_src,
                               expected_src.parent, root)),
         "NATIVE_INSTALLED_SOURCE_OR_DB_DRIFT")
    git = shutil.which("git")
    powershell = shutil.which("powershell.exe")
    need(git is not None and powershell is not None, "OWNER_TOOLS_MISSING")

    def git_text(*args):
        p = subprocess.run([git, "-C", str(actual_src), *args],
                           capture_output=True, stdin=subprocess.DEVNULL,
                           timeout=20, check=False)
        need(p.returncode == 0 and len(p.stdout) <= 64000, "OWNER_GIT_READ_FAILED")
        return p.stdout.decode("utf-8").strip()

    need(git_text("rev-parse", "HEAD") == owner_sha
         and git_text("rev-parse", "HEAD^{tree}") == owner_tree
         and git_text("status", "--porcelain", "--untracked-files=all") == ""
         and git_text("remote") == "", "OWNER_INSTALLED_GIT_DRIFT")
    script = r"""
$ErrorActionPreference='Stop'
$task=Get-ScheduledTask -TaskName 'FORGE-F139-UnifiedController' -ErrorAction Stop
$who=[Security.Principal.WindowsIdentity]::GetCurrent()
$sid=''
try{$sid=(New-Object Security.Principal.NTAccount([string]$task.Principal.UserId)).Translate([Security.Principal.SecurityIdentifier]).Value}catch{}
if([string]$task.Principal.UserId -ine $who.Name -and $sid -cne $who.User.Value){exit 41}
if($task.State -ne 'Running' -or $task.Settings.Enabled -ne $true -or @($task.Actions).Count -ne 1 -or @($task.Triggers).Count -ne 3){exit 42}
$a=$task.Actions[0]
if([IO.Path]::GetFileName([string]$a.Execute) -ine 'powershell.exe'){exit 43}
function Arg([string]$name){
  $m=[regex]::Match([string]$a.Arguments,'(?i)(?:^|\s)-'+$name+'\s+"([^"]+)"')
  if(-not $m.Success){throw 'OWNER_TASK_ARG_MISSING'}
  return [IO.Path]::GetFullPath($m.Groups[1].Value)
}
if((Arg 'RepositoryRoot') -ine [IO.Path]::GetFullPath($env:F139_EXPECTED_ROOT) -or
   (Arg 'Database') -ine [IO.Path]::GetFullPath($env:F139_EXPECTED_DB) -or
   (Arg 'File') -ine [IO.Path]::GetFullPath((Join-Path $env:F139_EXPECTED_ROOT 'scripts\Run-FORGE-F139.ps1')) -or
   (Arg 'PythonExe') -ine [IO.Path]::GetFullPath($env:F139_EXPECTED_PYTHON)){exit 44}
$ownerProcesses=@(Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe'" |
  Where-Object {$_.CommandLine -and $_.CommandLine.Contains('f139.local_controller')})
if($ownerProcesses.Count -ne 1 -or [int]$ownerProcesses[0].ProcessId -ne [int]$env:F139_EXPECTED_PID){exit 45}
# Windows Job supervisor starts the Python child directly from the scheduled wrapper.
$parent=Get-CimInstance Win32_Process -Filter ('ProcessId='+[int]$ownerProcesses[0].ParentProcessId)
if($null -eq $parent -or $parent.Name -ine 'powershell.exe' -or
   -not $parent.CommandLine -or -not $parent.CommandLine.Contains('Run-FORGE-F139.ps1') -or
   -not $parent.CommandLine.Contains($env:F139_EXPECTED_ROOT) -or
   -not $parent.CommandLine.Contains($env:F139_EXPECTED_DB)){exit 46}
Write-Output 'F139_FRESH_RUNNING_ORIGINAL_OWNER=PASS'
"""
    import sys
    env = dict(os.environ, F139_EXPECTED_ROOT=str(actual_src),
               F139_EXPECTED_DB=str(expected_db.resolve()),
               F139_EXPECTED_PYTHON=str(Path(sys.executable).resolve()),
               F139_EXPECTED_PID=str(os.getpid()))
    # No need for the child PowerShell read-only verifier to inherit the key.
    env.pop("F139_WORKER_HMAC_KEY", None)
    p = subprocess.run([powershell, "-NoProfile", "-NonInteractive", "-Command", script],
                       env=env, capture_output=True, stdin=subprocess.DEVNULL,
                       timeout=25, check=False)
    need(p.returncode == 0 and p.stdout.strip() == b"F139_FRESH_RUNNING_ORIGINAL_OWNER=PASS",
         "LIVE_ORIGINAL_TASK_OR_SID_DRIFT")
    legacy_windows_task_disabled()
    need(api.legacy_dispatchers_disabled() is True, "LEGACY_DISPATCHERS_ACTIVE")
    root_route = "repos/" + REPO
    policy = inspect_policy(api.get(root_route + "/issues/807"), OLD_SOURCE)
    need(policy["enabled"] is True and "Yggdrasil" in policy["lanes"],
         "OWNER_POLICY_DISABLED")
    comment_route = root_route + "/issues/comments/" + str(release["owner_comment_id"])
    comment = api.get(comment_route)
    need(comment.get("id") == release["owner_comment_id"]
         and comment.get("issue_url") == "https://api.github.com/" + root_route + "/issues/1830"
         and comment.get("user", {}).get("login") == "spoonman136668-ai"
         and comment.get("author_association") == "OWNER"
         and comment.get("body") == OWNER_RELEASE_PREFIX + release["worker_release_sha"]
             + " " + str(FRESH_RUN),
         "NATIVE_RELEASE_OWNER_COMMENT_DRIFT")
    run_route = root_route + "/actions/runs/" + str(release["owner_run_id"])
    run = api.get(run_route)
    need(run.get("id") == release["owner_run_id"]
         and run.get("event") == "issue_comment"
         and run.get("path") == OWNER_WORKFLOW
         and run.get("head_sha") == release["worker_release_sha"]
         and run.get("run_attempt") == 1
         and run.get("status") == "completed" and run.get("conclusion") == "success"
         and run.get("actor", {}).get("login") == "spoonman136668-ai"
         and run.get("repository", {}).get("full_name") == REPO
         and parse_time(run["created_at"]) >= parse_time(comment["created_at"]),
         "NATIVE_RELEASE_WORKFLOW_NOT_COMPLETED")
    jobs = api.get(run_route + "/jobs?per_page=100")
    rows = jobs.get("jobs")
    need(type(rows) is list and jobs.get("total_count") == len(rows)
         and sum(j.get("name") == OWNER_RELEASE_JOB and j.get("status") == "completed"
                 and j.get("runner_name") == "FORGE-CODEX-REMOTE"
                 and j.get("conclusion") == "success" for j in rows) == 1
         and all(j.get("name") == OWNER_RELEASE_JOB
                 or (j.get("status") == "completed" and j.get("conclusion") == "skipped")
                 for j in rows), "NATIVE_RELEASE_WINDOWS_JOB_NOT_COMPLETED")
    branch_route = root_route + "/branches/" + PREFIX + release["worker_release_sha"]
    branch = api.get(branch_route)
    commit = api.get(root_route + "/git/commits/" + release["worker_release_sha"])
    need(branch.get("protected") is True
         and branch.get("name") == PREFIX + release["worker_release_sha"]
         and branch.get("commit", {}).get("sha") == release["worker_release_sha"]
         and commit.get("sha") == release["worker_release_sha"]
         and commit.get("tree", {}).get("sha") == release["worker_release_tree"]
         and api.get(run_route) == run and api.get(comment_route) == comment
         and api.get(branch_route) == branch,
         "NATIVE_RELEASE_PROVIDER_DRIFT")



def audit_negative_record(doc, claim):
    need(type(doc) is dict and set(doc) == {
        "schema", "ticket", "run_id", "claim_sha256", "worker_release_sha",
        "conclusion", "jobs", "artifacts", "scientific_first_use",
        "development_qualified", "no_replay",
    } and doc["schema"] == "forge.f139.fresh-worker-provider-negative.v1"
         and doc["ticket"] == claim["ticket"] and pos(doc["run_id"])
         and doc["claim_sha256"] == digest(canonical(claim))
         and doc["worker_release_sha"] == claim["worker_release_sha"]
         and doc["conclusion"] in ("failure", "cancelled", "timed_out", "action_required",
                                  "startup_failure", "stale", "neutral", "skipped")
         and doc["scientific_first_use"] is False
         and doc["development_qualified"] is False and doc["no_replay"] is True
         and type(doc["jobs"]) is list and len(doc["jobs"]) <= 16
         and type(doc["artifacts"]) is list and len(doc["artifacts"]) <= 2,
         "NEGATIVE_PROVIDER_RECORD_INVALID")
    need(all(type(j) is dict and set(j) == {"id", "name", "conclusion"}
             and pos(j["id"]) and type(j["name"]) is str and len(j["name"]) <= 128
             and j["conclusion"] in ("success", "failure", "skipped", "cancelled",
                                     "timed_out", "action_required", "startup_failure", "neutral", "stale")
             for j in doc["jobs"])
         and len({j["id"] for j in doc["jobs"]}) == len(doc["jobs"])
         and all(type(a) is dict and set(a) == {"id", "name", "digest", "expired"}
                 and pos(a["id"]) and a["name"] in {
                     "forge-f139-fresh-native-receipt-" + label for label in OS}
                 and type(a["expired"]) is bool
                 and type(a["digest"]) is str and a["digest"].startswith("sha256:")
                 and sha(SHA64, a["digest"][7:]) for a in doc["artifacts"])
         and len({a["id"] for a in doc["artifacts"]}) == len(doc["artifacts"]),
         "NEGATIVE_PROVIDER_METADATA_INVALID")


def retain_negative_observation(db, api, release, entry, run):
    """One durable negative observation; never eligible for successor or replay.

    Preserve GitHub original run/job/artifact identity even if qualification
    failed before two complete signed archives exist. This is not positive
    terminal custody, and no source/worker retry is authorized by it.
    """
    from f139.nci04_fresh_worker_protocol import REPO, WORKFLOW, PREFIX
    claim, raw = committed_claim(entry, release)
    rid = run["id"]
    route = "repos/" + REPO + "/actions/runs/" + str(rid)
    observed = api.get(route)
    need(observed.get("id") == rid and observed.get("head_sha") == claim["worker_release_sha"]
         and observed.get("head_branch") == PREFIX + claim["worker_release_sha"]
         and observed.get("display_title") == observed.get("name") == "F139 " + claim["ticket"]
         and observed.get("event") == "workflow_dispatch" and observed.get("workflow_id") == 388797257
         and observed.get("path") == ".github/workflows/" + WORKFLOW
         and observed.get("repository", {}).get("full_name") == REPO
         and observed.get("actor", {}).get("login") == "spoonman136668-ai"
         and observed.get("run_attempt") == 1 and observed.get("status") == "completed"
         and observed.get("conclusion") == run.get("conclusion")
         and parse_time(observed["created_at"]) >= parse_time(entry["started_at"]),
         "NEGATIVE_PROVIDER_IDENTITY_DRIFT")
    jobs = api.get(route + "/jobs?per_page=100")
    arts = api.get(route + "/artifacts?per_page=100")
    jr, ar = jobs.get("jobs"), arts.get("artifacts")
    need(type(jr) is list and jobs.get("total_count") == len(jr) <= 16
         and all(j.get("status") == "completed" for j in jr)
         and type(ar) is list and arts.get("total_count") == len(ar) <= 2
         and all(a.get("workflow_run", {}).get("id") == rid
                 and a.get("workflow_run", {}).get("head_sha") == claim["worker_release_sha"]
                 for a in ar)
         and api.get(route) == observed,
         "NEGATIVE_PROVIDER_INVENTORY_DRIFT")
    record = {
        "schema": "forge.f139.fresh-worker-provider-negative.v1",
        "ticket": claim["ticket"], "run_id": rid,
        "claim_sha256": digest(canonical(claim)), "worker_release_sha": claim["worker_release_sha"],
        "conclusion": observed["conclusion"],
        "jobs": [{k: j[k] for k in ("id", "name", "conclusion")} for j in jr],
        "artifacts": [{k: a[k] for k in ("id", "name", "digest", "expired")} for a in ar],
        "scientific_first_use": False, "development_qualified": False, "no_replay": True,
    }
    audit_negative_record(record, claim)
    with db.transaction():
        db.verify()
        need(not db.conn.execute("SELECT 1 FROM events WHERE kind=?", (NEGATIVE_KIND,)).fetchone(),
             "NEGATIVE_OBSERVATION_ALREADY_CONSUMED")
        db.event(NEGATIVE_KIND, record)
        db.verify()
    return record


def tick_existing_fresh_owner(db, api, key, *, now):
    """One bounded step in the EXISTING run_once loop, after native release.

    READY -> commit claim -> one POST -> ack. Any ambiguous provider start is
    permanently spent, with subsequent ticks GET-only. Successful terminal
    custody allows a distinct eligible successor on a later tick.
    """
    from f139.local_controller import F139Error
    from f139.nci04_fresh_worker_protocol import dispatch_arguments, REPO, PREFIX, WORKFLOW
    release, entries = read_lifecycle(db, key)
    authenticate_runtime_owner(db, api, release, key)
    e = entries[-1]
    ticket = e["record"]["ticket"]
    result = {"ticket": ticket, "scientific_first_use": False,
              "model_continuation_authorized": False, "paid_model_calls": 0,
              "dispatches": 0, "no_replay": True}
    if e.get("negative"):
        return dict(result, disposition="FRESH_FAILED_PROVIDER_RETAINED_NO_REPLAY",
                    run_id=e["negative"]["run_id"], provider_conclusion=e["negative"]["conclusion"])
    if e["stage"] == "READY":
        claim, raw = reserve_claim(db, api, key, now=now)
        # Re-read provider authorization after the durable claim. Any failure
        # conservatively spends the claim instead of creating another POST.
        authenticate_provider(claim, raw, api.native_repo_get)
        try:
            api.runner(dispatch_arguments(key, claim, raw))
        except (F139Error, OSError, subprocess.TimeoutExpired):
            return dict(result, disposition="FRESH_START_RISK_NO_REPLAY")
        acknowledge_post(db, key, ticket=ticket)
        return dict(result, disposition="FRESH_WAIT_PROVIDER", dispatches=1)
    if e["stage"] in ("START_RISK", "WAIT_PROVIDER"):
        run = api.candidates_for_source(ticket, e["started_at"], release["worker_release_sha"])
        if run is None:
            return dict(result, disposition="FRESH_START_RISK_NO_VISIBLE_RUN_NO_REPLAY")
        need(type(run) is dict and pos(run.get("id"))
             and run.get("head_sha") == release["worker_release_sha"]
             and run.get("head_branch") == PREFIX + release["worker_release_sha"]
             and run.get("event") == "workflow_dispatch"
             and run.get("workflow_id") == 388797257
             and run.get("path") == ".github/workflows/" + WORKFLOW
             and run.get("display_title") == "F139 " + ticket
             and run.get("run_attempt") == 1
             and run.get("repository", {}).get("full_name") == REPO,
             "FRESH_RUN_IDENTITY_DRIFT")
        if run.get("status") in ("queued", "requested", "in_progress", "waiting", "pending"):
            return dict(result, disposition="FRESH_WAIT_PROVIDER", run_id=run["id"])
        need(run.get("status") == "completed", "FRESH_RUN_STATUS_UNRECOGNIZED")
        if run.get("conclusion") != "success":
            # Leave the consumed reservation intact. A failed run is never
            # positive terminal or eligible for automatic replay/admission.
            record = retain_negative_observation(db, api, release, e, run)
            return dict(result, disposition="FRESH_FAILED_PROVIDER_RETAINED_NO_REPLAY",
                        run_id=record["run_id"], provider_conclusion=record["conclusion"])
        custody = settle_provider(db, api, key, run_id=run["id"], now=now)
        return dict(result, disposition="FRESH_VERIFIED_TERMINAL",
                    run_id=custody["run_id"], development_qualified=True)
    need(e["stage"] == "VERIFIED", "FRESH_TERMINAL_STATE_INVALID")
    new = admit_next_successor(db, api, key)
    if new:
        return dict(result, disposition="FRESH_SUCCESSOR_READY",
                    successor_ticket=new["ticket"])
    if e.get("publication_attempt"):
        return dict(result, disposition="FRESH_PUBLICATION_ATTEMPT_CONSUMED_NO_RETRY",
                    successor_ticket=None)
    from f139.nci04_fresh_successor_publication import publish_one
    number = publish_one(db, api, key)
    return dict(result,
                disposition=("FRESH_SUCCESSOR_ISSUE_PUBLISHED_PENDING_ADMISSION"
                             if number else "FRESH_NO_UNUSED_SOURCE_RECIPE"),
                successor_issue_number=number, successor_ticket=None)
