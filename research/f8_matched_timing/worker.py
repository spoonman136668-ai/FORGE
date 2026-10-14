"""F8 real pinned Y070 timing-order ablation on already-consumed F3 seeds.

No fresh or sealed F8 data. Identical six physical sensor addresses and
decoder across two arms, matched on each original source episode.
"""
from contextlib import contextmanager
from pathlib import Path
import importlib.util
import subprocess
from schedule import ARMS,EPISODES,choose,validate_trace,matched_sets,common_decoder

SOURCE_COMMIT="5797a257a75fe139313e8486cd1a1ae79c44b148"
SOURCE_PATH="research/contrib/chatgpt/20261013-y070-onset1/execute.py"
SEEDS=(67206,67207)
PAIRS=((8,10),(11,13))

def load_source(root):
    root=Path(root).resolve(strict=True)
    def git(*args):
        return subprocess.check_output(["git","-C",str(root),*args],
                                       stderr=subprocess.DEVNULL).decode().strip()
    if git("rev-parse","HEAD")!=SOURCE_COMMIT or git("status","--porcelain"):
        raise ValueError("F8_IMMUTABLE_Y070_SOURCE_DRIFT")
    if git("ls-files","--error-unmatch",SOURCE_PATH)!=SOURCE_PATH:
        raise ValueError("F8_PINNED_SOURCE_PATH_DRIFT")
    spec=importlib.util.spec_from_file_location("f8_original_y070",root/SOURCE_PATH)
    if spec is None or spec.loader is None:
        raise ValueError("F8_PARENT_SOURCE_MISSING")
    source=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(source)
    return source

@contextmanager
def installed(source,arm,trace):
    if arm not in ARMS:raise ValueError("F8_UNKNOWN_ARM")
    m=source.m
    previous_sampler=m.y64.dual_public_samples
    previous_decoder=m.y61.y60.public_decoder
    def public_sampler(seed,family):
        history={}
        for time in EPISODES:
            chosen=choose(arm,time,history)
            history[time]={cell:m.y64.y46.coordinate(
                cell,seed,time,family,"late_shock") for cell in chosen}
        inspected=validate_trace(arm,history)
        trace.append({
            "addresses":[list(history[t]) for t in EPISODES],
            "public_values":[[history[t][a] for a in history[t]] for t in EPISODES],
            "budget":inspected
        })
        return {t:{str(c):v for c,v in reads.items()} for t,reads in history.items()}
    try:
        m.y64.dual_public_samples=public_sampler
        m.y61.y60.public_decoder=common_decoder
        yield
    finally:
        m.y64.dual_public_samples=previous_sampler
        m.y61.y60.public_decoder=previous_decoder

def evaluate(source,seed,pair,regime,family,matching_policy,arm):
    if seed not in SEEDS:
        raise ValueError("F8_FRESH_OR_TRAINING_SEED_REFUSED")
    if tuple(pair) not in PAIRS or regime not in ("steady","onset1"):
        raise ValueError("F8_NEW_PAIR_OR_REGIME_REFUSED")
    if arm not in ARMS:
        raise ValueError("F8_UNKNOWN_ARM")
    if family not in source.FAMILIES or matching_policy not in source.POLICIES:
        raise ValueError("F8_UNQUALIFIED_SOURCE_POLICY")
    m=source.m
    m.y58.install_transposition(None if regime=="steady" else 1,
                                pair,{"anchor_pair_checks":0})
    try:
        truth=m.y50.evaluate(seed,matching_policy,"canonical","continue",family)
        trace=[]
        with installed(source,arm,trace):
            result=m.candidate(seed,family,matching_policy,
                               "dual_sentinel_decoder_corrected")
        if len(trace)!=1 or result["public_scalar_reads"]!=10 or len(result["rows"])!=len(truth["rows"]):
            raise ValueError("F8_ACTUAL_MATCHING_HOOK_OR_BUDGET")
        first=result["rows"][-1]["public_detected_swap_first_episode"]
        pre=post=0
        for expected,row in zip(truth["rows"],result["rows"]):
            if expected["episode"]!=row["episode"] or row["illegal_physical_assignments"]!=0:
                raise ValueError("F8_PHYSICAL_ASSIGNMENT")
            if row["candidate_retained_cache_occupancy"]>9 or len(row["physical_assignment_evaluator_only"])!=7:
                raise ValueError("F8_RETAINED_CAPACITY")
            different=int(any(expected["physical_assignment"][k]!=row["physical_assignment_evaluator_only"][k]
                              for k in expected["physical_assignment"]))
            if first is None or row["episode"]<first:pre+=different
            else:post+=different
        return {"arm":arm,"seed":seed,"pair":list(pair),"regime":regime,
                "family":list(family),"matching_policy":matching_policy,
                "first_detection":first,"pre_mismatch":pre,"post_mismatch":post,
                "public_reads":10,"decoder":"F7-COMMON-PUBLIC-EARLY-V1",
                "sample_trace":trace[0]}
    finally:
        m.y49.restore_environment()
