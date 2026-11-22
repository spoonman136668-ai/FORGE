"""Bounded Wingless-native source proposal supplier; no GitHub or owner side effects.

This is a *development* mechanism for existing Wingless research lineage, NOT
a new scientific worker. The caller must authenticate the Git parent/tree/blob,
complete original F139 consumed history, and the independent evaluation owner.
The protected Wingless main currently lacks this candidate-only cognition file.
Do not silently substitute main or publish a branch-stacked PR as main-based.
"""
from __future__ import annotations

import hashlib
import re

from f139.nci04_autonomy_feed import candidate_identity
from f139.nci04_native_contract import canonical, digest

LANE = "Wingless"
REPOSITORY = "spoonman136668-ai/Wingless"
PARENT = "9087de76fd4be50eb304fd3b2cec1ae443ba2b65"
PATH = "cognition/continual.go"
SCHEMA = "forge.f139.native-source-candidate.v1"
MECHANISM = "wingless-two-timescale-evidence-floor-v1"
GENERATOR = "bounded-project-owned-go-source"
ANCHOR = " if disagreement0 == disagreement1 { return 0, false, nil }\n"
REPLACEMENT = (
    " // Reject low-evidence interventions; measure lost information gain against\n"
    " // the source-identical always-probe and random-cost controls.\n"
    " if math.Max(disagreement0, disagreement1) < 0.10 { return 0, false, nil }\n"
    + ANCHOR
)
SHA64 = re.compile(r"[0-9a-f]{64}\Z")


class WinglessSourceDenied(ValueError):
    pass


def require(ok: bool, reason: str) -> None:
    if not ok:
        raise WinglessSourceDenied("F139_WINGLESS_SOURCE_" + reason)


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii")
                        + b"\0" + raw).hexdigest()


def mechanism_id() -> str:
    return digest(canonical({
        "schema": SCHEMA,
        "lane": LANE,
        "parent": PARENT,
        "path": PATH,
        "recipe": MECHANISM,
        "replacement_sha256": _sha(REPLACEMENT.encode("utf-8")),
    }))


def propose(*, lane: str, parent_commit: str, path: str,
            before_bytes: bytes, verified_git_blob_sha: str,
            pinned_before_sha256: str, owner_history_sha256: str,
            consumed_mechanisms: set[str],
            consumed_source_sha256: set[str],
            scientific_first_use: bool = False) -> dict:
    """Produce one source-bound candidate, or explicitly fail closed.

    A supplied Git blob identity is cross-checked, NOT independently fetched.
    Independent Git GET and owner-ledger verification are caller obligations.
    This function never sends code to the original owner or a private worker.
    """
    require(lane == LANE and path == PATH and parent_commit == PARENT,
            "TARGET_LINEAGE_UNQUALIFIED")
    require(type(before_bytes) is bytes and 100 <= len(before_bytes) <= 32768
            and type(verified_git_blob_sha) is str
            and re.fullmatch(r"[0-9a-f]{40}", verified_git_blob_sha) is not None
            and _blob(before_bytes) == verified_git_blob_sha
            and type(pinned_before_sha256) is str
            and _sha(before_bytes) == pinned_before_sha256
            and type(owner_history_sha256) is str
            and SHA64.fullmatch(owner_history_sha256) is not None
            and type(consumed_mechanisms) is set
            and type(consumed_source_sha256) is set
            and len(consumed_mechanisms) <= 10000
            and len(consumed_source_sha256) <= 10000
            and all(type(x) is str and SHA64.fullmatch(x) is not None
                    for x in consumed_mechanisms | consumed_source_sha256)
            and scientific_first_use is False, "SOURCE_OR_AUTHORITY_DRIFT")
    require(mechanism_id() not in consumed_mechanisms,
            "MECHANISM_ALREADY_CONSUMED")
    try:
        before = before_bytes.decode("utf-8", "strict")
    except UnicodeError as exc:
        raise WinglessSourceDenied("F139_WINGLESS_SOURCE_UTF8_INVALID") from exc
    require(before.count(ANCHOR) == 1
            and "func (d *FastSlowState) ChooseDisagreementProbe" in before
            and "disagreement0 := math.Abs(fast0 - slow0)" in before
            and "disagreement1 := math.Abs(fast1 - slow1)" in before
            and ' "math"' in before, "SOURCE_BOUNDARY_DRIFT")
    after = before.replace(ANCHOR, REPLACEMENT, 1).encode("utf-8")
    require(after != before_bytes and len(after) <= 32768,
            "CANDIDATE_BYTES_INVALID")
    after_sha = _sha(after)
    require(after_sha not in consumed_source_sha256,
            "CANDIDATE_ALREADY_CONSUMED")
    identity = candidate_identity(LANE, PARENT, PATH, after_sha)
    record = {
        "schema": SCHEMA, "lane": LANE, "repository": REPOSITORY,
        "parent_commit": PARENT, "path": PATH,
        "original_git_blob_sha": verified_git_blob_sha,
        "before_sha256": pinned_before_sha256, "after_sha256": after_sha,
        "candidate_identity": identity, "mechanism_sha256": mechanism_id(),
        "history_sha256": owner_history_sha256,
        "generator": GENERATOR,
        "hypothesis": (
            "A 0.10 learned two-timescale disagreement floor may reduce "
            "unproductive public interventions without harming causal "
            "identification, cold retention, or unfamiliar-world transfer."
        ),
        "needed_controls": (
            "source-identical always-probe, no-probe, random-probe, "
            "fully trained recurrent and empirical; matched actions/cost"
        ),
        "cross_platform_qualified": False,
        "original_owner_admitted": False,
        "scientific_first_use": False, "dispatch_authorized": False,
        "policy_promotion_authorized": False,
        "independent_scientific_acceptance": False,
        "paid_model_calls": 0, "new_controller": False,
        "new_scheduler": False,
    }
    return {
        "source": after, "record": record,
        "record_sha256": digest(canonical(record)),
        "candidate_identity": identity,
        "pr_title": "F139 autonomy DEV: Wingless bounded disagreement probe",
        "requires_original_owner_witness": True,
        "requires_independent_source_authentication": True,
        "requires_full_linux_windows_native_qualification": True,
        "requires_separate_research_first_use": True,
    }
