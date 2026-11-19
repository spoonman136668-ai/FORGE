"""One bounded Wingless R8 source-custody repair proposal; no owner effects.

The approved model-source scope already permits the exact R8 TrainingSession
path; this module does not widen it. The source parent is an unmerged
project-owned, index-repaired development branch, NOT protected Wingless main.
It must not become a live F139 ticket without independent Wingless source
qualification and original-owner admission.

The experiment is an engineering fault-control: after an external source reset
succeeds, a later model-choice error must latch quarantine instead of allowing
a second unauthenticated reset. It is not a new learning algorithm or science.
"""
from __future__ import annotations

import hashlib
import re

from f139.nci04_autonomy_feed import candidate_identity
from f139.nci04_model_proposal import SCHEMA as RESPONSE_SCHEMA, validate
from f139.nci04_native_contract import canonical, digest, model_source_path_allowed

LANE = "Wingless"
PATH = "research/native/itd02/outcome/training_session.go"
PARENT = "f8d7113e7d2b6fa3a39939a213b032bdf91e403b"
BLOB = "9d444da474f3e1761e6494b64717b026c73fc9ce"
BEFORE_SHA256 = "9f82bfabaf83222ae98114a2e06fa08cb43dff23dc89ec0fddc72f37e462306c"
MECHANISM = "r8-choice-error-after-source-reset-quarantine-v1"
ANCHOR = (
    "        action, err := s.Learner.ChooseRewardExplore(\n"
    "            before, s.MinimumSelectedSamples)\n"
    "        if err != nil {\n"
    "            return zero, nil, err\n"
    "        }\n"
)
REPLACEMENT = (
    "        action, err := s.Learner.ChooseRewardExplore(\n"
    "            before, s.MinimumSelectedSamples)\n"
    "        if err != nil {\n"
    "            // The source reset already happened. Never repeat it when\n"
    "            // selection fails; original owner must reconcile custody.\n"
    "            s.quarantined = true\n"
    "            return zero, nil, err\n"
    "        }\n"
)
QUESTION = "Can a failed native choice after a source reset be retried safely?"
HYPOTHESIS = (
    "Latching session quarantine after an invalid pre-action observation "
    "prevents repeated external resets without fabricating feedback."
)
CONTROL = (
    "Original exact-source R8 TrainingSession, source-reset/invalid-public-grid "
    "negative, no duplicate ResetPublic or StepPublic, unchanged selected-action "
    "learning and checkpoint contracts; require original native full regression."
)
SHA40 = re.compile(r"[0-9a-f]{40}\Z")
SHA64 = re.compile(r"[0-9a-f]{64}\Z")


class R8SourceDenied(ValueError):
    pass


def need(ok: bool, reason: str) -> None:
    if not ok:
        raise R8SourceDenied("F139_WINGLESS_R8_" + reason)


def git_blob(data: bytes) -> str:
    return hashlib.sha1(
        b"blob " + str(len(data)).encode("ascii") + b"\0" + data
    ).hexdigest()


def mechanism_sha256() -> str:
    return digest(canonical({
        "lane": LANE, "target_commit": PARENT, "path": PATH,
        "before_sha256": BEFORE_SHA256, "operator": MECHANISM,
        "replacement_sha256": digest(REPLACEMENT.encode("utf-8")),
    }))


def propose(*, target_commit: str, path: str, original_bytes: bytes,
            authenticated_git_blob: str, history_sha256: str,
            consumed_after_sha256: set[str],
            consumed_mechanism_sha256: set[str],
            scientific_first_use: bool = False) -> dict:
    """Return one source-bound proposal, never an executable authorization."""
    need(target_commit == PARENT and path == PATH and
         model_source_path_allowed(LANE, path), "TARGET_SCOPE")
    need(type(original_bytes) is bytes
         and 100 <= len(original_bytes) <= 32768
         and digest(original_bytes) == BEFORE_SHA256
         and authenticated_git_blob == BLOB
         and git_blob(original_bytes) == BLOB
         and type(history_sha256) is str
         and SHA64.fullmatch(history_sha256) is not None
         and type(consumed_after_sha256) is set
         and type(consumed_mechanism_sha256) is set
         and len(consumed_after_sha256) <= 10000
         and len(consumed_mechanism_sha256) <= 10000
         and all(type(v) is str and SHA64.fullmatch(v)
                 for v in consumed_after_sha256 | consumed_mechanism_sha256)
         and scientific_first_use is False,
         "SOURCE_HISTORY_OR_AUTHORITY_DRIFT")
    need(mechanism_sha256() not in consumed_mechanism_sha256,
         "MECHANISM_CONSUMED")
    try:
        before = original_bytes.decode("utf-8", "strict")
    except UnicodeError as exc:
        raise R8SourceDenied("F139_WINGLESS_R8_INVALID_UTF8") from exc
    need(before.count(ANCHOR) == 1
         and "func (s *TrainingSession) RunEpisode(" in before
         and "before, err := env.ResetPublic()" in before
         and "s.checkpointUnconfirmed = true" in before
         and "s.quarantined = true" in before,
         "ORIGINAL_SOURCE_ANCHOR_DRIFT")
    after = before.replace(ANCHOR, REPLACEMENT, 1).encode("utf-8")
    after_sha = digest(after)
    need(after_sha not in consumed_after_sha256, "AFTER_SOURCE_CONSUMED")
    identity = candidate_identity(LANE, PARENT, PATH, after_sha)
    raw_response = canonical({
        "schema": RESPONSE_SCHEMA, "lane": LANE,
        "target_commit": PARENT, "path": PATH,
        "history_sha256": history_sha256, "question": QUESTION,
        "hypothesis": HYPOTHESIS, "control": CONTROL,
        "candidate_source": after.decode("utf-8", "strict"),
    })
    checked = validate(
        raw_response, lane=LANE, target_commit=PARENT, path=PATH,
        before=original_bytes, before_sha256=BEFORE_SHA256,
        history_sha256=history_sha256, consumed_candidates=set(),
        consumed_after_hashes=consumed_after_sha256)
    need(identity == checked["record"]["candidate_identity"],
         "ORIGINAL_MODEL_CONTRACT_DRIFT")
    return {
        "source": after,
        "raw_response": raw_response,
        "candidate_identity": identity,
        "mechanism_sha256": mechanism_sha256(),
        "source_after_sha256": after_sha,
        "original_source_git_blob": BLOB,
        "original_source_parent": PARENT,
        "original_source_path": PATH,
        "original_source_reviewed": False,
        "original_owner_authenticated": False,
        "owner_publication_authorized": False,
        "worker_dispatched": False,
        "scientific_first_use": False,
        "paid_model_calls": 0,
        "new_controller": False,
        "new_scheduler": False,
    }
