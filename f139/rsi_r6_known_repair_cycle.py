"""Finite native repair synthesis for an authenticated, already failed FORGE job.

DEVELOPMENT ONLY: this is a deterministic candidate producer, not an owner hook.
The original Windows F139 owner, native lanes, protected refs and FSA are never
opened or modified. Unknown failures, unauthenticated receipts and consumed
attempts are denied; no speculative retry is possible.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import ast
import re

from f139.r16_semantic_repair import (
    UnsafeRepair, _repair_python, synthesize_workflow_repair,
)
from f139.rsi_r4_native_alias_repair import AliasRepairDenied, propose as propose_alias

SCHEMA = "forge.f139.rsi-r6.source-only-known-repair.v1"
FAILURE = "WINDOWS_SQLITE_OPEN_HANDLE_CLEANUP"
HEAD = re.compile(r"[0-9a-f]{40}\Z")
DIGEST = re.compile(r"[0-9a-f]{64}\Z")
WORKFLOW_PATH = ".github/workflows/forge-f139-r13-owner-continuity-cold-audit.yml"
PATH = re.compile(r"(?:f139/[A-Za-z0-9_]+\.py|"
                  + re.escape(WORKFLOW_PATH) + r")\Z")
MAX_SOURCE = 24_999
MAX_LOG = 128_000


class RepairDenied(ValueError):
    pass


def need(ok: bool, reason: str) -> None:
    if not ok:
        raise RepairDenied("F139_RSI_R6_" + reason)


def digest(data: bytes) -> str:
    return sha256(data).hexdigest()


@dataclass(frozen=True)
class Evidence:
    """Values must originate from independently authenticated GitHub evidence.

    The producer checks internal consistency, not GitHub authenticity. A test
    fixture or a caller assertion is never owner or deployment authorization.
    """
    head_sha: str
    run_id: int
    job_id: int
    failure_class: str
    failed_log_sha256: str
    failed_log: bytes
    target_path: str
    target_source_sha256: str


@dataclass(frozen=True)
class Proposal:
    schema: str
    task_scope_sha256: str
    parent_sha: str
    path: str
    original_sha256: str
    candidate_sha256: str
    source: bytes
    mechanism: str
    original_failure_class: str
    # No condition may turn a source-only proposal into owner authority.
    eligible_for_owner: bool = False
    qualified: bool = False
    scientific_first_use: bool = False
    deployed: bool = False
    autonomous_rsi_proven: bool = False


def task_scope(evidence: Evidence) -> str:
    need(type(evidence) is Evidence and type(evidence.head_sha) is str
         and HEAD.fullmatch(evidence.head_sha) is not None,
         "ORIGIN_COMMIT_INVALID")
    need(type(evidence.run_id) is int and evidence.run_id > 0
         and type(evidence.job_id) is int and evidence.job_id > 0,
         "PROVIDER_RUN_INVALID")
    need(type(evidence.target_path) is str
         and PATH.fullmatch(evidence.target_path) is not None,
         "TARGET_SCOPE_INVALID")
    need(type(evidence.target_source_sha256) is str
         and DIGEST.fullmatch(evidence.target_source_sha256) is not None
         and type(evidence.failed_log_sha256) is str
         and DIGEST.fullmatch(evidence.failed_log_sha256) is not None,
         "DIGEST_INVALID")
    need(type(evidence.failed_log) is bytes
         and 0 < len(evidence.failed_log) <= MAX_LOG
         and digest(evidence.failed_log) == evidence.failed_log_sha256,
         "PROVIDER_LOG_DRIFT")
    need(evidence.failure_class == FAILURE,
         "FAILURE_CLASS_UNSUPPORTED")
    # The actual original Windows exception and original SQLite database path
    # must be present.  This is only a class correlation, NOT independent
    # authentication of the provider or proof of repair applicability.
    need(b"PermissionError: [WinError 32]" in evidence.failed_log
         and b"state.sqlite" in evidence.failed_log,
         "FAILURE_SIGNATURE_MISMATCH")
    data = (SCHEMA + "\n" + evidence.head_sha + "\n"
            + str(evidence.run_id) + "\n" + str(evidence.job_id) + "\n"
            + evidence.failed_log_sha256 + "\n"
            + evidence.target_path + "\n"
            + evidence.target_source_sha256 + "\n").encode("ascii")
    return digest(data)


def propose(*, evidence: Evidence, pinned_before: bytes,
            consumed_scopes: frozenset[str]) -> Proposal:
    """Propose one previously unseen bounded source change; NEVER dispatch.

    Safe external orchestration would still need: authenticated source+job,
    isolated fixed-command qualification, separate owner admissibility, and
    content-addressed persistent no-replay custody before ANY effect.
    """
    scope = task_scope(evidence)
    need(type(consumed_scopes) is frozenset
         and all(type(x) is str and DIGEST.fullmatch(x) is not None
                 for x in consumed_scopes), "CONSUMED_CUSTODY_INVALID")
    need(scope not in consumed_scopes, "SCOPE_ALREADY_CONSUMED")
    need(type(pinned_before) is bytes
         and 0 < len(pinned_before) <= MAX_SOURCE
         and b"\r" not in pinned_before
         and digest(pinned_before) == evidence.target_source_sha256,
         "PINNED_BEFORE_SOURCE_DRIFT")
    try:
        original = pinned_before.decode("ascii", "strict")
        tree = None if evidence.target_path == WORKFLOW_PATH else ast.parse(original)
    except (UnicodeError, SyntaxError) as exc:
        raise RepairDenied("F139_RSI_R6_UNSAFE_OR_INVALID_SOURCE") from exc
    # These are TWO already independently developed source grammars, not a
    # claim to invent unbounded repairs. Preserve R16's transaction behavior.
    has_alias = (tree is not None and any(
        isinstance(node, ast.Import)
        and any(item.name == "sqlite3" and item.asname
                for item in node.names)
        for node in tree.body))
    try:
        if evidence.target_path == WORKFLOW_PATH:
            after_text, count = synthesize_workflow_repair(original, FAILURE)
            need(1 <= count <= 6, "INVALID_EMBEDDED_REPAIR_COUNT")
            after, mechanism = after_text.encode("ascii"), "r16-embedded-workflow"
        elif has_alias:
            repair = propose_alias(
                original_source=pinned_before,
                expected_sha256=evidence.target_source_sha256,
                path=evidence.target_path, failure_class=FAILURE)
            after, mechanism = repair.proposed_source, repair.rule
        else:
            after_text, count = _repair_python(original)
            need(1 <= count <= 6, "INVALID_REPAIR_COUNT")
            after, mechanism = after_text.encode("ascii"), "r16-direct"
    except (AliasRepairDenied, UnsafeRepair, UnicodeError, ValueError) as exc:
        raise RepairDenied("F139_RSI_R6_KNOWN_GRAMMAR_NOT_APPLICABLE") from exc
    need(type(after) is bytes and 0 < len(after) <= MAX_SOURCE
         and after != pinned_before, "CANDIDATE_UNSAFE_OR_UNCHANGED")
    if evidence.target_path != WORKFLOW_PATH:
        try:
            compile(after, evidence.target_path, "exec")
        except SyntaxError as exc:
            raise RepairDenied("F139_RSI_R6_CANDIDATE_UNPARSABLE") from exc
    return Proposal(SCHEMA, scope, evidence.head_sha, evidence.target_path,
                    evidence.target_source_sha256, digest(after), after,
                    mechanism, FAILURE)
