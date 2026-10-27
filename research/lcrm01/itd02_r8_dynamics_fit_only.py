#!/usr/bin/env python3
"""Preserve fitted full-map dynamics control on the shared R8 FIT cohort.

Full-map BFS receives walls unavailable to native six-field R8/R5. It must
remain an EXTRA-INFORMATION control, not an equal-observation comparator.
No CHECK/DEV environments are opened.
"""
import hashlib
import json
import os
from pathlib import Path
import k4x_curriculum_intervention as k4x
import k4y_native_affordance as k4y
from itd02_r8_original_world_preflight import preflight

FIT = tuple(range(81400, 81424))

def main():
    preflight()
    old_seeds, old_fit = k4y.SEEDS, k4x.FIT_SEEDS
    try:
        k4y.SEEDS = {**old_seeds, "FIT": FIT}
        stream, starts, audit, _, control = k4y.fit()
    finally:
        k4y.SEEDS, k4x.FIT_SEEDS = old_seeds, old_fit
    if control is None or control.get("FIT_source_eligible") is not True:
        raise ValueError("R8_DYNAMICS_FIT_NOT_ELIGIBLE")
    if len(stream) != 12000 or any(audit[f]["public_steps"] != 6000 for f in ("empty", "fourrooms")):
        raise ValueError("R8_DYNAMICS_FIT_BUDGET_DRIFT")
    if any(e["seed"] not in FIT for e in stream):
        raise ValueError("R8_DYNAMICS_FIT_SEED_DRIFT")
    dynamics = control["dynamics"]
    if not isinstance(dynamics, dict) or dynamics.get("source_transition_count") != 12000:
        raise ValueError("R8_DYNAMICS_FIT_STATE_DRIFT")
    raw = json.dumps(dynamics, sort_keys=True, separators=(",", ":")).encode()
    if json.loads(raw) != dynamics:
        raise ValueError("R8_DYNAMICS_FIT_JSON_ROUNDTRIP")
    root = Path(os.environ["RUNNER_TEMP"]) / "itd02-r8-dynamics-fit"
    root.mkdir(parents=True, exist_ok=True)
    output = root / "full-map-fit-dynamics.json"
    receipt = root / "full-map-fit-receipt.json"
    if output.exists() or receipt.exists():
        raise ValueError("R8_DYNAMICS_FIT_REFUSE_OVERWRITE")
    output.write_bytes(raw)
    result = {"gate":"ITD02_R8_FULL_MAP_FIT_DYNAMICS",
              "result":"FIT_ONLY_CONTROL_PRESERVED",
              "fit_seeds":[81400,81423],"fit_public_transitions":12000,
              "dynamics_sha256":hashlib.sha256(raw).hexdigest(),
              "dynamics_bytes":len(raw),
              "full_public_map_extra_information":True,
              "equal_observation_comparator_ready":False,
              "check_episodes":0,"development_episodes":0,
              "scientific_first_use":False,"scientific_accepted":False}
    receipt.write_text(json.dumps(result, sort_keys=True)+"\n")
    print(json.dumps(result, sort_keys=True))

if __name__ == "__main__":
    main()
