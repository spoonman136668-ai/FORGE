"""F4 equal-decoder scientific-worker integration, engineering qualification only.

The F4 proposed first-use cohorts MUST NOT be passed to this module until an
externally authenticated all-lane ledger has proved their eligibility. This
fixture works exclusively on historical F3 DEVELOPMENT seeds, already used
for engineering. No source mutation, first-use, or F4 scientific original.
"""
from __future__ import annotations
from contextlib import contextmanager
from collections import Counter
import importlib.util
from pathlib import Path
import subprocess

Y070_COMMIT="5797a257a75fe139313e8486cd1a1ae79c44b148"
Y070_PATH="research/contrib/chatgpt/20261013-y070-onset1/execute.py"
PUBLIC_EPISODES=(0,1,3,5,7)
BUDGET=10
F3_DEV_USED=(67204,67205,67206,67207)
CONTROL=((0,1),(0,1),(0,1),(2,4),(2,4))
# Purely mechanical positive and order controls: NOT a development-trained F4 model.
SET_FIXTURE=((0,1),(0,1),(0,1),(8,11),(0,1))
ORDER_FIXTURE=((0,1),(0,1),(0,1),(0,1),(8,11))
ARMS={"F4-CONTROL":CONTROL,"F4-SET":SET_FIXTURE,"F4-ORDER-CONTROL":ORDER_FIXTURE}

def _git(root,*args):
    return subprocess.check_output(["git","-C",str(root),*args],stderr=subprocess.DEVNULL).decode().strip()

def load_pinned(root):
    root=Path(root).resolve(strict=True)
    if _git(root,"rev-parse","HEAD")!=Y070_COMMIT or _git(root,"status","--porcelain"):
        raise ValueError("F4_PINNED_SOURCE_IDENTITY_DRIFT")
    if _git(root,"ls-files","--error-unmatch",Y070_PATH)!=Y070_PATH:
        raise ValueError("F4_PINNED_WORKER_PATH")
    spec=importlib.util.spec_from_file_location("f4_immutable_y070",root/Y070_PATH)
    if spec is None or spec.loader is None:
        raise ValueError("F4_PINNED_IMPORT")
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def validate_schedule(schedule):
    if type(schedule) not in (tuple,list) or len(schedule)!=5:
        raise ValueError("F4_SCHEDULE_SHAPE")
    result=[]
    for pair in schedule:
        if type(pair) not in (tuple,list) or len(pair)!=2:
            raise ValueError("F4_TWO_READS_PER_PROBE")
        if any(type(x) is not int or not 0<=x<16 for x in pair) or pair[0]==pair[1]:
            raise ValueError("F4_PUBLIC_SENSOR_ID")
        result.append(tuple(pair))
    if tuple(result[:3])!=CONTROL[:3]:
        raise ValueError("F4_CALIBRATION_CHANGED")
    if sum(len(p) for p in result)!=10:
        raise ValueError("F4_PUBLIC_BUDGET")
    return tuple(result)

def decoder(observed,episode):
    """One common decoder for all three arms, only previously read public data."""
    b0=observed[0]["0"]
    a=(observed[0]["1"]-b0)%16
    d=(observed[1]["0"]-b0)%16
    if a%2!=1 or observed[1]["1"]!=(b0+d+a)%16:
        raise ValueError("F4_PUBLIC_CALIBRATION_INVALID")
    inv=pow(a,-1,16)
    detected={}
    first=None
    for probed in (5,7):
        if probed>episode:break
        for label,value in observed[probed].items():
            cell=int(label)
            if cell in (0,1):continue
            inferred=(inv*(value-(b0+probed*d)))%16
            if inferred==cell:continue
            if inferred in (0,1):
                raise ValueError("F4_UNQUALIFIED_ANCHOR_INFERENCE")
            proposal={cell:inferred,inferred:cell}
            if detected and proposal!=detected:
                raise ValueError("F4_UNQUALIFIED_SECOND_SWAP")
            detected=proposal
            if first is None:first=probed
    return {"a":a,"b0":b0,"d":d,"inverse":inv,
            "detected_pair":detected,"first_detection_episode":first}

def verify_comparators(arms=ARMS):
    if set(arms)!={"F4-CONTROL","F4-SET","F4-ORDER-CONTROL"}:
        raise ValueError("F4_ARM_ID_DRIFT")
    validated={k:validate_schedule(v) for k,v in arms.items()}
    if validated["F4-CONTROL"]!=CONTROL:
        raise ValueError("F4_BASELINE_CHANGED")
    if Counter(x for pair in validated["F4-SET"] for x in pair)!=Counter(
            x for pair in validated["F4-ORDER-CONTROL"] for x in pair):
        raise ValueError("F4_ORDER_CONTROL_NOT_SENSOR_SET_MATCHED")
    if validated["F4-SET"]==validated["F4-ORDER-CONTROL"]:
        raise ValueError("F4_ORDER_CONTROL_NOT_DISTINCT")
    return validated

@contextmanager
def install_equal_decoder_and_sampler(y070,schedule,audit):
    """Intercept the actual Y065 sensor transport and Y060 decoder boundary."""
    schedule=validate_schedule(schedule)
    m=y070.m
    native_sample=m.y64.dual_public_samples
    native_decode=m.y61.y60.public_decoder
    def public_samples(seed,family):
        readings={}
        for episode,pair in zip(PUBLIC_EPISODES,schedule):
            readings[episode]={str(cell):m.y64.y46.coordinate(
                cell,seed,episode,family,"late_shock") for cell in pair}
        if sum(len(v) for v in readings.values())!=10:
            raise ValueError("F4_PUBLIC_OBSERVATION_BUDGET")
        audit.append([[int(c) for c in readings[ep]] for ep in PUBLIC_EPISODES])
        return readings
    try:
        m.y64.dual_public_samples=public_samples
        m.y61.y60.public_decoder=decoder
        yield
    finally:
        m.y64.dual_public_samples=native_sample
        m.y61.y60.public_decoder=native_decode

def score_case(y070,seed,pair,onset,family,policy,arm):
    if seed not in F3_DEV_USED:
        raise ValueError("F4_NO_NEW_COHORT_TRAIN_OR_FIRST_USE")
    schedules=verify_comparators()
    if arm not in schedules:raise ValueError("F4_UNKNOWN_ARM")
    m=y070.m
    # Evaluator-only shock configuration; never passed to either sampling or decoder.
    m.y58.install_transposition(onset,pair,{"anchor_pair_checks":0})
    try:
        reference=m.y50.evaluate(seed,policy,"canonical","continue",family)
        audit=[]
        with install_equal_decoder_and_sampler(y070,schedules[arm],audit):
            trial=m.candidate(seed,family,policy,"dual_sentinel_decoder_corrected")
        if len(audit)!=1 or audit[0]!=[list(x) for x in schedules[arm]]:
            raise ValueError("F4_PUBLIC_HOOK_NOT_CALLED")
        if trial["public_scalar_reads"]!=10 or len(trial["rows"])!=8 or len(reference["rows"])!=8:
            raise ValueError("F4_READ_OR_EPISODE_BUDGET")
        first=trial["rows"][-1]["public_detected_swap_first_episode"]
        pre=post=0
        for truth,row in zip(reference["rows"],trial["rows"]):
            if truth["episode"]!=row["episode"] or row["illegal_physical_assignments"]!=0:
                raise ValueError("F4_ILLEGAL_PHYSICAL_ASSIGNMENT")
            if len(row["physical_assignment_evaluator_only"])!=7 or row["candidate_retained_cache_occupancy"]>9:
                raise ValueError("F4_RETAINED_CAPACITY")
            wrong=int(any(truth["physical_assignment"][k]!=row["physical_assignment_evaluator_only"][k]
                          for k in truth["physical_assignment"]))
            if first is None or row["episode"]<first:pre+=wrong
            else:post+=wrong
        return {"arm":arm,"seed":seed,"pair":list(pair),"onset":onset,
                "family":list(family),"policy":policy,"first_detection":first,
                "pre":pre,"post":post,"reads":10,"public_sensor_trace":audit[0],
                "decoder_identity":"F4-PUBLIC-DECODER-V1"}
    finally:
        m.y49.restore_environment()
