"""Independent M-R6 public-information audit over immutable R6 fitted-controls.

Developer-smoke only: no official R6 seeds, DEV/VALID/ABLATE, CKB admission,
protected original tasks, hidden role/state reads, or R6 experiment() invocation.
"""
from __future__ import annotations

import hashlib
import json
from public_dev import PUBLIC_FAMILIES, canonical
from r4_sequential_controls import PredictiveTransitionPlanner
from r5_causal_dev import R5CausalWorld, public_causal_oracle
from run_r6_fitted_controls import (
    SOURCE_PARENT, public_teacher_trajectory, role_seed, episode_key
)

PROTOCOL = "mass.r6.public-information-preregistered.v1"
FIT_SMOKE_SEED = 7
N_PER_FAMILY = 4
CAUSAL_PUBLIC_KINDS = frozenset(
    ("feed_pulse", "dependence_pulse", "goal_confirmed")
)
PARENT_R6_GIT_SHA = "b0074839fdc347d3ebf12f8d8806edf7bb0e76fa"


def fail_if(condition, why):
    if condition:
        raise ValueError("MASS_R6_" + why)


def one_trajectory(fi, i):
    fail_if(fi not in (0, 1) or type(i) is not int or i not in range(4),
            "FROZEN_SMOKE_COHORT")
    family = PUBLIC_FAMILIES[fi]
    source_seed = role_seed("FIT", FIT_SMOKE_SEED, fi, i)
    external = episode_key("FIT", FIT_SMOKE_SEED, fi, i)
    rows, teacher_sha = public_teacher_trajectory(family, source_seed, external)

    # Exact developer-only public replay checks the source-public trace bytes;
    # no hidden causal role or private future information is returned to agent.
    world = R5CausalWorld(family, "DEV-" + external.replace(":", "-"),
                          source_seed)
    first = json.loads(canonical(world.reset()))
    def step(action):
        return json.loads(canonical(world.step(action)))
    reward = public_causal_oracle(first, step)["reward"]
    events = [
        event
        for r in world.public_trace_records()
        for event in r["result"]["observation"]["delayed_events"]
        if event.get("kind") in CAUSAL_PUBLIC_KINDS
    ]
    replay_sha = world.public_trace_receipt()["trace_head_sha256"]
    fail_if(reward != 1 or teacher_sha != replay_sha,
            "TEACHER_PUBLIC_REPLAY_DISAGREEMENT")
    fail_if(not rows or not events,
            "PUBLIC_CAUSAL_EXPERIENCE_MISSING")
    fail_if(any(set(row) != {"x", "key", "y"} for row in rows),
            "UNDECLARED_TRAINING_FEATURE")
    fail_if(any(len(row["x"]) != 24 for row in rows),
            "FEATURE_WIDTH_DRIFT")
    feature_semantic = sum(int(any(row["x"][8:20])) for row in rows)
    feature_kind = sum(int(row["x"][23] != 0) for row in rows)
    history_semantic = sum(int(tuple(row["key"][3:5]) != (-1, -1))
                           for row in rows)
    return {
        "rows": rows,  # kept private in this audit, NOT added to public receipt
        "trace_sha256": teacher_sha,
        "summary": {
            "family": family, "smoke_seed": source_seed, "episode": external,
            "public_causal_event_count": len(events),
            "public_causal_kind_counts": {
                kind: sum(x["kind"] == kind for x in events)
                for kind in sorted(CAUSAL_PUBLIC_KINDS)
            },
            "training_rows": len(rows),
            "r4_semantic_role_feature_active_rows": feature_semantic,
            "r4_causal_event_type_feature_active_rows": feature_kind,
            "r4_history_key_role_bound_rows": history_semantic,
            "original_public_teacher_trace_sha256": teacher_sha,
        }
    }


def audit():
    family_rows = {}
    histories = []
    audit_chain = hashlib.sha256(b"MASS_R6_FROZEN_PUBLIC_SMOKE_V1").digest()
    for fi, family in enumerate(PUBLIC_FAMILIES):
        reports = []
        for i in range(N_PER_FAMILY):
            record = one_trajectory(fi, i)
            histories.append(record["rows"])
            reports.append(record["summary"])
            audit_chain = hashlib.sha256(audit_chain +
                bytes.fromhex(record["trace_sha256"])).digest()
        family_rows[family] = reports

    # Fit exactly ONE frozen conventional structured learner on 8 public
    # smoke demonstration histories. No R6 fit/val/DEV official cohort.
    fitted = PredictiveTransitionPlanner()
    before = dict(fitted.serialize())
    fitted.train(histories)
    after = fitted.serialize()
    evidence_rows = [v for reports in family_rows.values() for v in reports]
    causal = sum(r["public_causal_event_count"] for r in evidence_rows)
    feature_hits = sum(
        r["r4_semantic_role_feature_active_rows"] +
        r["r4_causal_event_type_feature_active_rows"] +
        r["r4_history_key_role_bound_rows"] for r in evidence_rows)
    stats = sum(sum(counter.values()) for counter
                in fitted.delays.values())
    results = {
        "schema": PROTOCOL,
        "candidate_r6_head": PARENT_R6_GIT_SHA,
        "frozen_r5_parent": SOURCE_PARENT,
        "public_only": True,
        "source_birth_authority": "NONE",
        "scientific_first_use": False,
        "native_wingless_yggdrasil_executed": False,
        "independent_hidden_h1_h2_used": False,
        "scope": "EXACTLY_EIGHT_NONPROTECTED_FIT_SMOKE_DEMONSTRATIONS",
        "fixed_smoke_model_seed": FIT_SMOKE_SEED,
        "public_demo_trace_chain_sha256": audit_chain.hex(),
        "public_causal_events_seen": causal,
        "baseline_semantic_feature_activations": feature_hits,
        "structured_planner_training_updates": fitted.updates,
        "structured_planner_public_event_fit_counts": stats,
        "structured_planner_initial_delay_prior": before["delay_fit"],
        "structured_planner_postfit_delay_prior": after["delay_fit"],
        "original_r6_frozen_DEV_reclassified": False,
        "families": family_rows
    }
    results["classification"] = (
        "UNUSABLE_PUBLIC_EVENT_VOCABULARY_IN_R4_FEATURE_PIPELINE"
        if causal > 0 and feature_hits == 0 and fitted.updates == 0 and
        stats == 0 and before["delay_fit"] == after["delay_fit"]
        else "COUNTEREXAMPLE_DO_NOT_CLAIM_EVENT_PIPELINE_BLINDNESS"
    )
    results["scientific_disposition"] = "INFORMATION_EQUIVALENCE_NOT_ESTABLISHED"
    return results


if __name__ == "__main__":
    print(json.dumps(audit(), sort_keys=True, separators=(",", ":")))
