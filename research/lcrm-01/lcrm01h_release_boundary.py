"""LCRM-01 H: static source-only DoTime v1.2.0 model-input eligibility.

This module reads NO benchmark data and confers NO original scientific
admission. Release identity and experimental assignment remain external claims
until independently verified by the existing scientific authority.
"""
from __future__ import annotations
from dataclasses import dataclass

REPO = "thummd/dotime"
COMMIT = "0b7833a1d8c1b945a89bc4118b54795ed979c420"
REGISTRY_BLOB = "23371578576f4bb78cca9f284d1ed212b8991b90"
DOCUMENTATION_BLOB = "dec8b0d56a4467dd1777cf665a679aa958e12537"
NAME = "dot-Identifiability-v1"
VERSION = "1.2.0"
RECORD = "23095083"
ALLOWED = frozenset(("observed_preintervention_x_obs_prefix",
                     "mask_or_observation_times_for_same_prefix",
                     "public_intervention_target", "public_intervention_value_and_kind",
                     "public_intervention_onset", "public_query_target",
                     "public_query_time_idx"))
HIDDEN = frozenset(("x_int", "y_true", "y_causal_effect", "true_graph", "scm",
                    "hidden_u", "metadata_graph", "metadata_latent",
                    "source_structure_or_family", "heldout_truth",
                    "observed_postintervention_x_obs", "debug_source_seed",
                    "diverged_flag_as_predictive_hint", "release_effect_magnitude"))

@dataclass(frozen=True)
class SourcePlan:
    repository: str = REPO
    commit: str = COMMIT
    registry_blob: str = REGISTRY_BLOB
    docs_blob: str = DOCUMENTATION_BLOB
    suite: str = NAME
    version: str = VERSION
    zenodo_record: str = RECORD
    fields: tuple[str, ...] = tuple(sorted(ALLOWED))
    query_encoding: str = "index/T"
    length: int = 100
    intervention_onset: int = 30
    prefix_stop: int = 30  # exclusive; no post-do observational values
    query_row: int = 31
    structure: str = "mediator"
    query_kind: str = "post_treatment"
    input_split: str = "FIT"
    shared_noise_claim: bool = True
    provider_manifest_pinned: bool = False
    actual_pairing_raw_verified: bool = False
    independent_custody: bool = False
    exact_download_sha256: str | None = None
    model_counterfactual_claim: bool = True


def _deny(status: str, *, provenance_only: bool = False) -> dict[str, object]:
    return {"status": status, "source_only": True,
            "model_interface_screen_pass": False,
            "provider_payload_authenticated": False,
            "real_counterfactual_firstuse_authorized": False,
            "scientific_firstuse_consumed": 0,
            "protected_source_opened": False,
            "provenance_only": provenance_only}


def screen(p: SourcePlan) -> dict[str, object]:
    """Validate static declared interface; NEVER validate supplied identity claims."""
    if (p.repository, p.commit, p.registry_blob, p.docs_blob, p.suite, p.version,
        p.zenodo_record) != (REPO, COMMIT, REGISTRY_BLOB, DOCUMENTATION_BLOB,
                              NAME, VERSION, RECORD):
        return _deny("DENY_VERSION_OR_CODE_PROVENANCE_DRIFT")
    if p.input_split != "FIT":
        return _deny("DENY_NOT_FIT_PUBLIC_INPUT")
    if not p.shared_noise_claim:
        return _deny("DENY_INDEPENDENT_NOISE_NOT_EPISODE_COUNTERFACTUAL")
    observed = set(p.fields)
    if len(p.fields) != len(observed):
        return _deny("DENY_DUPLICATE_MODEL_INPUT_FIELD")
    if observed & HIDDEN or not observed.issubset(ALLOWED) or observed != ALLOWED:
        return _deny("DENY_HIDDEN_OR_UNMATCHED_MODEL_INPUT")
    if p.query_encoding != "index/T":
        return _deny("DENY_RELEASE_QUERY_TIME_ENCODING_MISMATCH")
    if any(type(x) is not int for x in (p.length, p.intervention_onset,
                                        p.prefix_stop, p.query_row)):
        return _deny("DENY_NONINTEGER_OR_BOOLEAN_TIME")
    if not (1 < p.length and 0 <= p.intervention_onset < p.length
            and 0 <= p.prefix_stop <= p.intervention_onset
            and p.intervention_onset <= p.query_row < p.length):
        return _deny("DENY_FUTURE_OBSERVATION_OR_TIME_DRIFT")
    if p.structure == "mediator" and p.query_row <= p.intervention_onset:
        return _deny("DENY_MEDIATOR_QUERY_BEFORE_LAGGED_EFFECT")
    if p.query_kind != "post_treatment":
        return _deny("DENY_SELF_QUERY_OR_UNSUPPORTED_EVALUATION")
    if p.structure not in ("back_door", "observed_confounder", "confounder_mediator",
                          "front_door", "mediator", "instrumental_variable",
                          "bi_variate", "unobserved_confounder", "bow_graph"):
        return _deny("DENY_UNKNOWN_CAUSAL_STRUCTURE")
    if p.structure == "bow_graph" and p.model_counterfactual_claim:
        return _deny("DENY_OBSERVATION_ONLY_NONIDENTIFIED_CAUSAL_CLAIM")
    if p.exact_download_sha256 is not None:
        if len(p.exact_download_sha256) != 64 or any(c not in "0123456789abcdef"
                                                    for c in p.exact_download_sha256):
            return _deny("DENY_INVALID_DOWNLOAD_DIGEST")
    # These are caller claims; the validator cannot independently corroborate
    # the provider record, bytes, exogeneity, prior use or independent witness.
    if not (p.provider_manifest_pinned and p.actual_pairing_raw_verified
            and p.independent_custody and p.exact_download_sha256):
        status = "PUBLIC_MODEL_INTERFACE_ONLY_PROVIDER_UNVERIFIED"
    else:
        status = "CLAIMED_CUSTODY_REQUIRES_EXTERNAL_INDEPENDENT_AUTHORITY"
    out = _deny(status, provenance_only=True)
    out["model_interface_screen_pass"] = True
    out["release"] = "dot-Identifiability-v1@1.2.0"
    return out
