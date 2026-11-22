"""One-shot source-backed issue publication by the EXISTING F139 owner.

The original Windows owner must hold its SQLite mutex. An append-only attempt
is committed BEFORE the GitHub POST; an uncertain response permanently blocks
automatic retries. On a later tick the normal GET-only successor admission
may reconcile the exact published issue. No second queue or scheduler.
"""
from __future__ import annotations

from f139.local_controller import SingleOwner
from f139.nci04_fresh_dev_exclusions import candidate_violates_frozen_exclusions
from f139.nci04_fresh_native_activation import audit_fresh_native_activation
from f139.nci04_fresh_native_owner_route import _sealed_json
from f139.nci04_fresh_worker_protocol import SOURCE, TARGET, TARGET_TREE
from f139.nci04_fresh_successor_producer import (
    SCHEMA as LEGACY_PROPOSAL_SCHEMA, propose_from_original_owner,
)
from f139.nci04_fresh_structured_dev import SCHEMA as STRUCTURED_PROPOSAL_SCHEMA
from f139.nci04_fresh_curriculum_owner import plan_next_structured_dev_from_original_owner
from f139.nci04_fresh_lifecycle import (
    PUBLISH_KIND, PUBLISH_SCHEMA, PUBLISH_SCHEMA_STRUCTURED,
    read_lifecycle, authenticate_runtime_owner, need, digest,
)
from f139.nci04_owner_issue import inspect_owner_issue

def publish_one(db, api, key):
    """Return a new *issue number* only after provider-verified publication.

    This does not admit a task, dispatch a worker or inspect candidate results.
    An HTTP error after the attempt is always ambiguous and never retried.
    """
    need(SingleOwner.held(db.filename.with_suffix(".lock")),
         "PUBLICATION_ORIGINAL_OWNER_LOCK_REQUIRED")
    release, entries = read_lifecycle(db, key)
    authenticate_runtime_owner(db, api, release, key)
    last = entries[-1]
    need(last["stage"] == "VERIFIED", "PUBLICATION_BEFORE_TERMINAL")
    if last.get("publication_attempt"):
        return None

    activation = audit_fresh_native_activation(db)
    root = db.filename.parent
    consumed, consumed_bytes = _sealed_json(root / "consumed-development-identities.json")
    floor, floor_bytes = _sealed_json(root / "remote-issue-cutover-floor.json")
    boundary, boundary_bytes = _sealed_json(root / "yggdrasil-research-lineage.json")
    need(digest(consumed_bytes) == activation["consumed_exclusions_sha256"]
         and digest(floor_bytes) == activation["remote_cutover_receipt_sha256"]
         and digest(boundary_bytes) == activation["yggdrasil_research_boundary_sha256"]
         and floor["target_forge_source_sha"] == SOURCE
         and floor["remote_cutover_issue_provider_verified"] is True
         and floor["remote_cutover_issue_number_floor"] == activation["remote_issue_number_floor"]
         and boundary["accepted_main_source_sha"] == TARGET,
         "PUBLICATION_SEALED_HISTORY_DRIFT")
    attempted = set(consumed["old_source_after_sha256"])
    attempted.update(row["record"]["after_sha256"] for row in entries)
    attempted.update(row["publication_attempt"]["after_sha256"]
                     for row in entries if row.get("publication_attempt"))
    plan = propose_from_original_owner(api, entries[0]["record"], attempted)
    if plan is None:
        # Source-only candidate builds cannot activate this route. Only the
        # separately source-forwarded original Windows owner can enter here,
        # after independently verifying its own SID/task/checkout/release.
        # No second controller, scheduler, queue or scientific first-use.
        plan = plan_next_structured_dev_from_original_owner(
            db=db, api=api, owner_key=key, remaining_cost_units=16)
    if plan is None:
        return None
    need(plan["schema"] in (LEGACY_PROPOSAL_SCHEMA,
                            STRUCTURED_PROPOSAL_SCHEMA),
         "PUBLICATION_GENERATOR_SCHEMA_INVALID")
    v2 = plan["schema"] == STRUCTURED_PROPOSAL_SCHEMA

    # Require the provider target and immutable first owner seed to remain the
    # actual native admission contract. No synthetic/third-party identity.
    initial = entries[0]["record"]
    need(initial["source_sha"] == SOURCE
         and initial["native_target_commit"] == TARGET
         and initial["native_target_tree"] == TARGET_TREE
         and initial["native_path"] == "yggdrasil/public_causal_cells.py"
         and plan["after_sha256"] not in attempted
         and plan["intent_sha256"] not in
             {row["record"]["native_intent_sha256"] for row in entries}
         and plan["scientific_first_use"] is False
         and plan["paid_model_calls"] == 0,
         "PUBLICATION_CANDIDATE_CUSTODY_INVALID")
    event = {
        "schema": (PUBLISH_SCHEMA_STRUCTURED if v2 else PUBLISH_SCHEMA),
        "ticket": last["record"]["ticket"],
        "source_sha": SOURCE, "target_sha": TARGET,
        "recipe": plan["recipe"],
        "mechanism_sha256": plan["mechanism_sha256"],
        "after_sha256": plan["after_sha256"],
        "intent_sha256": plan["intent_sha256"],
        "issue_body_sha256": plan["body_sha256"],
        "scientific_first_use": False, "paid_model_calls": 0,
    }
    head = db.meta()["head_hash"]
    with db.transaction():
        db.verify()
        need(db.meta()["head_hash"] == head and db.ready() is None
             and not db.actives(), "PUBLICATION_ORIGINAL_HEAD_MOVED")
        db.event(PUBLISH_KIND, event)
        db.verify()
    # From here onward this recipe/attempt is irrevocably consumed. On any
    # uncertain POST the NEXT tick may only GET for this exact frozen intent.
    # NEVER resubmit a request just because the network returned no response.
    issue = api.create_native_feed_issue(
        title=plan["title"], body=plan["body"])
    need(type(issue) is dict and
         type(issue.get("number")) is int and issue["number"] > 1849,
         "PUBLICATION_REMOTE_ISSUE_NUMBER_INVALID_NO_RETRY")
    current = api.get("repos/spoonman136668-ai/FORGE/issues/" +
                      str(issue["number"]))
    native = inspect_owner_issue(
        current, protected_main=SOURCE,
        authenticated_target_commit=TARGET,
        authenticated_target_tree=TARGET_TREE)
    need(native.issue_id == issue["id"]
         and native.number == issue["number"]
         and native.native_intent_sha256 == plan["intent_sha256"]
         and native.candidate.after_sha256 == plan["after_sha256"]
         and native.issue_body_sha256 == plan["body_sha256"]
         and current["body"] == plan["body"],
         "PUBLICATION_REMOTE_READBACK_DRIFT_NO_RETRY")
    return issue["number"]
