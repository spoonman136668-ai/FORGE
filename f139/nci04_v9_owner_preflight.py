"""Fail-closed read-only V9 original-owner source transition preflight.

This does not mutate the ledger, policy, Windows task, or source checkout.
A V8 successor must be based on the actual authenticated original ledger,
not the one-time G50 event-225 precondition.
"""
from __future__ import annotations

import re
from f139.nci04_owner_ledger import verify_native_activation
from f139.nci04_release_pin_continuity import (
    ReleaseContinuityDenied, verify_release_worker_branch,
)

SHA = re.compile(r"[a-f0-9]{40}\Z")


class V9TransitionDenied(ValueError):
    pass


def verify_v9_owner_preflight(db, get, *, expected_old_source: str,
                              target_source: str) -> dict:
    from f139.local_controller import Database
    if type(db) is not Database:
        raise V9TransitionDenied("F139_V9_ORIGINAL_DATABASE_REQUIRED")
    if (not isinstance(expected_old_source, str)
            or SHA.fullmatch(expected_old_source) is None):
        raise V9TransitionDenied("F139_V9_OLD_SOURCE_INVALID")
    db.verify()
    meta = db.meta()
    if (meta["source_sha"] != expected_old_source
            or meta["enabled"] != 1
            or meta["legacy_suspended"] != 1
            or not isinstance(target_source, str)
            or SHA.fullmatch(target_source) is None
            or target_source == expected_old_source
            or db.ready() is not None or db.actives()
            or not verify_native_activation(db)):
        raise V9TransitionDenied("F139_V9_OWNER_LEDGER_OR_SOURCE_DRIFT")
    try:
        branch = verify_release_worker_branch(get, target_source)
    except (ReleaseContinuityDenied, KeyError, TypeError, ValueError) as exc:
        raise V9TransitionDenied("F139_V9_WORKER_RELEASE_REF_INVALID") from exc
    return {
        "from_source_sha": expected_old_source,
        "to_source_sha": target_source,
        "prior_event_seq": meta["head_seq"],
        "prior_event_sha256": meta["head_hash"],
        "worker_branch": branch,
        "scientific_first_use": False,
        "mutation_performed": False,
    }
