"""F11 task-aligned Q for observing matched sensor pairs in public time.

Six permutations of the same six nonanchor sensors; only temporal order
differs. All action values are learned numerically from actual past
physical-assignment mismatch costs, not from an anomaly-uncertainty proxy
or a prewritten public-start rule bank.

Inference sees ONLY prior public scalar observations and a frozen fitted
14-context x 6-action task-value table, never a hidden swap, seed, family,
onset, evaluator loss, or future public readings. With low support, empirical
Bayes shrinkage toward a global action mean keeps sparse contexts bounded.
"""
from pathlib import Path
import importlib.util
from itertools import permutations
from fractions import Fraction

_spec=importlib.util.spec_from_file_location(
    "f11_frozen_f8_schedule",
    Path(__file__).resolve().parents[1]/"f8_matched_timing"/"schedule.py")
f8=importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(f8)

EPISODES=(0,1,3,5,7)
PROBES=(3,5,7)
ORDERS=tuple(permutations(range(3)))  # six; identity fixed by this tuple order
SOURCE="5797a257a75fe139313e8486cd1a1ae79c44b148"
TRAIN_SEEDS=(67204,67205)
TEST_SEEDS=(67206,67207)
PAIRS=((8,10),(11,13))
SCHEMA="forge.f11.frozen-task-aligned-observation-value.v1"
STATUS="USED_F3_TASK_LOSS_TRAIN_ONLY_NO_SCIENTIFIC_AUTHORITY"
PSEUDO=8
MIN_CONTEXT_SUPPORT=3

def require(condition,code):
    if not condition:raise ValueError("F11_POLICY_"+code)

def start_from_public(history):
    require(type(history) is dict and 0 in history and 1 in history,
            "CALIBRATION_MISSING")
    for t in (0,1):
        require(type(history[t]) is dict and set(history[t])=={0,1} and
                all(type(v) is int and 0<=v<16 for v in history[t].values()),
                "ANCHOR_PUBLIC_ONLY")
    f8.f7.calibration(history)
    return f8.f7.public_start(history)

def validate_model(model):
    require(type(model) is dict and model.get("schema")==SCHEMA
       and model.get("status")==STATUS and model.get("source_commit")==SOURCE
       and model.get("train_seeds")==list(TRAIN_SEEDS)
       and model.get("validation_seeds")==list(TEST_SEEDS)
       and model.get("orders")==[list(x) for x in ORDERS]
       and model.get("pseudo_observations")==PSEUDO
       and model.get("minimum_context_support")==MIN_CONTEXT_SUPPORT
       and model.get("training_cases_per_order")==96
       and model.get("public_scalar_reads")==10
       and model.get("retained_limit")==9
       and model.get("new_first_use_claims")==0
       and model.get("scientific_dispatch_authorized") is False,
       "FROZEN_MODEL")
    rows=model.get("value_table")
    require(type(rows) is list and len(rows)==14*len(ORDERS),
            "VALUE_TABLE")
    for i,row in enumerate(rows):
        require(type(row) is dict and row.get("public_start")==i//6
            and row.get("action_index")==i%6
            and type(row.get("cases")) is int and 0<=row["cases"]<=96
            and type(row.get("total_task_loss")) is int
            and 0<=row["total_task_loss"]<=8*row["cases"]
            and type(row.get("global_loss")) is int
            and 0<=row["global_loss"]<=8*96,
            "NONCANONICAL_TRAINED_VALUES")

def expected_cost(model,s,action):
    validate_model(model)
    require(type(s) is int and 0<=s<14
            and type(action) is int and 0<=action<6,"CONTEXT_OR_ACTION")
    row=model["value_table"][s*6+action]
    # Exact rational with predeclared shrinkage to the global training
    # mean. No validation/reward-dependent weights or post-hoc tuning.
    baseline=Fraction(row["global_loss"],96)
    return (Fraction(row["total_task_loss"],1)+PSEUDO*baseline)/(row["cases"]+PSEUDO)

def learned_order(model,history):
    validate_model(model)
    s=start_from_public(history)
    supports=[model["value_table"][s*6+i]["cases"] for i in range(6)]
    # The same 96 matched cases were run under every schedule.
    require(len(set(supports))==1,"NONMATCHED_TRAINING_SUPPORT")
    if supports[0]<MIN_CONTEXT_SUPPORT:
        # If local evidence is sparse, rank by global task performance.
        return min(range(6),key=lambda i:(
            model["value_table"][s*6+i]["global_loss"],i))
    return min(range(6),key=lambda i:(expected_cost(model,s,i),i))

def choose(episode,history,model,force_order=None):
    # force_order is evaluator-only for the six train/validation controls,
    # never passed when assessing the learned arm. It cannot be a hidden
    # pair/seed/family and must be in the frozen six-action protocol.
    validate_model(model)
    require(type(episode) is int and episode in EPISODES,"EPISODE")
    require(type(history) is dict and sorted(history)==
            [t for t in EPISODES if t<episode],"FUTURE_OR_INCOMPLETE_PUBLIC")
    for t,row in history.items():
        require(type(row) is dict and len(row)==2 and
                all(type(k) is int and 0<=k<16 and
                    type(v) is int and 0<=v<16 for k,v in row.items()),
                "PUBLIC_SCALAR")
    if episode in (0,1):return (0,1)
    s=start_from_public(history)
    action=learned_order(model,history) if force_order is None else force_order
    require(type(action) is int and 0<=action<6,"ACTION_RANGE")
    sensor_set=tuple(f8.f7.SENSORS[(s+x)%14] for x in f8.OFFSETS)
    groups=tuple(sensor_set[i:i+2] for i in (0,2,4))
    return groups[ORDERS[action][PROBES.index(episode)]]

def audit(history,model,action_override=None):
    require(type(history) is dict and sorted(history)==list(EPISODES),
            "TRACE_EPISODES")
    pre={}
    for t in EPISODES:
        predicted=choose(t,pre,model,action_override)
        require(tuple(history[t])==predicted,"NONPUBLIC_ORACLE_DECISION")
        pre[t]=history[t]
    cells=[c for t in PROBES for c in history[t]]
    require(len(cells)==6 and len(set(cells))==6 and
            sum(len(h) for h in history.values())==10 and
            all(c>=2 for c in cells),"READ_CAPACITY")
    s=start_from_public(history)
    action=learned_order(model,history) if action_override is None else action_override
    return {"public_start":s,"action_index":action,"order":list(ORDERS[action]),
            "physical_cells":sorted(cells),"reads":10,"distinct_nonanchors":6}

decoder=f8.common_decoder
