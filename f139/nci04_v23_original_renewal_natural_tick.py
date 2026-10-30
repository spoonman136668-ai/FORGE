"""Original F139 owner's existing natural tick -> V21 renewable source route.

No new controller, task, scheduler, queue, protected writer or paid API.
This module is called ONLY by the existing F139 run_once after the eight
original V17 free attempts have been consumed. A new authenticated native
terminal must exist after all old spends; time rollover/source changes cannot
make old evidence eligible. No credential means no request.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Callable

from f139.local_controller import Database, SingleOwner
from f139.nci04_free_reasoner_provider import (
    _post_one, _public_get, public_packet, verify_anonymous_public_source,
)
from f139.nci04_model_owner_bridge import owner_request
from f139.nci04_owner_ledger import frozen_native_issue
from f139.nci04_owner_model_free_bootstrap import original_canonical_db
from f139.nci04_v19_research_renewal_shadow import is_sha40
from f139.nci04_v22_original_cli_bridge_sourceonly import (
    run_original_cli_v21_source_only,
)


class OriginalRenewalRuntimeDenied(ValueError):
    pass


def _packet_for_verified_terminal(
    db: Database, api: object, witness: dict, *,
    source_sha: str, owner_witness: Callable[[], bool],
    public_reader: Callable[[str], dict],
) -> dict:
    """Reconstruct native target from original *ledger*, not model input."""
    if (type(db) is not Database or not SingleOwner.held(
            db.filename.with_suffix(".lock"))
            or type(witness) is not dict
            or witness.get("disposition") !=
               "AUTHENTIC_FRESH_TERMINAL_SHADOW_ONLY_NOT_AUTHORIZED"
            or witness.get("owner_source_sha") != source_sha
            or type(witness.get("terminal_event_seq")) is not int
            or witness["terminal_event_seq"] < 1
            or not callable(owner_witness) or owner_witness() is not True):
        raise OriginalRenewalRuntimeDenied("F139_V23_TERMINAL_WITNESS_INVALID")
    db.verify()
    record = db.conn.execute(
        "SELECT kind,payload FROM events WHERE seq=?",
        (witness["terminal_event_seq"],)).fetchone()
    if record is None or record["kind"] != "PROVIDER_VERIFIED_TERMINAL":
        raise OriginalRenewalRuntimeDenied("F139_V23_TERMINAL_NOT_IN_ORIGINAL_LEDGER")
    original = json.loads(record["payload"])
    issue = frozen_native_issue(db, original["ticket"])
    if (issue.source_sha != source_sha or
            issue.lane not in ("Wingless", "Yggdrasil") or
            not is_sha40(issue.candidate.target_commit)):
        raise OriginalRenewalRuntimeDenied("F139_V23_FROZEN_NATIVE_TARGET_DRIFT")
    prepared = owner_request(
        db, api.native_repo_get, api.native_repo_get,
        source_sha=source_sha, lane=issue.lane,
        target_commit=issue.candidate.target_commit,
        path=issue.candidate.path, owner_witness=owner_witness)
    packet = public_packet(prepared["request"], public_source_verified=True)
    if (packet["lane"] != issue.lane or
            packet["target_commit"] != issue.candidate.target_commit or
            packet["target_tree_sha"] != issue.candidate.target_tree_sha or
            packet["path"] != issue.candidate.path or
            packet["before_sha256"] != issue.candidate.before_sha256):
        raise OriginalRenewalRuntimeDenied("F139_V23_PACKET_SOURCE_SCOPE_DRIFT")
    # Prove publicness before V21 could ever reserve the original terminal.
    # The handoff and one-shot sender independently repeat this exact GET.
    if verify_anonymous_public_source(packet, public_reader) is not True:
        raise OriginalRenewalRuntimeDenied("F139_V23_PUBLIC_SOURCE_NOT_AUTHENTICATED")
    return packet


def run_original_renewal_from_natural_tick(
    db: object, api: object, db_path: Path, *, source_sha: str,
    owner_witness: Callable[[], bool], utc_day: str,
    token: str | None = None,
    public_reader: Callable[[str], dict] | None = None,
    transport: Callable[[bytes, str], bytes] | None = None,
) -> dict:
    """Existing owner-only entry; externally injected test doubles are inert.

    The live owner may read only the historical free-only credential already
    permitted by V17. The source is public and the model endpoint remains the
    one fixed `:free` transport. No paid fallback. No restored quota.
    """
    if not isinstance(db_path, Path) or not is_sha40(source_sha):
        raise OriginalRenewalRuntimeDenied("F139_V23_SOURCE_IDENTITY_REQUIRED")
    if (not callable(owner_witness) or owner_witness() is not True):
        raise OriginalRenewalRuntimeDenied("F139_V23_RUNNING_OWNER_WITNESS_REQUIRED")
    if token is None:
        token = os.environ.get("OPENROUTER_API_KEY")
    if not isinstance(token, str) or not token.strip():
        return {"disposition": "NATIVE_RENEWAL_NO_FREE_CREDENTIAL_NO_REQUEST",
                "paid_model_calls": 0, "worker_dispatched": False,
                "scientific_first_use": False}
    if len(token) > 2048 or "\r" in token or "\n" in token:
        raise OriginalRenewalRuntimeDenied("F139_V23_CREDENTIAL_FORMAT_INVALID")
    reader = _public_get if public_reader is None else public_reader
    send = _post_one if transport is None else transport
    if not callable(reader) or not callable(send):
        raise OriginalRenewalRuntimeDenied("F139_V23_TRANSPORT_CAPABILITY_INVALID")
    def frozen_packet(witness: dict) -> dict:
        canonical, close = original_canonical_db(db, db_path)
        try:
            return _packet_for_verified_terminal(
                canonical, api, witness, source_sha=source_sha,
                owner_witness=owner_witness, public_reader=reader)
        finally:
            if close:
                canonical.close()
    return run_original_cli_v21_source_only(
        db, api, db_path, utc_day=utc_day,
        packet_for_terminal=frozen_packet,
        public_reader=reader, owner_witness=owner_witness,
        token=token, transport=send)
