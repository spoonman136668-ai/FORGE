"""Original-owner-only, *finite* model-free G29 proposal bootstrap.

This is NOT autonomous model inference or a reusable open-ended generator.
It closes one engineering connection: an already-reviewed source mechanism can
be converted into the merged #995/#998 proposal validation and #1000
at-most-once draft publishing path inside the original Windows owner.
No Codex, API model, paid inference, new controller, scheduler or science.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Callable

from f139.nci04_candidate_producer import candidate_mechanism_identity
from f139.nci04_candidate_producer_g3 import mechanism_identity as g3_identity
from f139 import nci04_candidate_producer_g29 as g29
from f139.nci04_model_owner_bridge import owner_request
from f139.nci04_model_owner_publication import (
    ATTEMPT, SUCCESS, publish_model_once,
)
from f139.nci04_model_proposal import SCHEMA as MODEL_SCHEMA
from f139.nci04_native_contract import canonical
from f139.local_controller import Database

LANE = "Yggdrasil"
PATH = "yggdrasil/public_causal_cells.py"


class LocalBootstrapDenied(ValueError):
    pass


def need(condition: bool, why: str) -> None:
    if not condition:
        raise LocalBootstrapDenied("F139_LOCAL_G29_" + why)


def original_canonical_db(db, db_path: Path):
    """Same original SQLite under the externally held single-owner mutex.

    The native CLI runs its controller module as __main__; the merged model
    bridge deliberately requires the canonical imported Database class.
    Reopen the SAME on-disk original, not a copied/synthetic SQLite or a
    second controller. The caller closes this connection before returning.
    """
    need(isinstance(db_path, Path) and db_path.is_file(),
         "ORIGINAL_DATABASE_PATH_REQUIRED")
    resolved = db_path.resolve(strict=True)
    need(isinstance(getattr(db, "filename", None), Path)
         and db.filename.resolve(strict=True) == resolved,
         "ORIGINAL_DATABASE_IDENTITY_DRIFT")
    if type(db) is Database:
        return db, False
    main = sys.modules.get("__main__")
    need(type(db).__module__ == "__main__"
         and type(db).__name__ == "Database"
         and main is not None
         and isinstance(getattr(main, "__file__", None), str)
         and Path(main.__file__).resolve(strict=True) ==
             (Path(__file__).resolve().parent / "local_controller.py").resolve(strict=True),
         "ORIGINAL_NATIVE_CLI_CLASS_REQUIRED")
    canon = Database(resolved)
    need(canon.filename.resolve(strict=True) == resolved,
         "ORIGINAL_DATABASE_REOPEN_CHANGED")
    return canon, True


def local_proposal_once(db: Database, get: Callable, steering_get: Callable,
                        write: Callable, *, source_sha: str,
                        owner_witness: Callable[[], bool]) -> dict:
    """Source-authenticated, at-most-once G29 proposal, with model-format data.

    Running source and old G29 frozen target are both independently verified
    by the existing bridge. History and source hash checks are repeated by the
    publisher immediately before any original-owner ledger mutation.
    """
    need(type(db) is Database
         and callable(get) and callable(steering_get)
         and callable(write) and callable(owner_witness)
         and owner_witness() is True,
         "ORIGINAL_OWNER_REQUIRED")
    db.verify()
    past = list(db.conn.execute(
        "SELECT kind,payload FROM events WHERE kind IN (?,?) ORDER BY seq",
        (ATTEMPT, SUCCESS)))
    if past:
        need(all(json.loads(row["payload"]).get("schema") ==
                 "forge.f139.owner-model-draft-publication.v1" for row in past),
             "PREVIOUS_MODEL_ATTEMPT_DRIFT")
        # A previous remote write may be ambiguous. No automatic retries.
        return {"disposition": "LOCAL_G29_ALREADY_ATTEMPTED_NO_REPLAY",
                "scientific_first_use": False, "worker_dispatched": False,
                "paid_model_calls": 0}
    prepared = owner_request(
        db, get, steering_get, source_sha=source_sha,
        lane=LANE, target_commit=g29.PARENT, path=PATH,
        owner_witness=owner_witness)
    req = prepared["request"]
    before = prepared["before"]
    produced = g29.produce_g29(
        lane=LANE, path=PATH, parent_commit=g29.PARENT,
        original=before, original_sha256=req["before_sha256"],
        history_sha256=req["history_sha256"],
        consumed_mechanisms={candidate_mechanism_identity(), g3_identity()},
        consumed_candidates=prepared["consumed_candidates"],
        scientific_first_use=False)
    need(produced["record"]["scientific_first_use"] is False
         and produced["record"]["publish_authorized"] is False
         and produced["record"]["dispatch_authorized"] is False
         and produced["record"]["paid_model_calls"] == 0,
         "GENERATOR_AUTHORITY_DRIFT")
    # MODEL_SCHEMA is a strict byte format, not a claim that a language model
    # authored this proposal. The payload's question/control are transparent.
    response = canonical({
        "schema": MODEL_SCHEMA,
        "lane": LANE,
        "target_commit": g29.PARENT,
        "path": PATH,
        "history_sha256": req["history_sha256"],
        "question": "Can action-local uncertainty guide limited exploration?",
        "hypothesis": produced["record"]["hypothesis"],
        "control": produced["record"]["comparison"],
        "candidate_source": produced["source"].decode("utf-8", "strict"),
    })
    outcome = publish_model_once(
        db, get, steering_get, write,
        session=prepared["session"], raw_response=response,
        owner_witness=owner_witness)
    return {**outcome, "generator": "BOUNDED_MODEL_FREE_G29",
            "paid_model_calls": 0, "scientific_first_use": False}


def run_original_g29_once(db, api, db_path: Path, source_sha: str,
                          owner_witness: Callable[[], bool]) -> dict:
    """Called only from existing run_once, while SingleOwner remains held."""
    from f139.local_controller import GitHub, SingleOwner
    need(type(api) is GitHub and
         SingleOwner.held(db_path.with_suffix(".lock")) and
         callable(owner_witness) and owner_witness() is True,
         "ORIGINAL_RUNNING_SINGLE_OWNER_REQUIRED")
    canonical_db, close = original_canonical_db(db, db_path)
    try:
        return local_proposal_once(
            canonical_db, api.native_repo_get, api.native_repo_get,
            api.owner_model_write, source_sha=source_sha,
            owner_witness=owner_witness)
    finally:
        if close:
            canonical_db.close()
