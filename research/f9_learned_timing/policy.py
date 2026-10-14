"""F9 learned *bounded* schedule choice from prior public anchor observations.

Train a finite, predeclared rule bank on already-used F3 development data.
Inference receives ONLY (episode, earlier public coordinate values, frozen
rule). Rule choice occurs after calibration episodes 0 and 1, before any
nonanchor reading at episode 3. Six identical physical sensor positions and
ten reads in every arm, using F8's immutable same-set timing comparator.
No seed, source family, true swap, onset, future query, reward or holdout
is an input to policy inference.
"""
import importlib.util
from pathlib import Path

PARENT=Path(__file__).resolve().parents[1]/"f8_matched_timing"/"schedule.py"
spec=importlib.util.spec_from_file_location("f9_frozen_f8_schedule",PARENT)
f8=importlib.util.module_from_spec(spec)
spec.loader.exec_module(f8)

EPISODES=(0,1,3,5,7)
TRAIN_SEEDS=(67204,67205)
VALIDATION_SEEDS=(67206,67207)
PAIRS=((8,10),(11,13))
RULES=(
 "ALWAYS_EARLY",
 "ALWAYS_SWAP",
 "START_EVEN_EARLY",
 "START_ODD_EARLY",
 "START_LT7_EARLY",
 "START_GE7_EARLY",
 "START_MOD3_ZERO_EARLY",
 "START_MOD3_NONZERO_EARLY",
)
RULE_ORDER={rule:index for index,rule in enumerate(RULES)}
NEXT_ID="Y-FORGE-F9-LEARNED-PUBLIC-OBSERVATION-ORDER-PROPOSAL"

def must(ok,why):
    if not ok:raise ValueError("F9_PUBLIC_"+why)

def public_start(history):
    # Compute exclusively from observed calibration, using F8's exact
    # source rule. No evaluator-supplied start/candidate label.
    must(type(history) is dict and all(t in history for t in (0,1)),
         "PUBLIC_CALIBRATION_MISSING")
    for t in (0,1):
        must(type(history[t]) is dict and set(history[t])=={0,1} and
             all(type(v) is int and 0<=v<16 for v in history[t].values()),
             "CALIBRATION_SHAPE")
    f8.f7.calibration(history)
    return f8.f7.public_start(history)

def choose_branch(rule,history):
    must(rule in RULES,"RULE_NOT_FROZEN")
    s=public_start(history)
    return {
        "ALWAYS_EARLY":True,
        "ALWAYS_SWAP":False,
        "START_EVEN_EARLY":s%2==0,
        "START_ODD_EARLY":s%2!=0,
        "START_LT7_EARLY":s<7,
        "START_GE7_EARLY":s>=7,
        "START_MOD3_ZERO_EARLY":s%3==0,
        "START_MOD3_NONZERO_EARLY":s%3!=0,
    }[rule]

def choose(episode,history,rule):
    must(rule in RULES,"RULE_NOT_FROZEN")
    must(type(episode) is int and episode in EPISODES,"EPISODE")
    must(type(history) is dict and sorted(history)==
         [t for t in EPISODES if t<episode],"FUTURE_OR_MISSING_PUBLIC_INPUT")
    if episode in (0,1):
        return f8.choose(f8.ARMS[0],episode,history)
    early=choose_branch(rule,history)
    arm=f8.ARMS[0] if early else f8.ARMS[1]
    return f8.choose(arm,episode,history)

def trace_audit(rule,history):
    must(type(history) is dict and sorted(history)==list(EPISODES),
         "TRACE_SCOPE")
    prior={}
    for t in EPISODES:
        addresses=choose(t,prior,rule)
        must(tuple(history[t])==addresses,"CAUSAL_SELECTION_OR_SOURCE_DRIFT")
        prior[t]=history[t]
    six=[cell for t in (3,5,7) for cell in history[t]]
    must(len(six)==len(set(six))==6 and
         all(c in range(2,16) for c in six) and
         sum(len(reads) for reads in history.values())==10,
         "SAME_SET_TEN_READ_CAPACITY")
    base=choose_branch(rule,{0:history[0],1:history[1]})
    return {"rule":rule,"public_start":public_start(history),
            "decision":"EARLY" if base else "SWAP",
            "physical_nonanchor_set":sorted(six),
            "reads":10,"distinct_nonanchor_cells":6}
