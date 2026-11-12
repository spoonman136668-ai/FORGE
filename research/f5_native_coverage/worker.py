"""Source-pinned F5 interface to real Y070 matching; historical engineering only.

The trial policy receives ONLY the public sample stream, not the evaluator
pair, seed, family, or true onset. The scientific evaluator installs the
environment separately. Equal generalized public-only decoder for every arm.
"""
from contextlib import contextmanager
from pathlib import Path
import importlib.util
import subprocess
from policy import POLICIES,PROBES,choose,audit_trace

SOURCE_COMMIT="5797a257a75fe139313e8486cd1a1ae79c44b148"
SOURCE_PATH="research/contrib/chatgpt/20261013-y070-onset1/execute.py"
HISTORICAL_DEV=(67204,67205,67206,67207)
HISTORICAL_PAIRS=((8,10),(11,13))

def git(root,*args):
    return subprocess.check_output(["git","-C",str(root),*args],stderr=subprocess.DEVNULL).decode().strip()

def load_source(root):
    root=Path(root).resolve(strict=True)
    if git(root,"rev-parse","HEAD")!=SOURCE_COMMIT or git(root,"status","--porcelain"):
        raise ValueError("F5_IMMUTABLE_SOURCE_DRIFT")
    if git(root,"ls-files","--error-unmatch",SOURCE_PATH)!=SOURCE_PATH:
        raise ValueError("F5_SOURCE_PATH_DRIFT")
    spec=importlib.util.spec_from_file_location("f5_y070_pinned",root/SOURCE_PATH)
    if spec is None or spec.loader is None:raise ValueError("F5_PINNED_SOURCE_UNAVAILABLE")
    source=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(source)
    return source

def decode(public,episode):
    base=public[0][str(0)]
    a=(public[0][str(1)]-base)%16
    d=(public[1][str(0)]-base)%16
    if a%2!=1 or public[1][str(1)]!=(base+a+d)%16:
        raise ValueError("F5_DECODER_PUBLIC_CALIBRATION")
    inv=pow(a,-1,16)
    found={}
    first=None
    for t in (5,7):
        if t>episode:break
        for label,val in public[t].items():
            addr=int(label)
            if addr<2:continue
            inferred=(inv*(val-(base+t*d)))%16
            if inferred==addr:continue
            if inferred<2:raise ValueError("F5_DECODER_NONANCHOR_INFERRED_ANCHOR")
            proposal={addr:inferred,inferred:addr}
            if found and proposal!=found:
                raise ValueError("F5_DECODER_CONFLICTING_SWAPS")
            found=proposal
            if first is None:first=t
    return {"a":a,"b0":base,"d":d,"inverse":inv,
            "detected_pair":found,"first_detection_episode":first}

@contextmanager
def install_public_policy(source,policy,trace):
    if policy not in POLICIES:raise ValueError("F5_UNKNOWN_POLICY")
    m=source.m
    original_sampler=m.y64.dual_public_samples
    original_decoder=m.y61.y60.public_decoder
    def sample(seed,family):
        history={}
        for episode in PROBES:
            pair=choose(policy,episode,history)
            history[episode]={addr:m.y64.y46.coordinate(
                addr,seed,episode,family,"late_shock") for addr in pair}
        audited=audit_trace(policy,history)
        trace.append({"addresses":[list(history[t]) for t in PROBES],
                      "state":audited})
        return {t:{str(c):v for c,v in item.items()} for t,item in history.items()}
    try:
        m.y64.dual_public_samples=sample
        m.y61.y60.public_decoder=decode
        yield
    finally:
        m.y64.dual_public_samples=original_sampler
        m.y61.y60.public_decoder=original_decoder

def evaluate_historical(source,seed,pair,onset,family,matching_policy,arm):
    if seed not in HISTORICAL_DEV:raise ValueError("F5_UNAUTHORIZED_NEW_SEED_OR_FIRST_USE")
    if tuple(pair) not in HISTORICAL_PAIRS:raise ValueError("F5_UNAUTHORIZED_PAIR")
    if arm not in POLICIES:raise ValueError("F5_UNKNOWN_ARM")
    if onset not in (None,1):raise ValueError("F5_UNAUTHORIZED_ONSET")
    if family not in source.FAMILIES or matching_policy not in source.POLICIES:
        raise ValueError("F5_SOURCE_FAMILY_OR_POLICY_DRIFT")
    m=source.m
    m.y58.install_transposition(onset,pair,{"anchor_pair_checks":0})
    try:
        reference=m.y50.evaluate(seed,matching_policy,"canonical","continue",family)
        trace=[]
        with install_public_policy(source,arm,trace):
            output=m.candidate(seed,family,matching_policy,"dual_sentinel_decoder_corrected")
        if len(trace)!=1 or output["public_scalar_reads"]!=10:
            raise ValueError("F5_PUBLIC_INTEGRATION_MISSING")
        if len(output["rows"])!=len(reference["rows"]) or len(trace[0]["addresses"])!=5:
            raise ValueError("F5_SOURCE_TRIAL_SHAPE")
        first=output["rows"][-1]["public_detected_swap_first_episode"]
        pre=post=0
        for truth,row in zip(reference["rows"],output["rows"]):
            if truth["episode"]!=row["episode"] or row["illegal_physical_assignments"]!=0:
                raise ValueError("F5_ILLEGAL_ASSIGNMENT")
            if row["candidate_retained_cache_occupancy"]>9 or len(row["physical_assignment_evaluator_only"])!=7:
                raise ValueError("F5_CAPACITY")
            wrong=int(any(truth["physical_assignment"][k]!=row["physical_assignment_evaluator_only"][k]
                          for k in truth["physical_assignment"]))
            if first is None or row["episode"]<first:pre+=wrong
            else:post+=wrong
        return {"arm":arm,"pair":list(pair),"seed":seed,
                "regime":"steady" if onset is None else "onset1",
                "family":list(family),"matching_policy":matching_policy,
                "first_detection":first,"pre_mismatch":pre,"post_mismatch":post,
                "public_reads":10,"sample_trace":trace[0],
                "decoder":"F5-GENERALIZED-PUBLIC-V1"}
    finally:
        m.y49.restore_environment()
