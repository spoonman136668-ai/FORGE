"""LCRM01-F read-only public source triage, not scientific source-birth.

A published GitHub commit or a dataset intervention label is not a signed
experiment, exogenous assignment, paired counterfactual, or temporal history.
This program never emits a scientific admission or first-use authorization.
"""
from __future__ import annotations
from dataclasses import dataclass

UPSTREAM_CODE_COMMIT = "1a2143cffdc85f835b41ce8d52034be1bf903e71"
UPSTREAM_DOWNLOAD_SPEC_BLOB = "a8cfbdcaec069da45fcb105e0f20cbed59202cf7"
FORGE_SOURCEBIRTH_BLOB = "1b034313880086a239ecd552373658d030cb862d"
BENCHMARKS = {
    "k562": "https://plus.figshare.com/ndownloader/files/35773219",
    "rpe1": "https://plus.figshare.com/ndownloader/files/35775606",
}

@dataclass(frozen=True)
class SourceMetadata:
    repository: str
    code_commit: str
    download_spec_blob: str
    dataset_key: str
    download_url: str
    producer_perturbation_labels: bool = False
    provider_payload_digest: str | None = None
    independent_witness_identity: str | None = None
    verified_exogenous_assignment: bool = False
    paired_counterfactual_truth: bool = False
    ordered_entity_intervention_episodes: bool = False


def inspect(candidate: SourceMetadata) -> dict[str, object]:
    """Screen bibliographic provenance, not downloaded data or valid custody."""
    expected_url = BENCHMARKS.get(candidate.dataset_key)
    pinned = (candidate.repository == "causalbench/causalbench"
              and candidate.code_commit == UPSTREAM_CODE_COMMIT
              and candidate.download_spec_blob == UPSTREAM_DOWNLOAD_SPEC_BLOB
              and expected_url is not None and candidate.download_url == expected_url)
    if not pinned:
        level, reason = "REJECT", "EXTERNAL_CODE_IDENTITY_OR_UPSTREAM_URL_MISMATCH"
    elif not candidate.producer_perturbation_labels:
        level, reason = "REJECT", "NO_SOURCE_DESCRIBED_INTERVENTION_TARGET"
    elif not candidate.provider_payload_digest or not candidate.independent_witness_identity:
        level, reason = "BIBLIOGRAPHIC_ONLY", "RAW_PAYLOAD_AND_INDEPENDENT_CUSTODY_UNVERIFIED"
    elif not candidate.verified_exogenous_assignment:
        level, reason = "DOCUMENTED_PERTURBATION_ONLY", "EXOGENOUS_ASSIGNMENT_UNVERIFIED"
    elif not candidate.ordered_entity_intervention_episodes:
        level, reason = "NONSEQUENTIAL_INTERVENTION_ONLY", "NO_ORDERED_ENTITY_CAUSAL_EPISODES"
    elif not candidate.paired_counterfactual_truth:
        level, reason = "SEQUENCE_BUT_NOT_COUNTERFACTUAL", "NO_PAIRED_COUNTERFACTUAL_TRUTH"
    else:
        # Caller-provided strings and booleans cannot constitute independent
        # crypto attestation. Never convert these into scientific admission.
        level, reason = "AUTHORITY_REVIEW_REQUIRED", "CLAIMS_NOT_CRYPTOGRAPHICALLY_VERIFIED_HERE"
    return {"level":level, "reason":reason,
            "code_provenance_pinned":pinned,
            "original_scientific_source_admitted":False,
            "scientific_firstuse_consumed":0,
            "counterfactual_claim_authorized":False,
            "controller_dispatch_authorized":False}


def sourcebirth_scope() -> dict[str, object]:
    """Bounded assessment of exact reviewed FORGE sourcebirth verifier."""
    return {"reviewed_go_blob":FORGE_SOURCEBIRTH_BLOB,
            "recognized_sourcebirth_lanes":["Wingless","Yggdrasil"],
            "recognizes_LCRM01_sourcebirth_lane":False,
            "signed_statement_includes_do_assignment_fields":False,
            "signed_statement_includes_causal_design_attestation":False,
            "cryptographic_birthing_implies_intervention_authenticity":False,
            "independent_original_science_accepted":False}
