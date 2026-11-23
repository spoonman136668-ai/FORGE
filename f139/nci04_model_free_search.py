"""Deterministic, finite source search on the existing original owner.

Three explicit development operators, no inference, credentials or randomness.
They test shrinkage, confidence-based abstention and local recency separately;
none promotes policy or claims scientific novelty. After all fresh operators
are consumed this returns exhaustion, never an LLM fallback or a quota reset.
The existing publisher journals before writing and the next ordinary tick must
independently reauthenticate, admit and evaluate each draft.
"""
from __future__ import annotations

import ast
import base64
import json
from pathlib import Path
from functools import lru_cache

from f139.nci04_native_contract import canonical, digest
from f139.nci04_model_owner_bridge import owner_request
from f139.nci04_model_owner_publication import ATTEMPT, SUCCESS, publish_model_once
from f139.nci04_model_proposal import SCHEMA
from f139.nci04_owner_ledger import native_events
from f139.nci04_owner_model_free_bootstrap import _run_original_local_proposal

PARENT = "992ef142aaa551156749a1de484a971b9a0c092f"
PATH = "yggdrasil/public_causal_cells.py"
BEFORE_SHA256 = "4f57fef8f6e287ffef66ca8cf313cce5c137d76de9aba63201eb0401d1782c50"
RATE = "        lhs, rhs = one0 * trials1, one1 * trials0\n"
CHOICE = "        return 0 if lhs > rhs else 1\n"
UPDATE = ("        old = self._counts[cell][arm][result]\n"
          "        self._counts[cell][arm][result] = min(65535, old + 1)\n")
# Fixed mathematical operators, not numeric tuning or replays of G1/G3/G29.
OPERATORS = (
    ("within-context-laplace-shrinkage", RATE,
     "        lhs = (one0 + 1) * (trials1 + 2)\n"
     "        rhs = (one1 + 1) * (trials0 + 2)\n",
     "Does within-context Laplace shrinkage reduce imbalanced-arm error?",
     "A symmetric unit pseudo-count may reduce sparse empirical overconfidence; "
     "it may bias rare but valid action evidence."),
    ("empirical-standard-error-abstention", CHOICE,
     "        gap = lhs - rhs\n"
     "        # Abstain inside one empirical standard error of the rate gap.\n"
     "        variance = (one0 * zero0 * trials1 ** 3\n"
     "                    + one1 * zero1 * trials0 ** 3)\n"
     "        if gap * gap * trials0 * trials1 <= variance:\n"
     "            return None\n"
     "        return 0 if lhs > rhs else 1\n",
     "Does standard-error abstention prevent weak-evidence action choices?",
     "Local observed variance may suppress unstable choices; test lost coverage "
     "and sparse deterministic evidence as failure modes."),
    ("cell-local-exponential-recency", UPDATE,
     "        # Decay both arms in this public cell before adding new evidence.\n"
     "        for prior_arm in self._counts[cell]:\n"
     "            for outcome in range(2):\n"
     "                prior_arm[outcome] //= 2\n"
     "        self._counts[cell][arm][result] += 1\n",
     "Does cell-local exponential recency adapt to changing public outcomes?",
     "Forgetting local old evidence may adapt to reversal; test stationary "
     "retention loss and abstention as explicit negative controls."),
)


def _normalized_uncached(source: bytes) -> str:
    """Original complete parse and AST-digest semantics, including failures."""
    try:
        tree = ast.parse(source.decode("utf-8", "strict"))
    except (SyntaxError, UnicodeError) as exc:
        # Candidate validation must fail closed without killing the owner loop.
        raise ValueError("F139_MODEL_FREE_SEARCH_SOURCE_NOT_PARSEABLE") from exc
    return digest(ast.dump(tree, include_attributes=False).encode("utf-8"))


@lru_cache(maxsize=64)
def _normalized_exact_bytes(source: bytes) -> str:
    # Only successful immutable source-byte identities are retained in-process.
    return _normalized_uncached(source)


def normalized(source: bytes) -> str:
    """Reject syntax and semantic replays; reuse only exact immutable source bytes.

    Bounded to 64 valid source entries of at most 256 KiB each. Large or
    mutable inputs preserve their original uncached validation behavior.
    Neither authenticated history nor negative outcomes are cached.
    """
    if type(source) is bytes and len(source) <= 256_000:
        return _normalized_exact_bytes(source)
    return _normalized_uncached(source)


def candidates(before: bytes):
    if type(before) is not bytes or digest(before) != BEFORE_SHA256:
        raise ValueError("F139_MODEL_FREE_SEARCH_FROZEN_SOURCE_DRIFT")
    text = before.decode("utf-8", "strict")
    for name, anchor, replacement, question, hypothesis in OPERATORS:
        if text.count(anchor) != 1:
            raise ValueError("F139_MODEL_FREE_SEARCH_OPERATOR_BOUNDARY_DRIFT")
        source = text.replace(anchor, replacement, 1).encode("utf-8")
        normalized(source)  # Parse only; never execute candidate in owner process.
        yield name, source, question, hypothesis


def consumed_source_identities(db, consumed_after_hashes, attempts=None, *,
                               with_sources=False, with_parent_eligibility=False):
    """Reuse complete source-use custody for publication and cold rehearsal."""
    if with_parent_eligibility:
        if not with_sources:
            raise ValueError("F139_MODEL_FREE_SEARCH_PARENT_SOURCES_REQUIRED")
        db.verify()
    if attempts is None:
        attempts = list(db.conn.execute(
            "SELECT payload FROM events WHERE kind=? ORDER BY seq", (ATTEMPT,)))
    consumed = set(consumed_after_hashes)
    consumed.update(json.loads(row["payload"])["source_after_sha256"]
                    for row in attempts)
    # Retain every original outcome, including negatives and historical sources.
    prior_asts = set()
    sources = []
    parent_stages = {}
    for event in native_events(db):
        intent = json.loads(base64.b64decode(event["native_intent_base64"], validate=True))
        if intent["lane"] == "Yggdrasil" and intent["path"] == PATH:
            raw = base64.b64decode(intent["after_base64"], validate=True)
            sources.append(raw)
            if with_parent_eligibility:
                task = db.conn.execute(
                    "SELECT stage FROM tasks WHERE ticket=?", (event["ticket"],)).fetchone()
                if task is None or task["stage"] not in {
                        "READY", "START_RISK", "WAIT_PROVIDER", "VERIFIED", "QUARANTINED"}:
                    raise ValueError("F139_MODEL_FREE_SEARCH_PARENT_TASK_DRIFT")
                parent_stages.setdefault(digest(raw), set()).add(task["stage"])
            try:
                prior_asts.add(normalized(raw))
            except ValueError:
                # Original invalid-source negatives are legitimate retained
                # evidence, not syntax trees. Their raw hashes/identities stay
                # consumed through owner_history; never repair/replay the source.
                task = db.conn.execute(
                    "SELECT stage FROM tasks WHERE ticket=?", (event["ticket"],)).fetchone()
                if task is None or task["stage"] != "QUARANTINED":
                    raise ValueError("F139_MODEL_FREE_SEARCH_INVALID_NONNEGATIVE_HISTORY")
                consumed.add(digest(raw))
    if with_parent_eligibility:
        # Engineering qualification only, never task utility or a science reward.
        # Conflicting/nonterminal histories cannot rehabilitate a failed source.
        eligible = frozenset(key for key, stages in parent_stages.items()
                             if stages == {"VERIFIED"})
        return consumed, prior_asts, tuple(sources), eligible
    return (consumed, prior_asts, tuple(sources)) if with_sources else (consumed, prior_asts)


def local_search_once(db, get, steering_get, write, *, source_sha, owner_witness):
    db.verify()
    # Journal incompleteness remains sticky across source releases and dates.
    attempts = list(db.conn.execute(
        "SELECT payload FROM events WHERE kind=? ORDER BY seq", (ATTEMPT,)))
    successes = list(db.conn.execute(
        "SELECT payload FROM events WHERE kind=? ORDER BY seq", (SUCCESS,)))
    from f139.nci04_partial_publication_custody import custodied_ids
    if len(attempts) != len(successes) + len(custodied_ids(db)):
        return report("MODEL_DRAFT_UNRESOLVED_NO_REPLAY")
    prepared = owner_request(
        db, get, steering_get, source_sha=source_sha, lane="Yggdrasil",
        target_commit=PARENT, path=PATH, owner_witness=owner_witness)
    consumed, prior_asts = consumed_source_identities(db, prepared["consumed_after_hashes"], attempts)
    for name, source, question, hypothesis in candidates(prepared["before"]):
        if digest(source) in consumed or normalized(source) in prior_asts:
            continue
        response = canonical({
            "schema": SCHEMA, "lane": "Yggdrasil", "target_commit": PARENT,
            "path": PATH, "history_sha256": prepared["request"]["history_sha256"],
            "question": question, "hypothesis": hypothesis,
            "control": "Unmodified pinned parent, fixed native regression, unfamiliar "
                       "family and action/context controls; retain every negative. "
                       "No holdout access, policy promotion or scientific first-use.",
            "candidate_source": source.decode("utf-8"),
        })
        outcome = publish_model_once(
            db, get, steering_get, write, session=prepared["session"],
            raw_response=response, owner_witness=owner_witness)
        return {**outcome, "generator": "DETERMINISTIC_SOURCE_SEARCH",
                "operator": name, "model_calls": 0, "paid_model_calls": 0}
    from f139.nci04_genenv_owner_backend import publish_after_exhaustion
    return publish_after_exhaustion(
        db, get, steering_get, write, prepared=prepared, consumed=consumed,
        historical_asts=prior_asts, source_sha=source_sha, owner_witness=owner_witness)


def report(disposition):
    return {"disposition": disposition, "generator": "DETERMINISTIC_SOURCE_SEARCH",
            "model_calls": 0, "paid_model_calls": 0, "scientific_first_use": False,
            "worker_dispatched": False}


def run_original_model_free_once(db, api, db_path: Path, *, source_sha, owner_witness):
    return _run_original_local_proposal(
        db, api, db_path, source_sha, owner_witness, local_search_once)
