"""ACC-118 bounded FIT/DEV comparison of already frozen arms.

Run: python -B research/acc95_u24/compare_fitdev.py
Output is diagnostic-only JSON (no reserved TEST, no model admission).
Raw prediction custody, complete CPU/RSS/energy accounting and fitted recurrent
control are still MISSING. No statistical superiority claim is permitted.
"""
from __future__ import annotations
import hashlib
import json
import sys
import time

from fitdev import FIT_RULES, FIT_SEEDS, DEV_RULES, DEV_SEEDS
from switching import switching_trace, evaluate_count_table
from ewma import RATES, evaluate_ewma
from interacting_cells import evaluate as evaluate_connected

SCHEMA = "forge.acc118.u24.fitdev-comparison.v1"
ARMS = ("count_carry",) + tuple("ewma_" + str(rate) for rate in RATES) + (
    "connected", "disabled", "shuffled"
)
NO_SCIENCE = "CONTROL_INCOMPLETE_RESOURCE_UNVERIFIED"


def run_one(trace, arm):
    if arm == "count_carry":
        return evaluate_count_table(trace)
    if arm.startswith("ewma_"):
        return evaluate_ewma(trace, float(arm[5:]))
    return evaluate_connected(trace, arm)


def screen():
    cases = []
    for split, rules, seeds, widths in (
        ("FIT", FIT_RULES, FIT_SEEDS, (25, 63)),
        ("DEV", DEV_RULES, DEV_SEEDS, (127,)),
    ):
        for rule in rules:
            for seed in seeds:
                for width in widths:
                    trace = switching_trace(split, rule, seed, width=width)
                    if trace["reserved_test_used"] or trace["split"] != split:
                        raise RuntimeError("RESERVED_TEST_OR_SPLIT_DRIFT")
                    row = {"split": split, "first_rule": rule, "seed": seed,
                           "width": width, "trace_sha256": trace["trace_sha256"],
                           "arms": {}}
                    for arm in ARMS:
                        start_cpu = time.process_time_ns()
                        start_wall = time.perf_counter_ns()
                        result = run_one(trace, arm)
                        wall_ns = time.perf_counter_ns() - start_wall
                        cpu_ns = time.process_time_ns() - start_cpu
                        if result["phase_queries"] != [128 * (width - width//4),
                                                        64 * (width - width//4),
                                                        128 * (width - width//4)]:
                            raise RuntimeError("INFORMATION_OR_PHASE_DRIFT")
                        if result.get("cold_restore_exact") is False:
                            raise RuntimeError("COLD_RESTART_DRIFT")
                        if result.get("cold_restore_exact") is None and arm != "count_carry":
                            raise RuntimeError("COLD_RESTART_UNVERIFIED")
                        row["arms"][arm] = {
                            "post_switch_accuracy": result["phase_accuracy"][2],
                            "adapt_error": result["adapt_error"],
                            "measured_cpu_ns": cpu_ns,
                            "measured_wall_ns": wall_ns,
                            "payload_bytes_sent": result.get("payload_bytes_sent", 0),
                            "payload_bytes_delivered": result.get("payload_bytes_delivered", 0),
                            "cold_restore_exact": result.get("cold_restore_exact", "INTERNAL_ONLY"),
                        }
                    cases.append(row)
    dev = [row for row in cases if row["split"] == "DEV"]
    if len(cases) != 36 or len(dev) != 4:
        raise RuntimeError("SPLIT_COVERAGE_DRIFT")
    aggregate = {}
    for arm in ARMS:
        all_rows = [row["arms"][arm] for row in dev]
        aggregate[arm] = {
            "mean_dev_post_accuracy": sum(x["post_switch_accuracy"] for x in all_rows) / len(all_rows),
            "total_dev_adapt_error": sum(x["adapt_error"] for x in all_rows),
            "total_dev_cpu_ns": sum(x["measured_cpu_ns"] for x in all_rows),
            "total_dev_wall_ns": sum(x["measured_wall_ns"] for x in all_rows),
            "total_dev_payload_sent": sum(x["payload_bytes_sent"] for x in all_rows),
        }
    baseline_arms = [arm for arm in ARMS if arm.startswith("ewma_") or arm == "count_carry"]
    best_accuracy_baseline = max(baseline_arms, key=lambda arm: aggregate[arm]["mean_dev_post_accuracy"])
    best_error_baseline = min(baseline_arms, key=lambda arm: aggregate[arm]["total_dev_adapt_error"])
    connected = aggregate["connected"]
    advantage_accuracy = connected["mean_dev_post_accuracy"] - aggregate[best_accuracy_baseline]["mean_dev_post_accuracy"]
    baseline_error = aggregate[best_error_baseline]["total_dev_adapt_error"]
    relative_error_reduction = (baseline_error - connected["total_dev_adapt_error"]) / baseline_error if baseline_error else None
    traces = hashlib.sha256("".join(row["trace_sha256"] for row in cases).encode()).hexdigest()
    return {"schema": SCHEMA,
            "baseline_commit": "52319a22897f76b08260cf3b8bd31b335a048528",
            "case_count": len(cases), "fit_cases": 32, "dev_cases": 4,
            "arms": list(ARMS), "trace_set_sha256": traces, "dev_aggregate": aggregate,
            "dev_per_case": [row for row in dev],
            "conservative_accuracy_baseline": best_accuracy_baseline,
            "conservative_error_baseline": best_error_baseline,
            "connected_accuracy_delta": advantage_accuracy,
            "connected_relative_adapt_error_reduction": relative_error_reduction,
            "data_split_test_accessed": False,
            "raw_predictions_retained": False,
            "recurrent_control_qualified": False,
            "rss_energy_routing_and_full_resource_qualified": False,
            "cold_restart_external_process_qualified": False,
            "scientific_acceptance": "NOT_GRANTED",
            "decision": NO_SCIENCE}

if __name__ == "__main__":
    result = screen()
    if result["scientific_acceptance"] != "NOT_GRANTED" or result["data_split_test_accessed"]:
        raise SystemExit("ACC118_ACCEPTANCE_OR_SOURCE_VIOLATION")
    print("ACC118_DIAGNOSTIC_JSON=" + json.dumps(result, sort_keys=True,
                                                separators=(",", ":")))
