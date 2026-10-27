"""Original F139 V12/G29 diagnostic: read-only, never a publication authority.

The GH Actions workflow independently authenticates original Windows owner,
scheduled-task SID, pristine V12 installation, exact SQLite path and V12
source-bound policy. This module analyzes PRE-WRITE gates only on a SQLite
read-only connection, using public GitHub GET endpoints. It never acquires the
controller lock, emits custody events, or invokes any GitHub writer.
"""
from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path

from f139.local_controller import Database, GitHub
from f139.nci04_model_owner_bridge import owner_history, owner_request, owner_response
from f139.nci04_candidate_producer import candidate_mechanism_identity
from f139.nci04_candidate_producer_g3 import mechanism_identity as g3_identity
from f139 import nci04_candidate_producer_g29 as g29
from f139.nci04_model_proposal import SCHEMA as MODEL_SCHEMA
from f139.nci04_model_owner_publication import _preflight
from f139.nci04_native_contract import canonical

SOURCE_V12 = "5ba084491ebea16f9c8b21c6deedba791a86fb1d"
ERROR_CODE = re.compile(r"F139_[A-Z0-9_]+")


def diagnose_original_prewrite(path: Path, source_sha: str) -> dict:
    if type(path) is not Path or not path.is_file() or source_sha != SOURCE_V12:
        raise ValueError("F139_G29_DIAG_SOURCE_OR_ORIGINAL_PATH")
    # Build an exact canonical Database object with a genuinely READ-ONLY
    # sqlite3 connection: calling Database(path) would set WAL PRAGMAs and
    # is intentionally avoided on the running original owner.
    db = object.__new__(Database)
    db.filename = path
    db.conn = sqlite3.connect(
        "file:" + str(path.resolve()).replace("\\", "/") + "?mode=ro",
        uri=True, isolation_level=None, timeout=10)
    db.conn.row_factory = sqlite3.Row
    db.conn.execute("PRAGMA query_only=ON")
    stage = "COLD_DB_VERIFY"
    try:
        db.verify()
        meta = db.meta()
        if (meta["source_sha"] != SOURCE_V12
                or meta["enabled"] != 1
                or meta["legacy_suspended"] != 1
                or meta["head_seq"] < 253
                or db.ready() is not None or db.actives()):
            raise ValueError("F139_G29_DIAG_ACTIVATION_OR_INFLIGHT_CHANGED")
        api = GitHub()
        real_main = api.native_repo_get("repos/spoonman136668-ai/FORGE/branches/main")
        real_main_sha = real_main["commit"]["sha"]
        if real_main.get("protected") is not True:
            raise ValueError("F139_G29_DIAG_PROTECTED_MAIN_UNVERIFIED")

        # The diagnostic itself was merged AFTER source V12. Only the
        # protected-main GET below is simulated to V12, to ask precisely how
        # the V12 natural tick's prewrite check behaved on its release.
        # This is NOT an owner witness and cannot authorize ANY write.
        def source_as_at_original_tick(route: str):
            result = api.native_repo_get(route)
            if route == "repos/spoonman136668-ai/FORGE/branches/main":
                result = {**result, "commit": {
                    **result["commit"], "sha": SOURCE_V12}}
            return result

        diagnostic_only_witness = lambda: True
        stage = "ORIGINAL_HISTORY"
        history = owner_history(db)
        stage = "ORIGINAL_REQUEST"
        prepared = owner_request(
            db, api.native_repo_get, api.native_repo_get,
            source_sha=SOURCE_V12, lane="Yggdrasil",
            target_commit=g29.PARENT, path=g29.PATH,
            owner_witness=diagnostic_only_witness)
        request = prepared["request"]
        stage = "G29_MECHANISM"
        produced = g29.produce_g29(
            lane="Yggdrasil", path=g29.PATH, parent_commit=g29.PARENT,
            original=prepared["before"],
            original_sha256=request["before_sha256"],
            history_sha256=request["history_sha256"],
            consumed_mechanisms={
                candidate_mechanism_identity(), g3_identity()
            },
            consumed_candidates=prepared["consumed_candidates"],
            scientific_first_use=False)
        response = canonical({
            "schema": MODEL_SCHEMA, "lane": "Yggdrasil",
            "target_commit": g29.PARENT, "path": g29.PATH,
            "history_sha256": request["history_sha256"],
            "question": "Can action-local uncertainty guide limited exploration?",
            "hypothesis": produced["record"]["hypothesis"],
            "control": produced["record"]["comparison"],
            "candidate_source": produced["source"].decode("utf-8", "strict"),
        })
        stage = "RESPONSE_REVALIDATION"
        outcome = owner_response(
            db, api.native_repo_get, api.native_repo_get,
            session=prepared["session"], raw_response=response,
            owner_witness=diagnostic_only_witness)
        stage = "PREWRITE_GITHUB_DRAFT"
        plan = _preflight(
            db, source_as_at_original_tick, api.native_repo_get,
            prepared["session"], response, diagnostic_only_witness)
        result = {
            "disposition": "ALL_PREWRITE_GATES_PASSED_READONLY",
            "event_seq": meta["head_seq"], "source_sha": SOURCE_V12,
            "observed_protected_main_sha": real_main_sha,
            "protected_main_simulated_as_release_for_diagnostic": True,
            "original_histories": len(history["history"]),
            "proposal_candidate_identity": plan["candidate_identity"],
            "stage": stage,
            "scientific_first_use": False, "paid_model_calls": 0,
            "owner_write_authorized": False,
        }
    except Exception as exc:
        code = ERROR_CODE.search(str(exc))
        result = {
            "disposition": "PREWRITE_BLOCKED_READONLY",
            "stage": stage,
            "error_code": code.group(0) if code else type(exc).__name__,
            "error_class": type(exc).__name__,
            "scientific_first_use": False, "paid_model_calls": 0,
            "owner_write_authorized": False,
        }
    finally:
        db.conn.close()
    return result
