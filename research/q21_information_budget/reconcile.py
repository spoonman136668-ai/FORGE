"""Read-only Q21 Windows/Linux DEV evidence reconciliation.

Never generates source rows, fits models, dispatches work, accepts scientific
first use, or grants CKB-plane authority. Caller-supplied receipts are not
authenticated by comparing them: controller custody remains independently
required. No protected original/held cohort can be accessed here.
"""
from __future__ import annotations

import math
import re

import evaluator as ev
import sourcefree as src

SCHEMA = "forge.q21.cross_os_development_receipt.v1"
RESOURCE_SCHEMA = "forge.q21.native-resource-census.v1"
SHA_PATTERN = re.compile(r"[0-9a-f]{64}\Z")
GIT_SHA_PATTERN = re.compile(r"[0-9a-f]{40}\Z")
TOLERANCE = 1e-6  # Prospective frozen Q21 cross-OS NLL tolerance.


def need(ok, code):
    if not ok:
        raise ValueError("Q21_REPLAY_" + code)


def finite(value, code, *, positive=False):
    need(type(value) in (int, float) and math.isfinite(value), code)
    need(value > 0 if positive else value >= 0, code)
    return value


def sha(value, code, *, git=False):
    pat = GIT_SHA_PATTERN if git else SHA_PATTERN
    need(type(value) is str and pat.fullmatch(value) is not None, code)
    return value


def _resource(result, platform):
    need(result.get("native_peak_rss_measured") is True,
         "NATIVE_RSS_MEASURED_REQUIRED")
    # This is a measurement, never a verified isolated model-memory advantage.
    need(result.get("native_peak_rss_qualified") is False,
         "FORGED_RESOURCE_QUALIFICATION")
    cost = result.get("native_resource_census")
    need(type(cost) is dict and cost.get("schema") == RESOURCE_SCHEMA,
         "RESOURCE_CENSUS_REQUIRED")
    need(cost.get("scientific_qualification") ==
         "NOT_AUTHORIZED_BY_RESOURCE_CENSUS", "FALSE_SCIENTIFIC_AUTHORITY")
    need(cost.get("rss_scope") ==
         "CUMULATIVE_PROCESS_HIGH_WATER_NOT_ISOLATED_MODEL",
         "UNJUSTIFIED_ISOLATED_RSS")
    cpu = 0.
    max_peak = 0
    for field in ("source_generation", "generation_to_evaluation_handoff",
                  "fit_dev_oracle_bootstrap"):
        stage = cost.get(field)
        need(type(stage) is dict and stage.get("schema") ==
             "forge.q21.native-process-resource.v1", "STAGE_RECEIPT_MISSING")
        need(stage.get("platform") == platform, "NATIVE_PLATFORM_DRIFT")
        need(stage.get("rss_scope") ==
             "CUMULATIVE_PROCESS_HIGH_WATER_NOT_ISOLATED_STAGE",
             "STAGE_RSS_NOT_CUMULATIVE")
        cpu += finite(stage.get("process_cpu_seconds"), "NONFINITE_STAGE_CPU")
        peak = finite(stage.get("process_peak_rss_bytes"), "INVALID_STAGE_RSS",
                      positive=True)
        max_peak = max(max_peak, peak)
        need(finite(stage.get("start_process_peak_rss_bytes"),
                    "INVALID_STAGE_START_RSS", positive=True) <= peak,
             "NONMONOTONIC_PEAK_RSS")
        io = stage.get("io")
        need(type(io) is dict and type(stage.get("io_measurement_source")) is str,
             "IO_PROVENANCE_MISSING")
        for key in ("read_transfer_bytes", "write_transfer_bytes"):
            finite(io.get(key), "IO_TRANSFER_MISSING")
        for key in ("disk_read_bytes", "disk_write_bytes"):
            if io.get(key) is None:
                need(platform == "Windows", "LINUX_DISK_IO_MISSING")
            else:
                finite(io[key], "INVALID_DISK_IO")
    need(abs(finite(cost.get("total_process_cpu_seconds"),
                    "TOTAL_CPU_INVALID") - cpu) <= 1e-8,
         "TOTAL_CPU_MISMATCH")
    need(cost.get("process_peak_rss_bytes") == max_peak,
         "PEAK_RSS_AGGREGATE_MISMATCH")
    transport = cost.get("adapter_transport")
    need(type(transport) is dict and
         transport.get("adapter_mode") in ("none", "measured"),
         "TRANSPORT_MEASUREMENT_UNDECLARED")
    finite(transport.get("wire_bytes"), "WIRE_BYTES_MISSING")
    finite(transport.get("adapter_bytes"), "ADAPTER_BYTES_MISSING")
    if transport["adapter_mode"] == "none":
        need(transport["wire_bytes"] == transport["adapter_bytes"] == 0,
             "FAKE_NO_TRANSPORT")
    inp = cost.get("public_input_serialization")
    need(type(inp) is dict and inp.get("encoding") == "canonical_json_utf8",
         "PUBLIC_PAYLOAD_MEASUREMENT_MISSING")
    finite(inp.get("serialized_bytes"), "PUBLIC_PAYLOAD_BYTES_MISSING",
           positive=True)
    sha(inp.get("serialized_sha256"), "PUBLIC_PAYLOAD_SHA_INVALID")
    finite(cost.get("all_seven_model_serialized_checkpoint_bytes"),
           "MODEL_BYTES_MISSING", positive=True)
    need(cost.get("checkpoint_persisted_bytes") ==
         "NOT_MEASURED_NO_PERSISTENCE_CLAIM",
         "UNVERIFIED_PERSISTENCE_CLAIM")
    return cost


def _family(report, family, platform):
    need(type(report) is dict and report.get("family") == family,
         "FAMILY_IDENTITY_DRIFT")
    need(report.get("protected_scientific_first_use") is False,
         "PROTECTED_FIRST_USE_CLAIM")
    hashes = report.get("role_sha256")
    need(type(hashes) is dict and set(hashes) == src.ROLES,
         "ROLE_COHORT_CUSTODY_MISSING")
    for role in src.ROLES:
        sha(hashes[role], "ROLE_DIGEST_INVALID")
    need(len(set(hashes.values())) == len(src.ROLES),
         "ROLE_DIGEST_COLLISION")
    arms = report.get("arm_results")
    need(type(arms) is dict and set(arms) == set(ev.ARM_NAMES),
         "SEVEN_ARM_INVENTORY_DRIFT")
    losses = {}
    checkpoint_hashes = {}
    checkpoint_bytes = 0
    for name in ev.ARM_NAMES:
        arm = arms[name]
        need(type(arm) is dict and type(arm.get("fit_cost")) is dict and
             type(arm.get("result")) is dict, "ARM_RECEIPT_MISSING")
        fit, outcome = arm["fit_cost"], arm["result"]
        finite(fit.get("fit_validation_nll"), "FIT_VALID_MISSING")
        cb = finite(fit.get("checkpoint_bytes"), "CHECKPOINT_BYTES_MISSING",
                    positive=True)
        checkpoint_bytes += cb
        checkpoint_hashes[name] = sha(fit.get("checkpoint_sha256"),
                                      "CHECKPOINT_SHA_MISSING")
        values = outcome.get("episode_nll")
        need(type(values) is list and
             len(values) == src.ROLE_COUNTS["DEV"],
             "DEV_EPISODE_CLUSTER_COUNT_DRIFT")
        for value in values:
            finite(value, "INVALID_EPISODE_LOSS")
        mean = finite(outcome.get("mean_nll"), "INVALID_MEAN_NLL")
        need(abs(mean - sum(values) / len(values)) <= 1e-9,
             "MEAN_VS_EPISODE_LOSS_DRIFT")
        losses[name] = mean
    need(report.get("best_current") ==
         ev.select_pre_dev_arm(arms, ev.MEMORYLESS) and
         report.get("best_history") ==
         ev.select_pre_dev_arm(arms, ev.HISTORY),
         "POSTHOC_DEV_ARM_SELECTION")
    gain = report.get("gain")
    need(type(gain) is dict and
         gain.get("resampling_unit") == "EPISODE" and
         gain.get("replicates") == 2048, "BOOTSTRAP_CONTRACT_DRIFT")
    for key in ("gain_nats_per_bit", "lower_95", "upper_95"):
        need(type(gain.get(key)) in (float, int) and
             math.isfinite(gain[key]), "BOOTSTRAP_NONFINITE")
    need(gain["lower_95"] <= gain["upper_95"], "BOOTSTRAP_ORDER_DRIFT")
    expected_gain = losses[report["best_current"]] - losses[report["best_history"]]
    need(abs(gain["gain_nats_per_bit"] - expected_gain) <= 1e-8,
         "GAIN_VS_SELECTED_ARM_DRIFT")
    oracle = finite(report.get("privileged_oracle_nll"),
                    "ORACLE_NLL_MISSING")
    need(report.get("oracle_is_not_matched_comparator") is True,
         "PRIVILEGED_ORACLE_MISLABELED")
    need(abs(report.get("public_oracle_headroom", math.nan) -
             (losses[report["best_current"]] - oracle)) <= 1e-8,
         "ORACLE_HEADROOM_DRIFT")
    cost = _resource(report, platform)
    need(cost["all_seven_model_serialized_checkpoint_bytes"] ==
         checkpoint_bytes, "MODEL_BYTE_TOTAL_DRIFT")
    return {"role_sha256": hashes, "arm_mean_nll": losses,
            "checkpoint_sha256": checkpoint_hashes, "gain": gain,
            "privileged_oracle_nll": oracle,
            "public_oracle_headroom": report["public_oracle_headroom"],
            "public_input_sha256":
                cost["public_input_serialization"]["serialized_sha256"]}


def compare(windows, linux, doc):
    """Compare two externally supplied DEV receipts, never accept the science."""
    need(doc["schema"] == src.SCHEMA, "FROZEN_PROTOCOL_SCHEMA_DRIFT")
    validated = {}
    for name, receipt in (("Windows", windows), ("Linux", linux)):
        need(type(receipt) is dict and receipt.get("schema") == SCHEMA,
             "RECEIPT_SCHEMA_MISSING")
        need(receipt.get("os_name") == name, "CROSS_OS_PROVENANCE_DRIFT")
        need(receipt.get("protocol_git_blob") == src.PROTOCOL_BLOB,
             "FROZEN_PROTOCOL_DRIFT")
        sha(receipt.get("candidate_source_sha"), "SOURCE_IDENTITY_MISSING",
            git=True)
        need(receipt.get("protected_scientific_first_use") is False,
             "PROTECTED_SCIENCE_CONSUMPTION")
        reports = receipt.get("by_family")
        need(type(reports) is dict and set(reports) == set(src.FAMILIES),
             "THREE_FAMILY_INVENTORY_DRIFT")
        validated[name] = {
            family: _family(reports[family], family, name)
            for family in src.FAMILIES
        }
    need(windows["candidate_source_sha"] == linux["candidate_source_sha"],
         "CANDIDATE_SOURCE_DRIFT")
    different_checkpoints = []
    for family in src.FAMILIES:
        a, b = validated["Windows"][family], validated["Linux"][family]
        need(a["role_sha256"] == b["role_sha256"] and
             a["public_input_sha256"] == b["public_input_sha256"],
             "INDEPENDENT_COHORT_DIGEST_MISMATCH")
        for key in ("gain_nats_per_bit", "lower_95", "upper_95"):
            need(abs(a["gain"][key] - b["gain"][key]) <= TOLERANCE,
                 "BOOTSTRAP_NUMERICAL_DRIFT")
        for key in ("privileged_oracle_nll", "public_oracle_headroom"):
            need(abs(a[key] - b[key]) <= TOLERANCE,
                 "ORACLE_NUMERICAL_DRIFT")
        for arm in ev.ARM_NAMES:
            need(abs(a["arm_mean_nll"][arm] - b["arm_mean_nll"][arm]) <=
                 TOLERANCE, "MODEL_NUMERICAL_DRIFT")
            if a["checkpoint_sha256"][arm] != b["checkpoint_sha256"][arm]:
                different_checkpoints.append(family + ":" + arm)
    pre = ev.preliminary_decision(windows["by_family"], doc)
    pre_linux = ev.preliminary_decision(linux["by_family"], doc)
    need(pre["q21_development_thresholds_met"] ==
         pre_linux["q21_development_thresholds_met"] and
         pre["per_real_family_meets_thresholds"] ==
         pre_linux["per_real_family_meets_thresholds"],
         "CROSS_OS_SCIENTIFIC_DECISION_DRIFT")
    need(pre["ckb_scientific_acceptance"] == "NOT_AUTHORIZED" and
         pre_linux["ckb_scientific_acceptance"] == "NOT_AUTHORIZED",
         "UNEXPECTED_ACCEPTANCE")
    return {
        "schema": "forge.q21.readonly_cross_os_reconciliation.v1",
        "candidate_source_sha": windows["candidate_source_sha"],
        "protocol_git_blob": src.PROTOCOL_BLOB,
        "matching_reported_public_cohort_digests": True,
        "numerical_agreement_within_frozen_tolerance": True,
        "matching_reported_checkpoint_hashes": not bool(different_checkpoints),
        "checkpoint_hash_divergences": different_checkpoints,
        "per_family_development_thresholds_met":
            pre["per_real_family_meets_thresholds"],
        "q21_dev_threshold_signal": pre["q21_development_thresholds_met"],
        "advisory_disposition":
            "INDEPENDENT_CKB_CUSTODY_AND_SCIENTIFIC_REVIEW_REQUIRED",
        "original_scientific_first_use": "NOT_PERFORMED",
        "execution_authority": "NONE",
    }
