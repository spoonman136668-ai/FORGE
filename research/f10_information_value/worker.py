"""Run F10's frozen learned information-value estimator in real Y070.

The selector receives only the past public values, episode and frozen
training-derived weights. The swap/seed/family stay outside the selector.
All runs restricted to already-consumed F3 validation seeds.
"""
import importlib.util
import subprocess
from contextlib import contextmanager
from pathlib import Path
from policy import CHECK,PAIRS,EPISODES,choose,trace_review,model_identity

SOURCE_COMMIT="5797a257a75fe139313e8486cd1a1ae79c44b148"
SOURCE_PATH="research/contrib/chatgpt/20261013-y070-onset1/execute.py"

def load_source(root):
    root=Path(root).resolve(strict=True)
    def git(*args):
        return subprocess.check_output(["git","-C",str(root),*args],
                                       stderr=subprocess.DEVNULL).decode().strip()
    if git("rev-parse","HEAD")!=SOURCE_COMMIT or git("status","--porcelain"):
        raise ValueError("F10_PINNED_Y070_SOURCE_DRIFT")
    if git("ls-files","--error-unmatch",SOURCE_PATH)!=SOURCE_PATH:
        raise ValueError("F10_PINNED_SOURCE_PATH_DRIFT")
    spec=importlib.util.spec_from_file_location("f10_y070_frozen_source",root/SOURCE_PATH)
    if not spec or not spec.loader:raise ValueError("F10_SOURCE_MISSING")
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

@contextmanager
def install(source,model,records):
    model_identity(model)
    m=source.m
    old_sampler=m.y64.dual_public_samples
    old_decoder=m.y61.y60.public_decoder
    # Import the public decoder from frozen F8 source, not mutable policy.
    f8path=Path(__file__).resolve().parents[1]/"f8_matched_timing"/"schedule.py"
    spec=importlib.util.spec_from_file_location("f10_immutable_f8_decoder",f8path)
    f8=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(f8)
    def sampler(seed,family):
        history={}
        for t in EPISODES:
            cells=choose(t,history,model)
            history[t]={c:m.y64.y46.coordinate(
                c,seed,t,family,"late_shock") for c in cells}
        decision=trace_review(history,model)
        records.append({"addresses":[list(history[t]) for t in EPISODES],
                        "public_values":[[history[t][c] for c in history[t]]
                                         for t in EPISODES],
                        "decision":decision})
        return {t:{str(c):v for c,v in history[t].items()} for t in EPISODES}
    try:
        m.y64.dual_public_samples=sampler
        m.y61.y60.public_decoder=f8.common_decoder
        yield
    finally:
        m.y64.dual_public_samples=old_sampler
        m.y61.y60.public_decoder=old_decoder

def evaluate(source,model,seed,pair,regime,family,matching_policy):
    if type(seed) is not int or seed not in CHECK:
        raise ValueError("F10_NEW_FIRST_USE_OR_TRAINING_SEED_REFUSED")
    if tuple(pair) not in PAIRS or regime not in ("steady","onset1"):
        raise ValueError("F10_UNINSPECTED_PAIR_OR_REGIME_REFUSED")
    if family not in source.FAMILIES or matching_policy not in source.POLICIES:
        raise ValueError("F10_SOURCE_MATCHING_OR_FAMILY_DRIFT")
    model_identity(model)
    m=source.m
    m.y58.install_transposition(None if regime=="steady" else 1,
                                pair,{"anchor_pair_checks":0})
    try:
        truth=m.y50.evaluate(seed,matching_policy,"canonical","continue",family)
        trace=[]
        with install(source,model,trace):
            actual=m.candidate(seed,family,matching_policy,
                               "dual_sentinel_decoder_corrected")
        if len(trace)!=1 or actual["public_scalar_reads"]!=10 or (
                len(actual["rows"])!=len(truth["rows"])):
            raise ValueError("F10_REAL_SOURCE_PUBLIC_HOOK")
        first=actual["rows"][-1]["public_detected_swap_first_episode"]
        pre=post=0
        for ground,row in zip(truth["rows"],actual["rows"]):
            if ground["episode"]!=row["episode"] or row["illegal_physical_assignments"]!=0:
                raise ValueError("F10_ILLEGAL_PHYSICAL_ASSIGNMENT")
            if row["candidate_retained_cache_occupancy"]>9 or (
                    len(row["physical_assignment_evaluator_only"])!=7):
                raise ValueError("F10_ACTIVE_RETAINED_LIMIT")
            mismatch=int(any(ground["physical_assignment"][c]!=
                             row["physical_assignment_evaluator_only"][c]
                             for c in ground["physical_assignment"]))
            if first is None or row["episode"]<first:pre+=mismatch
            else:post+=mismatch
        return {"arm":"F10-EXPECTED-PUBLIC-VALUE","seed":seed,
                "pair":list(pair),"regime":regime,"family":list(family),
                "matching_policy":matching_policy,"public_reads":10,
                "decoder":"F7-COMMON-PUBLIC-EARLY-V1",
                "pre_mismatch":pre,"post_mismatch":post,
                "first_detection":first,"sample_trace":trace[0]}
    finally:
        m.y49.restore_environment()
