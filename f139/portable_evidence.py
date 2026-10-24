"""F139 G4: data-minimal, original-validated portable negative evidence receipt.

The original Windows owner MUST validate its own SQLite + local artifact
custody before invoking export_owner_receipt. The portable verifier checks
receipt consistency and event commitments, but a portable receipt is NOT
authenticated unless its exact bytes also pass independent GitHub/Sigstore
provenance verification for the pinned original-owner workflow.

No controller, scheduler, task mutation, evidence-acceptance or scientific
first-use authority is granted by this module.
"""
from __future__ import annotations

import hashlib
import json
import re

SCHEMA = "forge.f139.owner-portable-negative.v1"
ZERO = "0" * 64
SHA40 = re.compile(r"[0-9a-f]{40}\Z")
SHA64 = re.compile(r"[0-9a-f]{64}\Z")
TICKET = re.compile(r"f139-nci04-i[1-9][0-9]*-[0-9a-f]{12}-[0-9a-f]{8}\Z")
MAX_EVENTS = 50000
MAX_BYTES = 8_000_000
TARGET_KINDS = (
    "NATIVE_DEVELOPMENT_ADMITTED",
    "ATTEMPT_QUARANTINED",
    "NATIVE_FAILED_PROVIDER_CUSTODY",
)


class PortableEvidenceDenied(ValueError):
    pass


def need(value, reason):
    if not value:
        raise PortableEvidenceDenied("F139_G4_" + reason)


def canonical(obj):
    return (json.dumps(obj, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=True) + "\n").encode("ascii")


def sha(obj):
    return hashlib.sha256(canonical(obj)).hexdigest()


def _exact(obj, names, code):
    need(type(obj) is dict and set(obj) == set(names), code)


def _hex(value, pattern):
    return isinstance(value, str) and pattern.fullmatch(value) is not None


def _headers(rows):
    result = []
    prev = ZERO
    for index, row in enumerate(rows, start=1):
        need(row["seq"] == index and row["prior_sha"] == prev
             and _hex(row["sha"], SHA64), "EVENT_HEADER_CHAIN")
        result.append({"seq": index, "prior_sha": prev, "sha": row["sha"]})
        prev = row["sha"]
    return result


def export_owner_receipt(db, ticket):
    """Only call on the original owner with a SAME-DIRECTORY disposable DB.

    Database.verify checks the original on-disk historic ZIP custody; this
    function does not open or modify the live database, nor publish anything.
    """
    from f139.nci04_owner_ledger import verify_native_activation
    need(_hex(ticket, TICKET), "TICKET_INVALID")
    db.verify()
    need(verify_native_activation(db) is True, "NATIVE_ACTIVATION_INVALID")
    meta = db.meta()
    need(meta["enabled"] == 1 and meta["legacy_suspended"] == 1
         and _hex(meta["source_sha"], SHA40), "OWNER_META_INVALID")
    rows = list(db.conn.execute(
        "SELECT seq,kind,payload,prior_sha,sha FROM events ORDER BY seq"))
    need(187 <= len(rows) <= MAX_EVENTS and meta["head_seq"] == len(rows),
         "EVENT_COUNT_INVALID")
    headers = _headers(rows)
    need(headers[-1]["sha"] == meta["head_hash"], "HEAD_HASH_DRIFT")
    task_rows = list(db.conn.execute(
        "SELECT ticket,stage,source_sha,run_id,quarantine_reason "
        "FROM tasks WHERE ticket=?", (ticket,)))
    need(len(task_rows) == 1 and task_rows[0]["stage"] == "QUARANTINED"
         and task_rows[0]["run_id"] is None
         and task_rows[0]["quarantine_reason"] ==
             "FAILED_OR_CANCELLED_NO_REPLAY", "TARGET_NOT_RETAINED_NEGATIVE")
    entries = []
    for row in rows:
        if row["kind"] not in TARGET_KINDS:
            continue
        payload = json.loads(row["payload"])
        if payload.get("ticket") != ticket:
            continue
        entry = {"seq": row["seq"], "kind": row["kind"],
                 "prior_sha": row["prior_sha"], "sha": row["sha"]}
        if row["kind"] != "NATIVE_DEVELOPMENT_ADMITTED":
            # The native admission contains a base64 source candidate.
            # Withhold it; disclose only its already sealed SHA commitment.
            entry["payload"] = payload
        entries.append(entry)
    # Valid original-owner failures use either v1 provider-before-quarantine
    # or v2 late custody after quarantine. Never discard or replay either.
    need(len(entries) == len(TARGET_KINDS) and
         {entry["kind"] for entry in entries} == set(TARGET_KINDS),
         "TARGET_ADMISSION_AND_TERMINAL_NOT_EXACTLY_ONCE")
    entries.sort(key=lambda entry: TARGET_KINDS.index(entry["kind"]))
    provider = entries[2]["payload"]["provider"]
    need(provider["provider_terminal"] == "FAILURE_NO_REPLAY"
         and provider["scientific_first_use"] is False
         and entries[2]["payload"]["run_id"] == provider["run_id"]
         and ticket in db.verified_native_provider_failures(),
         "PROVIDER_NEGATIVE_NOT_AUTHENTICATED")
    counts = {r["stage"]: r["n"] for r in db.conn.execute(
        "SELECT stage,COUNT(*) AS n FROM tasks GROUP BY stage")}
    need(set(counts) <= {"QUARANTINED", "VERIFIED"} and
         counts.get("QUARANTINED", 0) >= 11, "OWNER_TASKS_NOT_SETTLED")
    body = {
        "schema": SCHEMA, "owner_source_sha": meta["source_sha"],
        "owner_head_seq": meta["head_seq"],
        "owner_head_sha": meta["head_hash"],
        "scientific_first_use": False,
        "target_ticket": ticket, "target_source_sha": task_rows[0]["source_sha"],
        "task_stages": counts, "event_headers": headers,
        "target_events": entries,
    }
    return seal_body(body)


def seal_body(body):
    need(type(body) is dict, "BODY_NOT_OBJECT")
    return {"body": body, "body_sha256": sha(body)}


def verify_portable_receipt(raw, *, expected_ticket=None, expected_source=None):
    """Verify portable *consistency*, never claim owner provenance by itself.

    A remote caller MUST additionally use gh attestation verify with exact
    signer workflow, Git source digest and ref before trusting this receipt.
    """
    need(type(raw) is bytes and 0 < len(raw) <= MAX_BYTES, "RECEIPT_SIZE")
    try:
        obj = json.loads(raw, object_pairs_hook=_unique_json)
    except PortableEvidenceDenied:
        raise
    except (UnicodeError, ValueError, TypeError) as exc:
        raise PortableEvidenceDenied("F139_G4_RECEIPT_JSON") from exc
    _exact(obj, {"body", "body_sha256"}, "ENVELOPE_FIELDS")
    body = obj["body"]
    _exact(body, {
        "schema", "owner_source_sha", "owner_head_seq", "owner_head_sha",
        "scientific_first_use", "target_ticket", "target_source_sha",
        "task_stages", "event_headers", "target_events",
    }, "RECEIPT_FIELDS")
    need(obj["body_sha256"] == sha(body) and
         raw == canonical(obj), "NONCANONICAL_OR_TAMPERED_RECEIPT")
    need(body["schema"] == SCHEMA and body["scientific_first_use"] is False
         and _hex(body["owner_source_sha"], SHA40)
         and _hex(body["owner_head_sha"], SHA64)
         and _hex(body["target_source_sha"], SHA40)
         and _hex(body["target_ticket"], TICKET), "RECEIPT_IDENTITY")
    if expected_ticket is not None:
        need(body["target_ticket"] == expected_ticket, "TICKET_PIN_DRIFT")
    if expected_source is not None:
        need(body["owner_source_sha"] == expected_source, "SOURCE_PIN_DRIFT")
    h = body["event_headers"]
    need(type(h) is list and 187 <= len(h) <= MAX_EVENTS and
         type(body["owner_head_seq"]) is int and
         body["owner_head_seq"] == len(h), "TRUNCATED_EVENT_HEADERS")
    prev = ZERO
    for i, entry in enumerate(h, start=1):
        _exact(entry, {"seq", "prior_sha", "sha"}, "EVENT_HEADER_FIELDS")
        need(type(entry["seq"]) is int and entry["seq"] == i
             and entry["prior_sha"] == prev and _hex(entry["sha"], SHA64),
             "HEADER_DISCONTINUITY")
        prev = entry["sha"]
    need(prev == body["owner_head_sha"], "HEAD_MISMATCH")
    _exact(body["task_stages"], {"QUARANTINED", "VERIFIED"},
           "STAGE_COUNTER_FIELDS")
    counts = body["task_stages"]
    need(type(counts["QUARANTINED"]) is int and counts["QUARANTINED"] >= 11
         and type(counts["VERIFIED"]) is int and counts["VERIFIED"] >= 18,
         "STAGE_COUNTERS_INVALID")
    entries = body["target_events"]
    need(type(entries) is list and len(entries) == 3, "TARGET_EVENT_COUNT")
    for index, (entry, kind) in enumerate(zip(entries, TARGET_KINDS)):
        fields = {"seq", "kind", "prior_sha", "sha"}
        if index:
            fields.add("payload")
        _exact(entry, fields, "TARGET_EVENT_FIELDS")
        i = entry["seq"]
        need(type(i) is int and 1 <= i <= len(h)
             and entry["kind"] == kind and
             entry["sha"] == h[i-1]["sha"]
             and entry["prior_sha"] == h[i-1]["prior_sha"],
             "TARGET_EVENT_HEADER_MISMATCH")
        if index:
            rec = {"seq": i, "prior_sha": entry["prior_sha"],
                   "kind": kind, "payload": entry["payload"]}
            need(sha(rec) == entry["sha"], "TARGET_EVENT_PAYLOAD_TAMPERED")
    admission, quarantine, failure = entries
    negative = failure["payload"]
    version = negative.get("schema")
    base_fields = {
        "schema", "ticket", "run_id", "source_sha",
        "provider_sha256", "provider", "scientific_first_use",
    }
    if version == "forge.f139.owner-native-provider-negative.v1":
        need(set(negative) == base_fields and
             admission["seq"] < failure["seq"] and
             failure["seq"] + 1 == quarantine["seq"],
             "TARGET_EVENT_ORDER")
    elif version == "forge.f139.owner-native-provider-negative.v2":
        need(set(negative) == base_fields | {
                 "quarantine_event_seq", "quarantine_event_sha256"} and
             admission["seq"] < quarantine["seq"] < failure["seq"] and
             negative["quarantine_event_seq"] == quarantine["seq"] and
             negative["quarantine_event_sha256"] == quarantine["sha"],
             "TARGET_EVENT_ORDER")
    else:
        need(False, "PROVIDER_TERMINAL_SCHEMA")
    need(negative["source_sha"] == body["target_source_sha"] and
         negative["provider_sha256"] == sha(negative["provider"]) and
         negative["provider"].get("source_sha") == body["target_source_sha"],
         "PROVIDER_SOURCE_OR_DIGEST_DRIFT")
    _exact(entries[1]["payload"], {"ticket", "reason"},
           "QUARANTINE_FIELDS")
    need(entries[1]["payload"] == {
        "ticket": body["target_ticket"],
        "reason": "FAILED_OR_CANCELLED_NO_REPLAY"}, "QUARANTINE_BINDING")
    p = entries[2]["payload"]
    need(type(p) is dict and p.get("ticket") == body["target_ticket"]
         and p.get("scientific_first_use") is False, "NEGATIVE_BINDING")
    report = p.get("provider")
    need(type(report) is dict
         and report.get("ticket") == body["target_ticket"]
         and report.get("run_id") == p.get("run_id")
         and report.get("provider_terminal") == "FAILURE_NO_REPLAY"
         and report.get("scientific_first_use") is False, "PROVIDER_TERMINAL")
    artifacts = report.get("artifact_ids")
    jobs = report.get("jobs")
    need(type(artifacts) is list and len(artifacts) == 2
         and all(type(a) is int and a > 0 for a in artifacts)
         and sorted(set(artifacts)) == artifacts
         and type(jobs) is dict and set(jobs) == {
             "windows-latest", "ubuntu-latest"}
         and all(type(jobs[os].get("job_id")) is int
                 and jobs[os].get("conclusion") == "failure"
                 for os in ("windows-latest", "ubuntu-latest")),
         "PROVIDER_DUAL_OS_NEGATIVE")
    return {
        "schema": SCHEMA,
        "source_sha": body["owner_source_sha"],
        "head_seq": len(h), "head_sha": prev,
        "ticket": body["target_ticket"],
        "quarantined": counts["QUARANTINED"],
        "verified": counts["VERIFIED"],
        "provider_run_id": p["run_id"],
        "scientific_first_use": False,
        "original_custody_trust": "REQUIRES_INDEPENDENT_GITHUB_ATTESTATION",
    }


def _unique_json(pairs):
    obj = {}
    for key, value in pairs:
        need(key not in obj, "DUPLICATE_JSON_KEY")
        obj[key] = value
    return obj
