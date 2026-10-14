"""F4 sensor-set *mechanism rehearsal* using already-used F3 development labels.

This is NOT F4 training or a prospective experiment. No proposed F4
development/sealed seeds enter this module. It establishes that a
deterministic, train-only physical-sensor set learner can produce the
matched-decoder comparator without inference-time access to pair identity.
"""
import hashlib
import json
from collections import Counter
from dataclasses import dataclass

HISTORICAL_TRAIN_SEEDS=(67200,67201,67202,67203)
F3_LEGAL_TRAIN_PAIRS=((8,10),(11,13))
F4_PROPOSED_DEV=frozenset(range(67600,67608))
F4_PROPOSED_SEALED=frozenset(range(67640,67656))
CALIBRATION=((0,1),(0,1),(0,1))
PUBLIC_PROBES=(0,1,3,5,7)

@dataclass(frozen=True)
class TrainingCase:
    seed:int
    legal_pair:tuple[int,int]

def historical_training_cases():
    # F3 training labels were part of its earlier public preregistration;
    # no F4 cohort use, heldout label, or model API call occurs here.
    return tuple(TrainingCase(seed,HISTORICAL_TRAIN_SEEDS and F3_LEGAL_TRAIN_PAIRS[i%2])
                 for i,seed in enumerate(HISTORICAL_TRAIN_SEEDS))

def learn_coverage(training):
    rows=tuple(training)
    if len(rows)!=len(HISTORICAL_TRAIN_SEEDS):
        raise ValueError("F4_REHEARSAL_TRAINING_SIZE")
    if any(type(t) is not TrainingCase for t in rows):
        raise ValueError("F4_REHEARSAL_INPUT_TYPE")
    if tuple(t.seed for t in rows)!=HISTORICAL_TRAIN_SEEDS:
        raise ValueError("F4_REHEARSAL_FORBIDDEN_NEW_OR_REORDERED_SEED")
    if any(type(t.legal_pair) is not tuple or t.legal_pair not in F3_LEGAL_TRAIN_PAIRS
           for t in rows):
        raise ValueError("F4_REHEARSAL_LEGAL_PAIR_LABEL")
    if any(t.seed in F4_PROPOSED_DEV or t.seed in F4_PROPOSED_SEALED for t in rows):
        raise ValueError("F4_REHEARSAL_UNVERIFIED_F4_SEED")
    # Deterministic greedy maximum-cover: choose two physical sensor
    # addresses that detect the largest number of *training* swap cases.
    uncovered=set(range(len(rows)))
    chosen=[]
    for _ in range(2):
        scored=[(sum(i in uncovered and cell in row.legal_pair for i,row in enumerate(rows)),
                 -cell,cell) for cell in range(2,16) if cell not in chosen]
        best=max(scored)
        if best[0]<=0:
            raise ValueError("F4_REHEARSAL_ZERO_TRAINING_COVERAGE")
        chosen.append(best[2])
        uncovered={i for i in uncovered if best[2] not in rows[i].legal_pair}
    if len(chosen)!=2 or chosen[0]==chosen[1]:
        raise ValueError("F4_REHEARSAL_SENSOR_CAPACITY")
    set_schedule=CALIBRATION+(tuple(chosen),(0,1))
    # An order-control ablation moves the EXACT same physical-read set
    # from episode 5 to episode 7 without introducing more reads.
    order_schedule=CALIBRATION+((0,1),tuple(chosen))
    return {
        "schema":"forge.f4.historical-training-only-rehearsal.v1",
        "status":"MECHANISM_REHEARSAL_F3_USED_LABELS_ONLY_NOT_F4_TRAINING",
        "training_seed_ids":list(HISTORICAL_TRAIN_SEEDS),
        "historical_pair_labels":[list(t.legal_pair) for t in rows],
        "method":"train_label_maximum_cover_greedy_lex_tie",
        "learned_physical_sensors":chosen,
        "set_schedule":[list(x) for x in set_schedule],
        "order_control_schedule":[list(x) for x in order_schedule],
        "read_budget":10,
        "f4_development_seeds_consumed":0,
        "sealed_first_uses":0,
        "scientific_originals":0,
        "science_admitted":False,
        "inference_uses_hidden_pair":False,
    }

def serialize_model(model):
    return (json.dumps(model,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n").encode()

def digest_model(model):
    return hashlib.sha256(serialize_model(model)).hexdigest()
