"""LCRM01-G source-free public temporal-intervention provenance screen.

No data download, source birth, model training, first-use or counterfactual admission.
Published metadata is NOT an independent witness. This is a strict gate for
identifying eligible public development leads, not a scientific execution permit.
"""
from __future__ import annotations
from dataclasses import dataclass

UPSTREAM_REPO = "thummd/dotime"
UPSTREAM_COMMIT = "0b7833a1d8c1b945a89bc4118b54795ed979c420"
UPSTREAM_TREE = "cb390c791d82b79d381669302febf1f2f8426488"
UPSTREAM_BENCHMARK_BLOB = "23371578576f4bb78cca9f284d1ed212b8991b90"
RELEASES = {
    "1.0.0": ("20919553", 10800, "independent_noise"),
    "1.1.0": ("22673322", 10800, "shared_noise"),
    "1.2.0": ("23095083", 12150, "shared_noise"),
}
DATASET = "dot-Identifiability-v1"

@dataclass(frozen=True)
class PublicMetadata:
    repository: str
    commit: str
    tree: str
    bench_blob: str
    dataset: str
    version: str
    zenodo_record: str
    episode_count: int
    pair_mode: str
    provider_sha256: str | None = None
    independent_source_witness: str | None = None
    source_family: str = "back_door"
    model_public_inputs_include_hidden_graph: bool = False
    model_public_inputs_include_future_outcome: bool = False
    observed_pre_do_equal: bool | None = None
    raw_manifest_independently_verified: bool = False


def candidate(version="1.2.0", **changes):
    """Static GitHub-source-described *metadata*, not retrieved dataset values."""
    from dataclasses import replace
    rec, n, mode = RELEASES[version]
    base = PublicMetadata(UPSTREAM_REPO, UPSTREAM_COMMIT, UPSTREAM_TREE,
                          UPSTREAM_BENCHMARK_BLOB, DATASET, version, rec, n, mode)
    return replace(base, **changes)


def screen(m: PublicMetadata) -> dict:
    """No metadata combination can grant execution or first use."""
    all_versions = tuple(RELEASES)
    result = {"schema": "mass.lcrm01.g.readonly-source-screen.v1",
              "source_class": "BIBLIOGRAPHIC_NOT_INDEPENDENT_AUTHORITY",
              "original_scientific_firstuse_consumed": 0,
              "scientific_source_admitted": False,
              "counterfactual_execution_authorized": False,
              "controller_dispatch_authorized": False,
              "selected_release": m.version,
              "allowed_versions": list(all_versions)}
    def decline(status):
        return dict(result, status=status)
    if (m.repository != UPSTREAM_REPO or m.commit != UPSTREAM_COMMIT
            or m.tree != UPSTREAM_TREE or m.bench_blob != UPSTREAM_BENCHMARK_BLOB
            or m.dataset != DATASET or m.version not in RELEASES):
        return decline("DENY_SOURCE_OR_VERSION_PIN_MISMATCH")
    expected_rec, expected_count, expected_pair = RELEASES[m.version]
    if ((m.zenodo_record, m.episode_count, m.pair_mode)
            != (expected_rec, expected_count, expected_pair)):
        return decline("DENY_RELEASE_METADATA_MISMATCH")
    if m.model_public_inputs_include_hidden_graph or m.model_public_inputs_include_future_outcome:
        return decline("DENY_HIDDEN_SCM_OR_FUTURE_OUTCOME_LEAKAGE")
    if m.version == "1.0.0":
        return decline("DENY_INDEPENDENT_NOISE_TWINS_ARE_NOT_EPISODE_COUNTERFACTUALS")
    if m.source_family == "bow_graph" and m.version != "1.2.0":
        return decline("DENY_FAMILY_NOT_RELEASED_IN_VERSION")
    if m.source_family not in ("back_door", "front_door", "mediator", "bow_graph",
                               "instrumental_variable", "bi_variate", "unobserved_confounder",
                               "observed_confounder", "confounder_mediator"):
        return decline("DENY_UNSUPPORTED_STRUCTURE")
    if m.observed_pre_do_equal is False:
        return decline("DENY_PRE_INTERVENTION_PAIRING_VIOLATION")
    if not m.provider_sha256 or not m.independent_source_witness or not m.raw_manifest_independently_verified:
        return decline("PUBLIC_METADATA_ONLY_RAW_SOURCE_CUSTODY_NOT_VERIFIED")
    if len(m.provider_sha256) != 64 or any(c not in "0123456789abcdef" for c in m.provider_sha256):
        return decline("DENY_INVALID_PROVIDER_DIGEST_FORMAT")
    if m.observed_pre_do_equal is not True:
        return decline("DENY_SHARED_NOISE_PAIRING_NOT_VERIFIED_IN_RAW_BYTES")
    if m.source_family == "bow_graph":
        return decline("NONIDENTIFIED_BOW_GRAPH_OBSERVATION_ONLY_ABSTENTION_REQUIRED")
    # No self-supplied 'validated' booleans can prove trusted custody and source
    # first-use. A separate independent CKB-plane authority must be consulted.
    return decline("INDEPENDENT_CUSTODY_AND_FIRSTUSE_REVIEW_REQUIRED")


def source_only_record():
    return {"schema": "mass.lcrm01.g.readonly-qualification.v1",
            "unverified_release_screen": {v:screen(candidate(v))["status"] for v in RELEASES},
            "firstuse_consumed": 0,
            "public_dataset_downloaded": False,
            "actual_provider_bytes_inspected": False,
            "scientific_transfer_proven": False}
