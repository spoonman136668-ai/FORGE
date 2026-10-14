"""F10 learned public-sensor value: posterior expected uncertainty reduction.

Only prior public measurements are available when selecting a sensor.
Offline supervised counts are derived from F9's previously consumed F3
training trace *public values*, not the hidden swap, seed, regime or family
at inference. Each potential Bernoulli anomaly observation has expected
quadratic-uncertainty reduction p*(1-p); sample the top two unobserved
physical cells at episodes 3,5,7, within the original ten scalar reads.

This is a deliberately simple learned information-value estimator rather
than a handcrafted rule bank, NOT prospective scientific generalization.
"""
from fractions import Fraction
from pathlib import Path
import importlib.util

_f9_path=Path(__file__).resolve().parents[1]/"f9_learned_timing"/"policy.py"
_spec=importlib.util.spec_from_file_location("f10_frozen_f9_public",_f9_path)
_f9=importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_f9)
public_start=_f9.public_start
EPISODES=(0,1,3,5,7)
PROBES=(3,5,7)
NONANCHORS=tuple(range(2,16))
TRAIN=(67204,67205)
CHECK=(67206,67207)
PAIRS=((8,10),(11,13))
SCHEMA="forge.f10.frozen-public-value-estimator.v1"
MODEL_STATUS="PREVIOUSLY_USED_F3_TRAIN_ONLY_NOT_SCIENCE"

def fail_if(condition,code):
    if condition:raise ValueError("F10_PUBLIC_"+code)

def calibration(history):
    fail_if(not all(t in history for t in (0,1)),"CALIBRATION")
    a=history[0]
    b=history[1]
    fail_if(set(a)!=set((0,1)) or set(b)!=set((0,1)),
            "ANCHOR_IDENTITY")
    base=a[0]
    slope=(a[1]-base)%16
    velocity=(b[0]-base)%16
    fail_if(slope%2!=1 or b[1]!=(base+slope+velocity)%16,
            "ANCHOR_FIDELITY")
    return base,slope,velocity

def anomaly(history,t,cell,value):
    base,slope,velocity=calibration(history)
    inferred=(pow(slope,-1,16)*(value-base-t*velocity))%16
    return int(inferred!=cell)

def prior_anomaly(history,t):
    # This variable is computed from ALREADY OBSERVED nonanchor reads only.
    return int(any(anomaly(history,old,cell,value)
                   for old in PROBES if old<t and old in history
                   for cell,value in history[old].items()))

def model_identity(model):
    fail_if(type(model) is not dict or model.get("schema")!=SCHEMA
            or model.get("status")!=MODEL_STATUS
            or model.get("source_commit")!="5797a257a75fe139313e8486cd1a1ae79c44b148"
            or model.get("train_seeds")!=list(TRAIN)
            or model.get("validation_seeds")!=list(CHECK)
            or model.get("public_scalar_reads")!=10
            or model.get("retained_limit")!=9
            or model.get("first_use_claims")!=0
            or model.get("scientific_dispatch_authorized") is not False,
            "INVALID_FROZEN_MODEL")
    table=model.get("table")
    fail_if(type(table) is not list or len(table)!=3*2*14,
            "INCOMPLETE_VALUE_TABLE")
    for index,row in enumerate(table):
        t=PROBES[index//28]
        flag=(index//14)%2
        offset=index%14
        fail_if(row.get("episode")!=t or row.get("prior_anomaly")!=flag or
                row.get("offset")!=offset or
                type(row.get("observations")) is not int or
                type(row.get("anomalies")) is not int or
                not 0<=row["anomalies"]<=row["observations"],
                "VALUE_TABLE_DRIFT")

def choose(t,history,model):
    model_identity(model)
    fail_if(type(t) is not int or t not in EPISODES,"TIME")
    fail_if(type(history) is not dict or sorted(history)!=
            [e for e in EPISODES if e<t],"FUTURE_OR_MISSING_HISTORY")
    for e,measurements in history.items():
        fail_if(type(measurements) is not dict or len(measurements)!=2 or
                any(type(cell) is not int or cell not in range(16)
                    or type(v) is not int or v not in range(16)
                    for cell,v in measurements.items()),"NONPUBLIC_OR_INVALID")
    if t in (0,1):
        return (0,1)
    start=public_start(history)
    flag=prior_anomaly(history,t)
    used={c for old in PROBES if old<t and old in history
          for c in history[old]}
    candidates=[]
    for cell in NONANCHORS:
        if cell in used:continue
        offset=(cell-2-start)%14
        row=model["table"][PROBES.index(t)*28+flag*14+offset]
        n=row["observations"]
        yes=row["anomalies"]
        # Posterior mean from Beta(1,1), and expected reduction of
        # squared uncertainty if this Bernoulli outcome were observed.
        # Exact rational arithmetic guarantees deterministic ties.
        value=Fraction((yes+1)*(n-yes+1),(n+2)*(n+2))
        candidates.append((value,cell))
    fail_if(len(candidates)<2,"SENSOR_EXHAUSTED")
    candidates.sort(key=lambda x:(-x[0],x[1]))
    return tuple(cell for _,cell in candidates[:2])

def trace_review(history,model):
    fail_if(type(history) is not dict or sorted(history)!=list(EPISODES),
            "READ_TRACE_SHAPE")
    prior={}
    for t in EPISODES:
        expected=choose(t,prior,model)
        fail_if(tuple(history[t])!=expected,"CAUSAL_SENSOR_DECISION")
        prior[t]=history[t]
    cells=[cell for t in PROBES for cell in history[t]]
    fail_if(len(cells)!=len(set(cells)) or len(cells)!=6 or
            sum(len(x) for x in history.values())!=10,"BUDGET")
    return {"reads":10,"distinct_nonanchors":6,
            "addresses":[list(history[t]) for t in EPISODES],
            "public_start":public_start(history),
            "anomaly_after_3":prior_anomaly(history,5),
            "anomaly_after_5":prior_anomaly(history,7)}
