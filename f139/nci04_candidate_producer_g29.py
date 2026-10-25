"""G29: inert, bounded source-only local action-uncertainty candidate.

Conventional Bayesian exploration baseline, not novel scientific cognition.
Neither original F139 SQLite nor GitHub publication is modified here.
"""
from __future__ import annotations

import ast
import hashlib
import re

from f139.nci04_autonomy_feed import candidate_identity
from f139.nci04_native_contract import canonical, digest

SCHEMA = "forge.f139.g29.local-action-probe.v1"
MECHANISM = "local-beta-variance-action-probing-v1"
PARENT = "992ef142aaa551156749a1de484a971b9a0c092f"
LANE = "Yggdrasil"
PATH = "yggdrasil/public_causal_cells.py"
ANCHOR = "        return 0 if lhs > rhs else 1\n"
METHOD = """
    def probe_uncertain(self, address: int, *, retained: bool = False) -> int:
        \"\"\"Select public action with greatest LOCAL Beta(1,1) uncertainty.

        No other context, hidden outcomes, memory writes, or changed choose().
        Equal scores deterministically choose action zero.
        \"\"\"
        cell = self._address(address, retained)
        (zero0, one0), (zero1, one1) = self._counts[cell]
        n0, n1 = zero0 + one0 + 2, zero1 + one1 + 2
        a0, a1 = (zero0 + 1) * (one0 + 1), (zero1 + 1) * (one1 + 1)
        # Compare Beta variances exactly: a / (n*n*(n+1)).
        lhs = a0 * n1 * n1 * (n1 + 1)
        rhs = a1 * n0 * n0 * (n0 + 1)
        return 1 if rhs > lhs else 0
"""
SHA64 = re.compile(r"[a-f0-9]{64}\Z")


class G29Denied(ValueError):
    pass


def require(ok: bool, reason: str) -> None:
    if not ok:
        raise G29Denied("F139_G29_" + reason)


def mechanism_identity() -> str:
    return digest(canonical({
        "schema": SCHEMA, "mechanism": MECHANISM,
        "lane": LANE, "path": PATH,
        "method_sha256": hashlib.sha256(METHOD.encode("utf-8")).hexdigest(),
    }))


def produce_g29(*, lane: str, path: str, parent_commit: str,
                original: bytes, original_sha256: str, history_sha256: str,
                consumed_mechanisms: set[str],
                consumed_candidates: set[str],
                scientific_first_use: bool = False) -> dict:
    """Derive bytes only; caller independently authenticates original Git."""
    require(lane == LANE and path == PATH and parent_commit == PARENT
            and type(original) is bytes and 100 <= len(original) <= 32768
            and isinstance(original_sha256, str)
            and hashlib.sha256(original).hexdigest() == original_sha256
            and isinstance(history_sha256, str)
            and SHA64.fullmatch(history_sha256) is not None
            and type(consumed_mechanisms) is set
            and type(consumed_candidates) is set
            and len(consumed_mechanisms) <= 10000
            and len(consumed_candidates) <= 10000
            and all(isinstance(v, str) and SHA64.fullmatch(v) is not None
                    for v in consumed_mechanisms | consumed_candidates)
            and scientific_first_use is False,
            "INPUT_OR_HISTORICAL_CUSTODY_INVALID")
    mechanism_sha = mechanism_identity()
    require(mechanism_sha not in consumed_mechanisms,
            "MECHANISM_ALREADY_CONSUMED_NO_REPLAY")
    try:
        before = original.decode("utf-8", "strict")
        ast.parse(before, filename=PATH)
    except (UnicodeError, SyntaxError, ValueError) as exc:
        raise G29Denied("F139_G29_ORIGINAL_SOURCE_INVALID") from exc
    require(before.count(ANCHOR) == 1
            and before.count("class PublicCausalCells:") == 1
            and "    def choose(self, address:" in before
            and "    def _address(cls, address:" in before
            and "probe_uncertain" not in before,
            "FROZEN_NATIVE_SOURCE_BOUNDARY_DRIFT")
    changed = before.replace(ANCHOR, ANCHOR + METHOD + "\n", 1)
    try:
        ast.parse(changed, filename=PATH)
    except SyntaxError as exc:
        raise G29Denied("F139_G29_GENERATED_SOURCE_INVALID") from exc
    after = changed.encode("utf-8")
    require(after != original and len(after) <= 32768,
            "GENERATED_SOURCE_OUT_OF_BOUNDS")
    after_sha = hashlib.sha256(after).hexdigest()
    identity = candidate_identity(lane, parent_commit, path, after_sha)
    require(identity not in consumed_candidates,
            "CANDIDATE_ALREADY_CONSUMED_NO_REPLAY")
    record = {
        "schema": SCHEMA, "mechanism": MECHANISM,
        "mechanism_sha256": mechanism_sha,
        "candidate_identity": identity,
        "source_before_sha256": original_sha256,
        "source_after_sha256": after_sha,
        "history_sha256": history_sha256,
        "parent_commit": parent_commit,
        "lane": lane, "path": path,
        "hypothesis": "Local outcome uncertainty improves intervention selection",
        "comparison": "equal-budget random and least-observed-arm baselines",
        "risks": ["uncertainty_trap", "reversal_underexploration"],
        "held_out_causal_transfer": "NOT_TESTED",
        "scientific_first_use": False, "paid_model_calls": 0,
        "dispatch_authorized": False, "publish_authorized": False,
        "v1_worker_authorized": False,
        "new_controller": False, "new_scheduler": False,
    }
    return {
        "source": after, "record": record,
        "record_sha256": digest(canonical(record)),
        "candidate_identity": identity,
        "pr_title": "F139 autonomy DEV: local public-outcome uncertainty probing",
    }
