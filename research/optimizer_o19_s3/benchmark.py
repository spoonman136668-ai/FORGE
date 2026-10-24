"""Handwritten source-FREE public input stream; no original environment use."""
from __future__ import annotations
import hashlib
import json
from change_memory import TwoTimescaleMemory, canonical
from controls import LastObserved, LaplaceHistory, MarkovLaplace, NoMemory

# This contains explicitly invented occupancy values, not historical K5F
# CHECK/DEV data or privately sampled environment/world labels.
STREAM = tuple((t, cell, bool(value)) for t, (cell, value) in enumerate([
    ((0,0),1), ((1,0),0), ((0,0),1), ((2,0),0), ((1,0),0),
    ((0,0),1), ((2,0),1), ((1,0),0), ((2,0),0), ((0,0),1),
    ((1,0),0), ((2,0),1), ((0,0),1), ((2,0),0), ((1,0),0),
    ((2,0),1), ((0,0),1), ((2,0),1), ((1,0),0), ((2,0),0),
    ((3,0),1), ((2,0),1), ((3,0),1), ((0,0),1), ((3,0),0),
    ((2,0),0), ((3,0),1), ((0,0),1), ((2,0),1), ((3,0),0),
]))


def measure():
    models = {"two_timescale": TwoTimescaleMemory(),
              "conventional_last": LastObserved(),
              "conventional_laplace": LaplaceHistory(),
              "conventional_markov": MarkovLaplace(),
              "no_memory": NoMemory()}
    outcomes = {name: [] for name in models}
    for t, cell, blocked in STREAM:
        for name, model in models.items():
            pred = model.predict(t, cell)   # LEARNER HAS NOT SEEN THIS OBSERVATION
            outcomes[name].append((pred-int(blocked))**2)
            model.observe(t, cell, blocked)
    # Framing-free canonical JSON size proxies, NOT interpreter RSS nor
    # comparable CPU/FLOP/energy measurements.
    public_states = {
        "two_timescale": {k:vars(v) for k,v in models["two_timescale"].cells.items()},
        "conventional_last": models["conventional_last"].memory,
        "conventional_laplace": dict(models["conventional_laplace"].count),
        "conventional_markov": {"last":models["conventional_markov"].last,
                                 "transition":dict(models["conventional_markov"].transitions)},
        "no_memory": {}}
    return {"schema": "optimizer.o19-s3.handwritten-sourcefree-benchmark.v1",
            "source_original_episodes_executed": 0,
            "scientific_go": False,
            "handwritten_events": len(STREAM),
            "stream_sha256": hashlib.sha256(canonical(STREAM)).hexdigest(),
            "brier_mean": {k: round(sum(v)/len(v), 9) for k,v in outcomes.items()},
            "candidate_better_than_best_conventional":
                (sum(outcomes["two_timescale"])/len(STREAM)
                 < min(sum(outcomes[k])/len(STREAM)
                       for k in models if k != "two_timescale")),
            "unframed_state_json_bytes": {k:len(canonical(v)) for k,v in public_states.items()},
            "predict_updates_per_model": {k:{"predictions":len(v),"updates":len(v)}
                                          for k,v in outcomes.items()},
            "final_candidate_cells": len(models["two_timescale"].cells),
            "final_candidate_checkpoint_bytes": len(models["two_timescale"].snapshot()),
            "final_candidate_observed_flips": sum(c.observed_flips for c in models["two_timescale"].cells.values()),
            "disposition": "SOURCE_ONLY_INTERFACE_TEST_NOT_SCIENCE"}

if __name__ == "__main__":
    print(json.dumps(measure(), indent=2, sort_keys=True))
