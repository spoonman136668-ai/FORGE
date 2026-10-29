"""AC-21 bounded, historically native fit on sequentially buffered PUBLIC DTR history.

The per-site latch is fixed, not a learned recurrent state. Original unchanged
Yggdrasil LocalTaskRuntime performs the actual reward learning, with shared
genome and local role weights; the two original one-hop cell outputs are fused
externally. Neither DTR nor the active Yggdrasil runtime is imported/edited.
Only previously certified original-source FIT/DEV JSON is replayed.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
import sys
import time
import tracemalloc

import ac15_native_public_adapter as ac15
import ac18_original_ring_dtr as ac18
import ac19_typed_original_native_bridge as ac19
import ac20_history_locality as ac20

SCHEMA = "forge.ac21.sequential-public-history-original-native-fit.v1"
SOURCE_RECEIPT_RUN = 40797373953
HISTORY_SITES = (3, 4, 5, 6)
REWARD_SITES = (4, 5)
FIT_SEEDS = tuple(range(760000, 760008))
DEV_SEEDS = tuple(range(760200, 760204))


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def binary(value):
    if type(value) is not int or value not in (0, 1):
        raise ValueError("AC21_PUBLIC_BIT_REQUIRED")
    return value


class SequentialLocalLatch:
    """Episode-local, site-addressed public pulse latch; NO target/latent input.

    Only stage-zero observation and scripted public action become site 3/4.
    Only a *subsequent* stage-one observation and action become site 5/6.
    Each site retains its own binary value; no full-history tensor is sent
    to a site. The historical LocalTaskRuntime reads local one-hop features.
    Retention is deterministic and is explicitly NOT trained.
    """

    def __init__(self):
        self.bits = [0] * 8
        self.stage = 0
        self.writes = 0

    def advance(self, stage, observation, action):
        if type(stage) is not int or stage != self.stage or stage not in (0, 1):
            raise ValueError("AC21_STAGE_ORDER_OR_DUPLICATE")
        observation, action = binary(observation), binary(action)
        target_sites = (3, 4) if stage == 0 else (5, 6)
        self.bits[target_sites[0]] = observation
        self.bits[target_sites[1]] = action
        self.writes += 2
        self.stage += 1
        return tuple(self.bits)

    def terminal_bits(self, omit=None):
        if self.stage != 2 or self.writes != 4:
            raise ValueError("AC21_INCOMPLETE_SEQUENTIAL_PUBLIC_HISTORY")
        if omit is not None and (type(omit) is not int or omit not in HISTORY_SITES):
            raise ValueError("AC21_INVALID_ABLATION_SITE")
        data = list(self.bits)
        if omit is not None:
            data[omit] = 0
        return data


def public_episode_bits(episode, omit=None):
    """Source document contract was verified separately before this replay."""
    if type(episode) is not dict or set(episode) != {"seed", "events", "ctf_do_permission_denied"}:
        raise ValueError("AC21_UNKNOWN_ORACLE_OR_UNVERIFIED_EPISODE_FIELD")
    events = episode["events"]
    if type(events) is not list or len(events) != 2:
        raise ValueError("AC21_NOT_TWO_PUBLIC_STAGES")
    latch = SequentialLocalLatch()
    for step, event in enumerate(events):
        if type(event) is not dict or set(event) != ac15.FIELDS:
            raise ValueError("AC21_ORACLE_FIELD_IN_PUBLIC_EVENT")
        latch.advance(event["stage"], event["observation"], event["action"])
        if step == 0 and (event["terminated"] is not False or
                          event["reward"] != 0 or
                          event["next_observation"] != events[1]["observation"]):
            raise ValueError("AC21_PUBLIC_STAGE_CHAIN_OR_EARLY_REWARD")
    if events[1]["terminated"] is not True or events[1]["next_observation"] is not None:
        raise ValueError("AC21_TERMINAL_PUBLIC_TYPE_DRIFT")
    bits = latch.terminal_bits(omit=omit)
    return bits, binary(events[1]["reward"]), latch.writes


def reward_targets(label):
    label = binary(label)
    targets = [0] * 8
    for site in REWARD_SITES:
        targets[site] = label
    return targets


def two_site_score(model, bits):
    predictions = model.predict(bits)
    return (float(predictions[4]) + float(predictions[5])) / 2.0


def score(probs, labels):
    if len(probs) != len(labels) or not probs:
        raise ValueError("AC21_EMPTY_OR_MISALIGNED_SCORE")
    if any(not math.isfinite(p) or not 0 <= p <= 1 for p in probs):
        raise ValueError("AC21_NONPROBABILISTIC_PREDICTION")
    return {
        "n": len(labels),
        "correct": sum(int(p >= .5) == y for p, y in zip(probs, labels)),
        "brier": sum((p - y)**2 for p, y in zip(probs, labels)) / len(labels)
    }


def run(ygg: Path, source: Path, parent15: Path, parent18: Path):
    # Original source checkout is pinned for identity only, never imported.
    ac20._verify(source, ac20.SOURCE_COMMIT,
                 "causal_gym/envs/dtr.py", ac20.SOURCE_BLOB)
    ac20._verify(ygg, ac20.NATIVE_COMMIT,
                 "yggdrasil/task_runtime.py", ac20.NATIVE_BLOB)
    sys.path.insert(0, str(ygg.resolve()))
    from yggdrasil.task_runtime import LocalTaskRuntime, LocalCountControl
    # AC18 also authenticates unchanged original historical ring and bridge.
    ac18.original_native(ygg)
    p15 = json.loads(parent15.read_text(encoding="utf-8"))
    p18 = json.loads(parent18.read_text(encoding="utf-8"))
    fit, dev = ac18.exact_source(p15)
    if (p18.get("schema") != ac18.SCHEMA or
        p18.get("upstream_original_commit") != ac20.SOURCE_COMMIT or
        p18.get("historical_ygg_original_commit") != ac20.NATIVE_COMMIT or
        p18.get("new_source_owned_episodes") != 0 or
        p18.get("scientific_first_use") is not False or
        p18.get("full_native_task_bridge_admission", {}).get(
            "full_native_runtime_admission") != "NO_GO_PUBLIC_TYPE_MISMATCH"):
        raise RuntimeError("AC21_CERTIFIED_PARENT_OR_NEGATIVE_NOT_PRESERVED")
    if ([e["seed"] for e in fit["episodes"]] != list(FIT_SEEDS) or
        [e["seed"] for e in dev["episodes"]] != list(DEV_SEEDS) or
        set(FIT_SEEDS) & set(DEV_SEEDS)):
        raise RuntimeError("AC21_SOURCE_ROLE_SEEDS_DRIFT")

    native = LocalTaskRuntime()
    cold_control = LocalCountControl(native.neighbors)
    stage_current = LocalTaskRuntime()
    ablated = {site: LocalTaskRuntime() for site in HISTORY_SITES}
    if native.neighbors[4] != (3, 5) or native.neighbors[5] != (4, 6):
        raise RuntimeError("AC21_SOURCE_LOCAL_NEIGHBORHOOD_DRIFT")
    before = sha(native.snapshot())
    full_counts = defaultdict(lambda: [0, 0])
    recent = {}
    priors = []
    fit_rows = []
    tracemalloc.start()
    start = time.perf_counter_ns()
    for episode in fit["episodes"]:
        bits, label, writes = public_episode_bits(episode)
        if writes != 4:
            raise RuntimeError("AC21_NOT_SEQUENTIAL")
        full_counts[tuple(bits[3:7])][label] += 1
        priors.append(label)
        native.observe(bits, reward_targets(label))
        cold_control.observe(bits, reward_targets(label))
        e1 = episode["events"][1]
        stage_current.observe(ac19.encode_before(1, e1["observation"], e1["action"]),
                              ac19.encode_after(None, True, label))
        for site, model in ablated.items():
            masked, _, _ = public_episode_bits(episode, omit=site)
            model.observe(masked, reward_targets(label))
        fit_rows.append({"seed": episode["seed"], "public_cells": bits[3:7],
                         "local_writes": writes})
    fit_wall = time.perf_counter_ns() - start
    peak = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()
    if native.core.events != 8 or stage_current.core.events != 8 or any(
        model.core.events != 8 for model in ablated.values()):
        raise RuntimeError("AC21_NATIVE_FIT_EVENTS_NOT_EIGHT")
    if sha(native.snapshot()) == before:
        raise RuntimeError("AC21_ORIGINAL_NATIVE_DID_NOT_LEARN")

    frozen = native.snapshot()
    frozen_hash = sha(frozen)
    restored = LocalTaskRuntime.restore(frozen)
    if restored.snapshot() != frozen:
        raise RuntimeError("AC21_NATIVE_COLD_RESTORE_INVALID")
    other_frozen = {str(site): sha(m.snapshot()) for site, m in ablated.items()}
    current_frozen = sha(stage_current.snapshot())
    tabular_counts_before = json.dumps(sorted(
        (list(k), v) for k, v in full_counts.items()), separators=(",", ":"))
    prior = sum(priors) / len(priors)
    predicted = {key: [] for key in
                 ("native_two_local_cells", "original_local_count_two_cells",
                  "native_current_context_only", "full_history_laplace",
                  "full_history_recency", "pooled_fit_prior",
                  *("ablate_site_" + str(i) for i in HISTORY_SITES))}
    labels = []
    dev_rows = []
    dev_start = time.perf_counter_ns()
    for episode in dev["episodes"]:
        bits, truth, writes = public_episode_bits(episode)
        key = tuple(bits[3:7])
        # Missing DEV contexts must never insert entries into FIT state.
        count = full_counts.get(key, (0, 0))
        n = sum(count)
        native_p = two_site_score(native, bits)
        if native_p != two_site_score(restored, bits):
            raise RuntimeError("AC21_COLD_DEV_PREDICTION_DRIFT")
        table_p = (1 + count[1]) / (2 + n)
        # Same complete history and same source FIT events for both controls.
        timeline = [(k, y) for k, y in
                    ((tuple(row["public_cells"]), fit["episodes"][idx]["events"][1]["reward"])
                     for idx, row in enumerate(fit_rows)) if k == key]
        ema = prior
        for _, y in timeline:
            ema = .5 * y + .5 * ema
        current_event = episode["events"][1]
        baseline_bits = ac19.encode_before(1, current_event["observation"],
                                          current_event["action"])
        values = {
            "native_two_local_cells": native_p,
            "original_local_count_two_cells":
                (float(cold_control.predict(bits)[4]) +
                 float(cold_control.predict(bits)[5])) / 2.,
            "native_current_context_only": float(stage_current.predict(baseline_bits)[5]),
            "full_history_laplace": table_p,
            "full_history_recency": ema,
            "pooled_fit_prior": prior
        }
        for site, model in ablated.items():
            masked, _, _ = public_episode_bits(episode, omit=site)
            values["ablate_site_" + str(site)] = two_site_score(model, masked)
        for name, prob in values.items():
            predicted[name].append(prob)
        labels.append(truth)
        dev_rows.append({"seed": episode["seed"],
                         "public_history": list(key),
                         "source_observed_terminal_reward": truth,
                         "fit_full_history_support": n,
                         "model_probabilities": values,
                         "sequential_local_writes": writes})
    dev_wall = time.perf_counter_ns() - dev_start
    if (native.snapshot() != frozen or restored.snapshot() != frozen or
        sha(stage_current.snapshot()) != current_frozen or
        any(sha(m.snapshot()) != other_frozen[str(site)] for site, m in ablated.items()) or
        json.dumps(sorted((list(k), v) for k, v in full_counts.items()),
                   separators=(",", ":")) != tabular_counts_before):
        raise RuntimeError("AC21_DEV_MUTATED_FIT_PARAMETERS")
    result = {
        "schema": SCHEMA,
        "scope": "HISTORICAL_NATIVE_WITH_FIXED_SEQUENTIAL_SITE_LATCH_ENGINEERING",
        "original_source_commit": ac20.SOURCE_COMMIT,
        "original_source_blob": ac20.SOURCE_BLOB,
        "historical_native_commit": ac20.NATIVE_COMMIT,
        "historical_native_blob": ac20.NATIVE_BLOB,
        "certified_source_receipt_run": SOURCE_RECEIPT_RUN,
        "fit_episodes_replayed": len(fit["episodes"]),
        "dev_episodes_replayed": len(dev["episodes"]),
        "new_source_owned_episodes": 0,
        "fit_native_terminal_label_updates": native.core.events,
        "native_shared_genome_and_local_roles": True,
        "per_site_temporal_latch_is_fixed_not_learned": True,
        "external_two_site_prediction_fusion": True,
        "only_original_one_hop_native_features": True,
        "fit_local_write_count": sum(x["local_writes"] for x in fit_rows),
        "dev_local_write_count": sum(x["sequential_local_writes"] for x in dev_rows),
        "fit_wall_ns": fit_wall,
        "fit_python_peak_bytes": peak,
        "dev_wall_ns": dev_wall,
        "fitted_native_checkpoint_bytes": len(frozen.encode("utf-8")),
        "fitted_native_sha256": frozen_hash,
        "original_native_changed_during_fit": before != frozen_hash,
        "native_cold_restore_predictions_match": True,
        "dev_updates": 0,
        "dev_scoring": {k: score(v, labels) for k, v in predicted.items()},
        "dev_public_records": dev_rows,
        "source_private_latent_or_model_oracle_used": False,
        "source_module_imported": False,
        "on_policy_source_actions_executed": False,
        "true_on_policy_return_measured": False,
        "learned_distributed_temporal_memory_demonstrated": False,
        "superiority_over_all_fully_informed_controls_proven": False,
        "scientific_first_use": False,
        "scientific_admission": False,
        "active_native_or_forge_controller_modified": False
    }
    if (len(dev_rows) != 4 or result["fit_local_write_count"] != 32 or
        result["dev_local_write_count"] != 16 or
        not result["original_native_changed_during_fit"]):
        raise RuntimeError("AC21_FIT_OR_DEV_BOUND_FAIL")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--native", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--ac15-report", type=Path, required=True)
    parser.add_argument("--ac18-report", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    a = parser.parse_args()
    outcome = run(a.native, a.source, a.ac15_report, a.ac18_report)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(outcome, sort_keys=True, indent=2,
                                allow_nan=False) + "\n", encoding="utf-8")
    print("AC21_SEQUENTIAL_ORIGINAL_NATIVE_FIT=PASS")
    for name, metric in outcome["dev_scoring"].items():
        print("AC21_DEV_BRIER_" + name.upper() + "=" + str(metric["brier"]))
    print("AC21_NEW_SOURCE_EPISODES=ZERO")
    print("AC21_SCIENTIFIC_ADMISSION=NO")
