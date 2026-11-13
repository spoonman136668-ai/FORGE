"""Read-only V41 #1715 escrow replay; no writer or dispatch authority."""
import json
import re
from f139.local_controller import canonical as event_canonical
from f139.nci04_v41_catalog_recovery_preflight import OWNER_SOURCE, OBSERVED_SEQ, OBSERVED_HEAD

KIND = "NATIVE_PENDING_ESCROWED"
SCHEMA = "forge.f139.v41.pending-escrow.v1"
FIELDS = frozenset(("schema", "source_sha", "issue_number", "issue_id",
    "ticket", "issue_body_sha256", "native_intent_sha256",
    "semantic_identity_sha256", "target_commit", "target_tree_sha",
    "original_head_seq", "original_head_sha256", "frozen_observed_seq",
    "frozen_observed_head_sha256", "owner_comment_id",
    "owner_comment_body_sha256", "pending_disposition", "new_dispatches",
    "reissue_authorized", "scientific_first_use", "hybrid_admission"))
SHA40 = re.compile(r"[a-f0-9]{40}\Z")
SHA64 = re.compile(r"[a-f0-9]{64}\Z")
TICKET = re.compile("f139-nci04-i1715-" + OWNER_SOURCE[:12] + r"-[a-f0-9]{8}\Z")

class EscrowDenied(ValueError):
    pass

def need(ok, reason):
    if not ok:
        raise EscrowDenied("F139_V41_ESCROW_" + reason)

def _sha(value, regex):
    return type(value) is str and regex.fullmatch(value) is not None

def verify_event_shape(row, doc):
    """Pure event grammar; scoped owner approval requires separate verification."""
    need(type(row) is dict and type(doc) is dict and set(doc) == FIELDS, "FIELDS")
    need(type(row.get("seq")) is int and row["seq"] > OBSERVED_SEQ
         and _sha(row.get("prior_sha"), SHA64)
         and doc["schema"] == SCHEMA and doc["source_sha"] == OWNER_SOURCE
         and type(doc["issue_number"]) is int and doc["issue_number"] == 1715
         and type(doc["issue_id"]) is int and doc["issue_id"] == 6333201763
         and type(doc["ticket"]) is str and TICKET.fullmatch(doc["ticket"])
         and all(_sha(doc[k], SHA64) for k in (
             "issue_body_sha256", "native_intent_sha256",
             "semantic_identity_sha256", "owner_comment_body_sha256"))
         and all(_sha(doc[k], SHA40) for k in ("target_commit", "target_tree_sha"))
         and type(doc["original_head_seq"]) is int
         and doc["original_head_seq"] == row["seq"] - 1
         and doc["original_head_sha256"] == row["prior_sha"]
         and doc["frozen_observed_seq"] == OBSERVED_SEQ
         and doc["frozen_observed_head_sha256"] == OBSERVED_HEAD
         and type(doc["owner_comment_id"]) is int and doc["owner_comment_id"] > 0
         and doc["pending_disposition"] == "EXPLICIT_ESCROW_ONCE"
         and type(doc["new_dispatches"]) is int and doc["new_dispatches"] == 0
         and doc["reissue_authorized"] is False
         and doc["scientific_first_use"] is False
         and doc["hybrid_admission"] is False,
         "IDENTITY_OR_AUTHORITY")
    return True

def verify_before_transition(db, transition_seq):
    """A sole escrow must immediately precede V41 source transition."""
    need(type(transition_seq) is int and transition_seq > OBSERVED_SEQ + 1
         and getattr(db, "conn", None) is not None, "NOT_A_COLD_TRANSITION")
    rows = db.conn.execute(
        "SELECT seq,kind,sha,prior_sha,payload FROM events WHERE kind=? ORDER BY seq",
        (KIND,)).fetchall()
    need(len(rows) == 1 and rows[0]["seq"] == transition_seq - 1,
         "ESCROW_MISSING_DUPLICATE_OR_NONADJACENT")
    r = rows[0]
    need(_sha(r["sha"], SHA64), "ESCROW_SHA_INVALID")
    try:
        doc = json.loads(r["payload"])
    except (TypeError, ValueError, UnicodeError) as exc:
        raise EscrowDenied("F139_V41_ESCROW_JSON_INVALID") from exc
    verify_event_shape({"seq": r["seq"], "prior_sha": r["prior_sha"]}, doc)
    need(event_canonical(doc).decode("ascii") == r["payload"],
         "ESCROW_NONCANONICAL")
    observed = db.conn.execute("SELECT sha FROM events WHERE seq=?",
                                (OBSERVED_SEQ,)).fetchone()
    need(observed is not None and observed["sha"] == OBSERVED_HEAD,
         "ORIGINAL_FROZEN_PREFIX_DRIFT")
    for row in db.conn.execute(
            "SELECT payload FROM events WHERE kind='NATIVE_DEVELOPMENT_ADMITTED'"):
        item = json.loads(row["payload"])
        need(item.get("issue_number") != 1715
             and item.get("issue_id") != 6333201763
             and item.get("ticket") != doc["ticket"], "ISSUE_ALREADY_ADMITTED")
    need(db.conn.execute("SELECT 1 FROM tasks WHERE ticket=?",
                         (doc["ticket"],)).fetchone() is None,
         "ISSUE_TASK_ALREADY_PRESENT")
    return r["sha"]


def audit_committed_escrow(db):
    """Fail closed on any escrow left committed without its V41 transition.

    During the *single existing owner-locked SQLite transaction*, the escrow
    is briefly a valid provisional last event while build_proof calls verify().
    Once the transaction ends, escrow must be immediately followed by exactly
    one v36 SOURCE_TRANSITION_ADMITTED. A cold reopen must never accept a
    stranded escrow as a healthy old-source owner.
    """
    from f139.local_controller import SingleOwner
    rows = list(db.conn.execute(
        "SELECT seq,sha,prior_sha,payload FROM events WHERE kind=? ORDER BY seq",
        (KIND,)))
    if not rows:
        return "NO_ESCROW"
    need(len(rows) == 1, "MULTIPLE_ESCROWS")
    row = rows[0]
    need(type(row["seq"]) is int and _sha(row["sha"], SHA64),
         "EVENT_IDENTITY_DRIFT")
    try:
        doc = json.loads(row["payload"])
    except (TypeError, ValueError, UnicodeError) as exc:
        raise EscrowDenied("F139_V41_ESCROW_EVENT_JSON") from exc
    verify_event_shape({"seq": row["seq"], "prior_sha": row["prior_sha"]}, doc)
    next_row = db.conn.execute(
        "SELECT seq,kind,sha,prior_sha,payload FROM events WHERE seq=?",
        (row["seq"] + 1,)).fetchone()
    if next_row is None:
        # Provisional state exists only within the copy's owner-held transaction.
        # Reopening a committed orphan necessarily fails these checks.
        m = db.meta()
        need(db.conn.in_transaction
             and not getattr(db, "_readonly_opened", False)
             and db.conn.execute("PRAGMA query_only").fetchone()[0] == 0
             and SingleOwner.held(db.filename.with_suffix(".lock"))
             and m["source_sha"] == OWNER_SOURCE
             and m["head_seq"] == row["seq"] and m["head_hash"] == row["sha"],
             "COMMITTED_OR_UNOWNED_ORPHAN")
        return "PROVISIONAL_OWNER_TRANSACTION"
    need(next_row["seq"] == row["seq"] + 1
         and next_row["kind"] == "SOURCE_TRANSITION_ADMITTED"
         and next_row["prior_sha"] == row["sha"],
         "NONADJACENT_OR_WRONG_SUCCESSOR")
    try:
        successor = json.loads(next_row["payload"])
    except (TypeError, ValueError, UnicodeError) as exc:
        raise EscrowDenied("F139_V41_ESCROW_SUCCESSOR_JSON") from exc
    need(type(successor) is dict
         and successor.get("schema") == "forge.f139.source-transition.v36"
         and successor.get("from_source_sha") == OWNER_SOURCE
         and _sha(successor.get("to_source_sha"), SHA40)
         and successor["to_source_sha"] != OWNER_SOURCE
         and successor.get("original_head_seq") == row["seq"]
         and successor.get("prior_event_head_sha256") == row["sha"]
         and successor.get("pending_1715_escrow_sha256") == row["sha"]
         and successor.get("owner_event_id") == doc["owner_comment_id"],
         "SOURCE_PAIR_IDENTITY_DRIFT")
    return "PAIRED_V41_TRANSITION"
