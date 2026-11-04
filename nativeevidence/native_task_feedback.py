"""Read-only native task receipts -> bounded development feedback.

No source execution, policy update, first-use, scientific acceptance or signer.
Transport authentication stays with the existing original-receipt custodian.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from f118_autonomy_feedback import canonical
MAX_BYTES = 4 * 1024 * 1024

SCHEMA = "forge.native-task-feedback.v1"
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")

class Rejected(ValueError):
    pass

def need(ok, reason):
    if not ok:
        raise Rejected(reason)

def integer(value):
    return type(value) is int and 0 <= value <= 1000000

def number(value):
    return type(value) in (int, float) and math.isfinite(value)

def strict(raw):
    need(type(raw) is bytes and 0 < len(raw) <= MAX_BYTES, "RECEIPT_SIZE")
    def pairs(items):
        out = {}
        for key, value in items:
            need(key not in out, "DUPLICATE_JSON_KEY")
            out[key] = value
        return out
    def invalid_constant(value):
        raise Rejected("NONFINITE_JSON")
    try:
        result = json.loads(raw.decode("utf8"), object_pairs_hook=pairs,
                            parse_constant=invalid_constant)
    except (ValueError, UnicodeError) as exc:
        raise Rejected("INVALID_JSON") from exc
    need(type(result) is dict, "RECEIPT_OBJECT_REQUIRED")
    return result


def episode(row, lane):
    need(type(row) is dict, "EPISODE_REQUIRED")
    steps = row.get("original_selected_actions" if lane == "Yggdrasil" else "steps")
    reward = row.get("return")
    need(integer(steps) and number(reward), "INVALID_TASK_METRIC")
    if lane == "Yggdrasil":
        positives = row.get("positive_terminal_rewards")
        need(integer(positives) and positives <= steps, "INVALID_GOAL_COUNT")
        need(type(row.get("terminated")) is bool and type(row.get("truncated")) is bool,
             "TERMINAL_FLAGS_REQUIRED")
        need(positives == 0 or row["terminated"] and reward > 0, "UNSUPPORTED_GOAL")
        ledger = row.get("source_ledger")
        need(type(ledger) is list and len(ledger) == steps, "SOURCE_STEP_COUNT")
        need(hashlib.sha256(canonical(ledger).removesuffix(b"\n")).hexdigest() == row.get("source_ledger_sha256"),
             "SOURCE_LEDGER_DIGEST")
        need(all(type(e) is dict and number(e.get("reward")) for e in ledger),
             "SOURCE_REWARD_REQUIRED")
        need(math.isclose(sum(e["reward"] for e in ledger), reward, abs_tol=1e-9),
             "SOURCE_RETURN_MISMATCH")
        wall = row.get("elapsed_wall_seconds")
        need(number(wall) and wall >= 0, "INVALID_COST")
        return steps, reward, int(positives > 0), wall
    goal = row.get("goal_reached")
    need(type(goal) is bool and (not goal or reward > 0), "INVALID_GOAL")
    return steps, reward, int(goal), None

def summarize(raw, *, lane, source_sha, expected_sha256):
    need(lane in ("Wingless", "Yggdrasil") and type(source_sha) is str
         and HEX40.fullmatch(source_sha) is not None, "SOURCE_IDENTITY")
    need(type(expected_sha256) is str and HEX64.fullmatch(expected_sha256)
         and type(raw) is bytes and hashlib.sha256(raw).hexdigest() == expected_sha256,
         "RECEIPT_IDENTITY")
    report = strict(raw)  # Actual MG90 train receipts exceed 1 MB; fixed 4 MiB ceiling.
    schema = report.get("schema")
    groups = []
    incomplete = False
    if lane == "Yggdrasil":
        need(schema == "yggdrasil.mg90.empirical-relational-frontier-dev.v1"
             and report.get("phase") in ("train", "heldout"), "UNSUPPORTED_REPORT")
        need(report.get("scientific_admission") == "DEV_ONLY_NO_CAUSAL_OR_GENERALIZATION_CLAIM",
             "AUTHORITY_DRIFT")
        phase = report["phase"]
        rows = report.get("episodes")
        need(type(rows) is list and 0 < len(rows) <= 128, "EPISODE_BOUNDS")
        roles = report.get("roles")
        need(type(roles) is list and 0 < len(roles) <= 16
             and all(type(r) is str for r in roles) and len(set(roles)) == len(roles),
             "ROLE_IDENTITY")
        identities = [(r.get("family"), r.get("role"), r.get("phase"), r.get("seed"))
                      for r in rows if type(r) is dict]
        need(len(identities) == len(rows)
             and all(type(f) is str and role in roles and p == phase and type(seed) is int and 0 <= seed < 2**32
                     for f, role, p, seed in identities)
             and len(set(identities)) == len(rows), "DUPLICATE_OR_MIXED_EPISODES")
        for role in roles:
            selected = [r for r in rows if r["role"] == role]
            need(bool(selected), "MISSING_ROLE")
            groups.append((role, phase, selected))
        counts = report.get("source_step_counts")
        need(type(counts) is dict and set(counts) == set(roles)
             and all(type(counts[r]) is int and counts[r] == sum(
                 x["original_selected_actions"] for x in rows if x["role"] == r)
                     for r in roles), "ROLE_EXPOSURE_MISMATCH")
    else:
        if schema == "wingless.itd02.exact-exposure-incomplete.v1":
            need(report.get("status") == "INCOMPLETE_SOURCE_EXPOSURE"
                 and report.get("science") == "NOT_ACCEPTED"
                 and report.get("comparison_complete") is False
                 and report.get("evaluation_authorized_by_receipt") is False,
                 "INCOMPLETE_AUTHORITY_DRIFT")
            observed, remaining, required = (report.get(k) for k in
                ("observed_interactions", "remaining_interactions", "required_interactions"))
            need(all(integer(v) for v in (observed, remaining, required))
                 and remaining > 0 and observed + remaining == required,
                 "INCOMPLETE_EXPOSURE_MISMATCH")
            rows = report.get("completed_episode_records")
            need(type(rows) is list and len(rows) <= 128
                 and all(type(x) is dict and integer(x.get("steps")) for x in rows)
                 and sum(x["steps"] for x in rows) == observed, "INCOMPLETE_PREFIX")
            incomplete = True
            phase = "incomplete"
            groups = []  # Partial observations never masquerade as a complete arm.
        else:
            need(schema == "wingless.itd02.exact-exposure-frozen.v1"
                 and report.get("science") == "NOT_ACCEPTED", "UNSUPPORTED_REPORT")
            training = report.get("train")
            need(type(training) is dict and 0 < len(training) <= 16, "TRAIN_ARMS_REQUIRED")
            expected = report.get("exact_train_interactions_per_arm")
            need(integer(expected) and expected > 0, "TRAIN_EXPOSURE_REQUIRED")
            for role, arm in training.items():
                need(type(role) is str and type(arm) is dict, "ARM_IDENTITY")
                rows = arm.get("episodes")
                need(type(rows) is list and 0 < len(rows) <= 128, "EPISODE_BOUNDS")
                need(sum(x.get("steps", -1) for x in rows) == expected,
                     "UNEQUAL_TRAINING_EXPOSURE")
                groups.append((role, "train", rows))
            # Evaluation outcomes are deliberately excluded from optimization input.
            phase = "train"
    metrics = []
    for role, group_phase, rows in groups:
        values = [episode(r, lane) for r in rows]
        metrics.append(dict(role=role, phase=group_phase, episodes=len(rows),
            source_steps=sum(v[0] for v in values), task_return=sum(v[1] for v in values),
            completed_goals=sum(v[2] for v in values),
            wall_seconds=sum(v[3] for v in values) if all(v[3] is not None for v in values) else None))
    return dict(schema=SCHEMA, lane=lane, source_sha=source_sha,
        receipt_sha256=expected_sha256, input_schema=schema, phase=phase,
        status="INCOMPLETE" if incomplete else "OBSERVED_TASK_METRICS", metrics=metrics,
        development_training_feedback_available=phase == "train" and not incomplete,
        incomplete_exposure=dict(observed=observed, remaining=remaining, required=required)
            if incomplete else None,
        source_authentication="NOT_ESTABLISHED_BY_ADAPTER",
        all_in_cost_verified=False, retention_verified=False, transfer_verified=False,
        optimizer_update_authorized=False, scientific_acceptance=False,
        first_use_authorized=False, live_owner_changed=False)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--lane", choices=("Wingless", "Yggdrasil"), required=True)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--receipt-sha256", required=True)
    args = parser.parse_args()
    # Bounded read; strict() rejects an oversized original without truncation.
    with args.receipt.open("rb") as stream:
        raw = stream.read(MAX_BYTES + 1)
    print(canonical(summarize(raw, lane=args.lane, source_sha=args.source_sha,
                             expected_sha256=args.receipt_sha256)).decode())
