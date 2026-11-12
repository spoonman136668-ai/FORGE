"""LCRM01-B2 source-only boundary for externally pinned public intervention receipts.

Authenticity is *not* created by this validator: trusted_pin must be supplied by
an independent, already qualified source custodian. Test pins are not scientific
admissions. No protected, prospective, or consumed source case is loaded.
"""
from __future__ import annotations
import hashlib
import json
from typing import Mapping

from lcrm01_public_feasibility import MODELS, consistent_models, do_x

REQUIRED = frozenset(("schema", "provider_ref", "source_commit", "public_split",
                      "baseline_u", "baseline_xyz", "do_target", "do_value",
                      "observed_xyz", "capture_id"))
SCHEMA = "mass.lcrm01.b2.public-do-receipt.v1"


def _bit(value: object) -> bool:
    return type(value) is int and value in (0, 1)


def digest(receipt: dict) -> str:
    return hashlib.sha256(json.dumps(receipt, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=True).encode("utf8")).hexdigest()


def public_history_digest(observations: tuple[tuple[int, int, int], ...]) -> str:
    return digest({"public_observations": observations})


def fail(reason: str, *, versions: tuple[str, ...] = MODELS) -> dict:
    return {"status": reason, "models": list(versions), "science_admitted": False,
            "new_first_use": 0, "counterfactual_acceptance": False}


def qualify_observation_only(event: Mapping[str, object]) -> dict:
    """Historical events have an action *covariate*, not a certified do label."""
    if not isinstance(event, Mapping):
        return fail("INVALID_PUBLIC_EVENT")
    fields = set(event)
    if {"target", "source", "event", "observed"}.issubset(fields):
        return fail("NO_AUTHENTICATED_DO_IN_HISTORICAL_EVENT")
    return fail("MISSING_PUBLIC_EVENT_FIELDS")


def assess(receipt: Mapping[str, object] | None, *,
           trusted_pin: Mapping[str, object] | None,
           observations: tuple[tuple[int, int, int], ...]) -> dict:
    """Scope: binary three-variable *two-SCM witness* only.

    Caller must obtain trusted_pin independently of receipt/synthetic generator:
    provider_ref, source_commit, exact sha256 and causal assignment design.
    This test function cannot verify cryptographic origin/exogeneity on its own.
    It never grants original first-use or scientific eligibility.
    """
    if not receipt or not isinstance(receipt, Mapping):
        return fail("NO_PUBLIC_DO_RECEIPT")
    if set(receipt) != REQUIRED or receipt.get("schema") != SCHEMA:
        return fail("INVALID_OR_SELF_ASSERTED_DO_SCHEMA")
    if (not isinstance(receipt["provider_ref"], str) or not receipt["provider_ref"]
        or not isinstance(receipt["source_commit"], str)
        or len(receipt["source_commit"]) != 40
        or any(c not in "0123456789abcdef" for c in receipt["source_commit"])
        or not isinstance(receipt["capture_id"], str) or not receipt["capture_id"]
        or receipt["public_split"] != "FIT"):
        return fail("INELIGIBLE_SOURCE_IDENTITY_OR_SPLIT")
    if (receipt["do_target"] != "X" or not _bit(receipt["baseline_u"])
        or not _bit(receipt["do_value"])):
        return fail("INVALID_PUBLIC_INTERVENTION_ASSIGNMENT")
    pre, post = receipt["baseline_xyz"], receipt["observed_xyz"]
    if (not isinstance(pre, (tuple, list)) or not isinstance(post, (tuple, list))
        or len(pre) != 3 or len(post) != 3
        or not all(_bit(v) for v in tuple(pre) + tuple(post))
        or tuple(pre) != (receipt["baseline_u"],) * 3):
        return fail("INVALID_BASELINE_OR_OBSERVED_VALUES")
    if not observations or any(not isinstance(row, tuple) or len(row) != 3
                               or not all(_bit(v) for v in row) for row in observations):
        return fail("INVALID_OBSERVATIONAL_HISTORY")
    if not isinstance(trusted_pin, Mapping):
        return fail("NO_INDEPENDENT_TRUST_PIN")
    # A trust pin is a supplied trusted *input* from the independent authority,
    # not a claim that the receipt itself creates an independent witness.
    keys = {"provider_ref", "source_commit", "receipt_sha256",
            "public_history_sha256", "causal_assignment_witness", "public_split"}
    if set(trusted_pin) != keys or trusted_pin.get("public_split") != "FIT":
        return fail("INCOMPLETE_INDEPENDENT_TRUST_PIN")
    if (trusted_pin.get("provider_ref") != receipt["provider_ref"]
        or trusted_pin.get("source_commit") != receipt["source_commit"]
        or trusted_pin.get("receipt_sha256") != digest(dict(receipt))
        or trusted_pin.get("public_history_sha256") != public_history_digest(observations)):
        return fail("UNPINNED_OR_TAMPERED_PUBLIC_RECEIPT")
    if trusted_pin.get("causal_assignment_witness") != "INDEPENDENTLY_VERIFIED_PAIRED_EXOGENOUS":
        return fail("CAUSAL_ASSIGNMENT_NOT_INDEPENDENTLY_VERIFIED")
    x, change = receipt["baseline_u"], receipt["do_value"]
    if x == change:
        return fail("NON_DISCRIMINATING_DO_EQUALS_BASELINE")
    if tuple(post)[0] != change:
        return fail("DO_TARGET_MISMATCH")
    models = consistent_models(observations, ((x, change, tuple(post)),))
    if len(models) == 0:
        return fail("OUTCOME_CONTRADICTS_WITNESS_VERSION_SPACE", versions=())
    if len(models) != 1:
        return fail("PUBLIC_DO_DID_NOT_IDENTIFY_WITNESS_MODEL", versions=models)
    # This is a conditional logical identification *inside two toy SCMs*,
    # not evidence of real independently authenticated intervention or science.
    return {"status": "TWO_SCM_CONDITIONAL_DISCRIMINATION",
            "models": list(models), "public_contrast": list(post),
            "science_admitted": False, "new_first_use": 0,
            "counterfactual_acceptance": False,
            "scope": "conditional logic only; external custody unverified by this function"}


def analytic_fixture(model: str) -> tuple[dict, dict]:
    """Explicit sourcefree hand-authored mock trust, NEVER a real certificate."""
    if model not in MODELS:
        raise ValueError("TOY_MODEL")
    row = {"schema":SCHEMA, "provider_ref":"ANALYTIC_FIXTURE_NOT_PROVIDER",
           "source_commit":"1" * 40, "public_split":"FIT", "baseline_u":0,
           "baseline_xyz":[0,0,0], "do_target":"X", "do_value":1,
           "observed_xyz":list(do_x(0, 1, model)),
           "capture_id":"SOURCEFREE_NO_REAL_WITNESS"}
    pin = {"provider_ref":row["provider_ref"], "source_commit":row["source_commit"],
           "receipt_sha256":digest(row),
           "public_history_sha256":public_history_digest(tuple((u, u, u) for u in (0,1,0,1,1,0,0,1))),
           "causal_assignment_witness":"INDEPENDENTLY_VERIFIED_PAIRED_EXOGENOUS",
           "public_split":"FIT"}
    return row, pin
