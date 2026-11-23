"""G3: finite, source-only local-evidence confidence gating proposal.

Distinct from G1 cross-context pooling: this mechanism uses ONLY the action
outcomes already observed at the queried address. Abstain when either local
arm has fewer than three observations. This can reduce sparse-sample errors
but can also worsen exploration or retention; scientific transfer UNTESTED.
No GitHub write, owner activation, scientific original or paid model.
"""
from __future__ import annotations

import ast
import hashlib
import re

from f139.nci04_autonomy_feed import candidate_identity
from f139.nci04_native_contract import canonical, digest

SCHEMA = "forge.f139.g3.local-evidence-abstention.v1"
MECHANISM = "local-three-observation-abstention-v1"
LANE = "Yggdrasil"
PATH = "yggdrasil/public_causal_cells.py"
ANCHOR = (
    "        if not trials0 or not trials1:\n"
    "            return None\n"
)
REPLACEMENT = (
    "        # G3 hypothesis: refuse fragile causal rankings at sparse local counts.\n"
    "        # Never borrow counts from other contexts or memory tiers.\n"
    "        if trials0 < 3 or trials1 < 3:\n"
    "            return None\n"
)
SHA40 = re.compile(r"[a-f0-9]{40}\Z")
SHA64 = re.compile(r"[a-f0-9]{64}\Z")


class G3Denied(ValueError):
    pass


def require(ok: bool, reason: str) -> None:
    if not ok:
        raise G3Denied("F139_G3_" + reason)


def mechanism_identity() -> str:
    return digest(canonical({
        "schema": SCHEMA, "mechanism": MECHANISM, "lane": LANE,
        "path": PATH, "replacement_sha256": hashlib.sha256(
            REPLACEMENT.encode("utf-8")).hexdigest(),
    }))


def produce_g3(*, lane: str, path: str, parent_commit: str,
               original: bytes, original_sha256: str,
               history_sha256: str, consumed_mechanisms: set[str],
               consumed_candidates: set[str],
               scientific_first_use: bool = False) -> dict:
    """Derive bounded candidate bytes; caller independently authenticates Git."""
    require(lane == LANE and path == PATH and
            isinstance(parent_commit, str) and SHA40.fullmatch(parent_commit)
            and type(original) is bytes and 100 <= len(original) <= 32768
            and isinstance(original_sha256, str)
            and hashlib.sha256(original).hexdigest() == original_sha256
            and isinstance(history_sha256, str) and SHA64.fullmatch(history_sha256)
            and type(consumed_mechanisms) is set
            and type(consumed_candidates) is set
            and all(isinstance(x, str) and SHA64.fullmatch(x)
                    for x in consumed_mechanisms | consumed_candidates)
            and len(consumed_mechanisms) <= 10000
            and len(consumed_candidates) <= 10000
            and scientific_first_use is False,
            "INPUT_OR_CUSTODY_INVALID")
    identity = mechanism_identity()
    require(identity not in consumed_mechanisms, "MECHANISM_CONSUMED_NO_REPLAY")
    try:
        text = original.decode("utf-8", "strict")
        ast.parse(text, filename=PATH)
    except (UnicodeError, SyntaxError, ValueError) as exc:
        raise G3Denied("F139_G3_ORIGINAL_NOT_VALID_PYTHON") from exc
    require(text.count(ANCHOR) == 1 and
            "class PublicCausalCells:" in text and
            "def choose(self, address:" in text and
            "trials0 = " in text and "trials1 = " in text,
            "SOURCE_ANCHOR_DRIFT")
    changed = text.replace(ANCHOR, REPLACEMENT, 1)
    try:
        ast.parse(changed, filename=PATH)
    except SyntaxError as exc:
        raise G3Denied("F139_G3_GENERATED_SYNTAX_FAILURE") from exc
    source = changed.encode("utf-8")
    require(source != original and len(source) <= 32768,
            "GENERATED_SOURCE_OUT_OF_BOUNDS")
    after_hash = hashlib.sha256(source).hexdigest()
    candidate = candidate_identity(lane, parent_commit, path, after_hash)
    require(candidate not in consumed_candidates, "CANDIDATE_CONSUMED_NO_REPLAY")
    record = {
        "schema": SCHEMA, "mechanism": MECHANISM,
        "mechanism_sha256": identity, "candidate_identity": candidate,
        "source_before_sha256": original_sha256,
        "source_after_sha256": after_hash, "history_sha256": history_sha256,
        "parent_commit": parent_commit, "lane": lane, "path": path,
        "hypothesis": "Three per-arm local observations reduce noisy interventions",
        "negative_risks": ["slower_learning", "persistent_abstention"],
        "independent_unfamiliar_transfer": "NOT_TESTED",
        "scientific_first_use": False, "paid_model_calls": 0,
        "dispatch_authorized": False, "publish_authorized": False,
        "new_controller": False, "new_scheduler": False,
    }
    return {"source": source, "record": record,
            "record_sha256": digest(canonical(record)),
            "candidate_identity": candidate,
            "pr_title": "F139 autonomy DEV: local evidence confidence gating"}
