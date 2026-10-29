"""F139 V19 G33: inert, version-distinct owner/provider signature contract.

READ-ONLY schema verifier, NOT a V1/V2 worker, signer, dispatcher, GitHub
writer, SQLite consumer, or production native qualification. Neither the
original owner signing key nor independent provider keys are installed here.
A valid *fixture* demonstrates rejection behavior, not actual live signatures.

HMAC verifier inputs would have to be independently provisioned and bound to
original owner custody before any new original-owner contract were eligible.
"""
from __future__ import annotations
import hashlib
import hmac
import json
import re

SCHEMA = "forge.f139.v19.g33.readonly-signature-contract.v1"
OWNER = "forge.f139.v19.g33.original-owner-admission.v1"
PROVIDER = "forge.f139.v19.g33.provider-development-report.v1"
SOURCE = "0743ca22b76ebd943a66f05a36ea919301676be0"
TARGET_COMMIT = "021423311027517c9096c76bed7d35ac53c4a229"
TARGET_TREE = "93620bd8e46bfbae1dbcd8e4ce397e27044de4f1"
NATIVE_PATH = "yggdrasil/public_causal_cells.py"
G32_SCHEMA = "forge.f139.v19.g32.github-diagnostic-artifact-custody.v1"
ORIGINAL_FAILED_ISSUE = 1138
ORIGINAL_FAILED_RUN = 40861987373
ORIGINAL_TERMINAL_SEQ = 322
DIAGNOSTIC_RUN = 40885501321
RUNNER_OSES = ("ubuntu-latest", "windows-latest")
SHA64 = re.compile(r"[a-f0-9]{64}\Z")
SIGNED = frozenset(("binding", "hmac_sha256"))
OWNER_FIELDS = frozenset((
    "schema", "ticket", "owner_source_sha", "owner_epoch",
    "original_event_seq", "original_event_sha256", "issue_number",
    "issue_id", "native_intent_sha256", "qualification_key",
    "target_commit", "target_tree", "path",
    "candidate_after_sha256", "provider_run_id", "development_only",
    "scientific_first_use", "paid_model_calls", "accepted_ref_mutations"))
PROVIDER_FIELDS = frozenset((
    "schema", "ticket", "owner_source_sha", "owner_event_sha256",
    "native_intent_sha256", "qualification_key", "target_commit",
    "target_tree", "path", "candidate_after_sha256", "provider_run_id",
    "provider_job_id", "runner_os", "artifact_sha256",
    "baseline_g29_pass_count", "baseline_full_pass_count",
    "candidate_g29_expected_negative_count",
    "candidate_applicable_test_count", "candidate_test_module_count",
    "candidate_compiled", "child_cpu_measured", "child_rss_measured",
    "resource_budget_enforced", "native_qualified",
    "scientific_first_use", "accepted_ref_mutations", "paid_model_calls"))
OWNER_DOMAIN = b"FORGE-F139-V19-G33-OWNER\x00"
PROVIDER_DOMAIN = b"FORGE-F139-V19-G33-PROVIDER\x00"


class G33Denied(ValueError):
    pass


def require(value, code):
    if not value:
        raise G33Denied("F139_V19_G33_" + code)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True).encode("ascii")


def validate_key(key):
    require(type(key) is bytes and 32 <= len(key) <= 4096, "KEY_INVALID")
    return key


def verify_mac(envelope, fields, schema, domain, key):
    require(type(envelope) is dict and set(envelope) == SIGNED,
            "SIGNED_ENVELOPE_FIELDS_INVALID")
    binding, mac = envelope["binding"], envelope["hmac_sha256"]
    require(type(binding) is dict and set(binding) == fields
            and binding["schema"] == schema
            and type(mac) is str and SHA64.fullmatch(mac) is not None,
            "SIGNED_BINDING_OR_VERSION_INVALID")
    actual = hmac.new(validate_key(key), domain + canonical(binding),
                      hashlib.sha256).hexdigest()
    require(hmac.compare_digest(mac, actual), "SIGNATURE_MISMATCH")
    return binding


def require_sha(value, code):
    require(type(value) is str and SHA64.fullmatch(value) is not None, code)


def positive(value):
    return type(value) is int and value > 0


def check_g32(g32):
    require(type(g32) is dict and g32.get("schema") == G32_SCHEMA
            and g32.get("source_run_id") == DIAGNOSTIC_RUN
            and g32.get("git_authenticated_metadata_download_required") is True
            and g32.get("original_artifact_ids") ==
                {"linux": 12900619626, "windows": 12901923435}
            and g32.get("original_zip_sha256") == {
                "linux": "4cd4bf9a236dff693e35173e2c4774b6a0cf6abf0cfc2d6724903ab6e21a5c19",
                "windows": "8f47dae9acc904d778aea5874795b11d92f8d1ec2feb5aee2834f43dd4d0e15e"}
            and g32.get("provider_receipt_signed") is False
            and g32.get("original_owner_consumed") is False
            and g32.get("native_qualified") is False
            and g32.get("full_native_worker_regression_qualified") is False
            and g32.get("production_release_authorized") is False
            and g32.get("scientific_first_use") is False
            and type(g32.get("diagnostic")) is dict
            and g32["diagnostic"].get("windows_historical_regression") ==
                "NEGATIVE_RETAINED"
            and g32["diagnostic"].get("native_qualified") is False
            and g32["diagnostic"].get("signed_provider_success") is False,
            "HISTORICAL_G32_NEGATIVE_ORIGIN_INVALID")


def verify_contract(g32, owner, providers, provenance, *, owner_key, provider_keys):
    """Validate *synthetic* signature/provenance protocol. Never grant release.

    The caller must authenticate GitHub job/ZIP and original SQLite separately.
    An HMAC-positive fixture is NOT proof such upstream custody exists.
    """
    check_g32(g32)
    require(type(provider_keys) is dict
            and set(provider_keys) == set(RUNNER_OSES)
            and all(validate_key(x) for x in provider_keys.values())
            and len({owner_key, *provider_keys.values()}) == 3,
            "INDEPENDENT_KEYS_REQUIRED")
    o = verify_mac(owner, OWNER_FIELDS, OWNER, OWNER_DOMAIN, owner_key)
    for name in ("native_intent_sha256", "qualification_key",
                 "original_event_sha256", "candidate_after_sha256"):
        require_sha(o[name], "OWNER_HASH_INVALID")
    require(o["owner_source_sha"] == SOURCE
            and o["target_commit"] == TARGET_COMMIT
            and o["target_tree"] == TARGET_TREE
            and o["path"] == NATIVE_PATH
            and type(o["owner_epoch"]) is int and o["owner_epoch"] > 0
            and type(o["original_event_seq"]) is int
            and o["original_event_seq"] > ORIGINAL_TERMINAL_SEQ
            and positive(o["issue_number"])
            and o["issue_number"] > ORIGINAL_FAILED_ISSUE
            and positive(o["issue_id"])
            and positive(o["provider_run_id"])
            and o["provider_run_id"] not in (ORIGINAL_FAILED_RUN, DIAGNOSTIC_RUN)
            and o["ticket"] ==
                "f139-nci04-i" + str(o["issue_number"]) + "-" +
                SOURCE[:12] + "-" + o["native_intent_sha256"][:8]
            and o["development_only"] is True
            and o["scientific_first_use"] is False
            and type(o["paid_model_calls"]) is int and o["paid_model_calls"] == 0
            and type(o["accepted_ref_mutations"]) is int
            and o["accepted_ref_mutations"] == 0,
            "OWNER_ADMISSION_OR_REPLAY_INVALID")
    require(type(providers) is list and len(providers) == 2
            and type(provenance) is dict
            and set(provenance) == set(RUNNER_OSES),
            "PROVIDER_INVENTORY_INVALID")
    os_seen, jobs, artifacts = set(), set(), set()
    for envelope in providers:
        require(type(envelope) is dict and type(envelope.get("binding")) is dict,
                "PROVIDER_FORMAT_INVALID")
        osname = envelope["binding"].get("runner_os")
        require(osname in RUNNER_OSES and osname not in os_seen,
                "PROVIDER_OS_DUPLICATE_OR_INVALID")
        p = verify_mac(envelope, PROVIDER_FIELDS, PROVIDER,
                       PROVIDER_DOMAIN + osname.encode("ascii") + b"\x00",
                       provider_keys[osname])
        for field in ("owner_event_sha256", "native_intent_sha256",
                      "qualification_key", "candidate_after_sha256",
                      "artifact_sha256"):
            require_sha(p[field], "PROVIDER_HASH_INVALID")
        for field in ("ticket", "owner_source_sha", "native_intent_sha256",
                      "qualification_key", "target_commit", "target_tree",
                      "path", "candidate_after_sha256", "provider_run_id"):
            require(p[field] == o[field], "CROSS_SIGNATURE_BINDING_MISMATCH")
        require(p["owner_event_sha256"] == o["original_event_sha256"]
                and positive(p["provider_job_id"]) and
                p["provider_job_id"] not in jobs and
                p["artifact_sha256"] not in artifacts,
                "PROVIDER_JOB_OR_ARTIFACT_REPLAY")
        evidence = provenance[osname]
        require(type(evidence) is dict and set(evidence) ==
                {"repository", "run_id", "job_id", "runner_os",
                 "artifact_sha256", "run_attempt", "conclusion",
                 "source_sha", "authenticated_from_github"},
                "PROVIDER_INDEPENDENT_EVIDENCE_FIELDS_INVALID")
        require(evidence == {
            "repository": "spoonman136668-ai/FORGE",
            "run_id": o["provider_run_id"], "job_id": p["provider_job_id"],
            "runner_os": osname, "artifact_sha256": p["artifact_sha256"],
            "run_attempt": 1, "conclusion": "success", "source_sha": SOURCE,
            "authenticated_from_github": True},
            "PROVIDER_INDEPENDENT_EVIDENCE_MISMATCH")
        require(type(p["baseline_g29_pass_count"]) is int
                and p["baseline_g29_pass_count"] == 4
                and positive(p["baseline_full_pass_count"])
                and positive(p["candidate_g29_expected_negative_count"])
                and p["candidate_g29_expected_negative_count"] == 2
                and positive(p["candidate_applicable_test_count"])
                and type(p["candidate_test_module_count"]) is int
                and p["candidate_test_module_count"] >= 4
                and p["candidate_compiled"] is True
                and p["child_cpu_measured"] is True
                and p["child_rss_measured"] is True
                and p["resource_budget_enforced"] is True
                and p["native_qualified"] is True
                and p["scientific_first_use"] is False
                and type(p["accepted_ref_mutations"]) is int
                and p["accepted_ref_mutations"] == 0
                and type(p["paid_model_calls"]) is int
                and p["paid_model_calls"] == 0,
                "POSITIVE_RESOURCE_OR_REGRESSION_EVIDENCE_MISSING")
        os_seen.add(osname)
        jobs.add(p["provider_job_id"])
        artifacts.add(p["artifact_sha256"])
    require(os_seen == set(RUNNER_OSES), "PROVIDER_BOTH_OSES_REQUIRED")
    return {
        "schema": SCHEMA, "signature_contract_fixtures_valid": True,
        "distinct_owner_and_provider_keys": True,
        "signed_envelope_semantics_v3": True,
        "historical_g32_negative_preserved": True,
        "candidate_signed_real_provider_proof": False,
        "actual_original_sqlite_owner_signature_verified": False,
        "genuine_provider_zip_verified": False,
        "native_qualified": False,
        "original_owner_consumed": False,
        "production_release_authorized": False,
        "scientific_first_use": False,
    }


def inspect_real_g32_pair(linux, windows):
    """Read immutable G32 reports only; source origin must be Actions-verified."""
    check_g32(linux)
    check_g32(windows)
    require(linux == windows, "TWO_HOST_G32_DIAGNOSTIC_DIFFERENCE")
    return {"schema": SCHEMA,
            "g32_read_only_report_pair_equal": True,
            "g32_historical_negative_preserved": True,
            "signed_live_provider": False,
            "signed_live_original_owner": False,
            "production_release_authorized": False}
