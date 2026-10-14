"""F11 pinned real-Y070 task-value training / validation evaluator.

The public sampling policy sees episode, prior measured public values, and
frozen model only. The source/evaluator holds hidden swap, seed, family
and task losses outside the policy. Only previously consumed F3 seeds
67204..67207 and pairs [8,10]/[11,13] are allowed.
"""
import importlib.util,subprocess
from contextlib import contextmanager
from pathlib import Path
from policy import (TRAIN_SEEDS,TEST_SEEDS,PAIRS,EPISODES,choose,audit,
                    validate_model,decoder,ORDERS)

SOURCE_COMMIT="5797a257a75fe139313e8486cd1a1ae79c44b148"
SOURCE_PATH="research/contrib/chatgpt/20261013-y070-onset1/execute.py"

def load_source(root):
    root=Path(root).resolve(strict=True)
    def git(*args):
        return subprocess.check_output(["git","-C",str(root),*args],
                stderr=subprocess.DEVNULL).decode().strip()
    if git("rev-parse","HEAD")!=SOURCE_COMMIT or git("status","--porcelain"):
        raise ValueError("F11_PINNED_ORIGINAL_SOURCE_DRIFT")
    if git("ls-files","--error-unmatch",SOURCE_PATH)!=SOURCE_PATH:
        raise ValueError("F11_PINNED_SOURCE_PATH")
    spec=importlib.util.spec_from_file_location("f11_y070_pinned_original",root/SOURCE_PATH)
    if not spec or not spec.loader:raise ValueError("F11_SOURCE_MISSING")
    obj=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj

@contextmanager
def install(source,model,trace,arm):
    validate_model(model)
    if arm!="LEARNED" and (type(arm) is not int or arm not in range(6)):
        raise ValueError("F11_UNQUALIFIED_ACTION")
    override=None if arm=="LEARNED" else arm
    m=source.m
    old_sampler=m.y64.dual_public_samples
    old_decoder=m.y61.y60.public_decoder
    def sampler(seed,family):
        h={}
        for episode in EPISODES:
            loc=choose(episode,h,model,override)
            h[episode]={cell:m.y64.y46.coordinate(
                cell,seed,episode,family,"late_shock") for cell in loc}
        attestation=audit(h,model,override)
        trace.append({"addresses":[list(h[t]) for t in EPISODES],
                      "public_values":[[h[t][cell] for cell in h[t]]
                                       for t in EPISODES],
                      "decision":attestation})
        return {t:{str(cell):v for cell,v in h[t].items()} for t in EPISODES}
    try:
        m.y64.dual_public_samples=sampler
        m.y61.y60.public_decoder=decoder
        yield
    finally:
        m.y64.dual_public_samples=old_sampler
        m.y61.y60.public_decoder=old_decoder

def evaluate(source,model,seed,pair,regime,family,matching,arm):
    if type(seed) is not int or seed not in TRAIN_SEEDS+TEST_SEEDS:
        raise ValueError("F11_NEW_OR_UNAUTHORIZED_FIRST_USE")
    if tuple(pair) not in PAIRS or regime not in ("steady","onset1"):
        raise ValueError("F11_NEW_PAIR_OR_REGIME")
    if arm!="LEARNED" and (type(arm) is not int or arm not in range(6)):
        raise ValueError("F11_UNDECLARED_ACTION")
    if family not in source.FAMILIES or matching not in source.POLICIES:
        raise ValueError("F11_SOURCE_FAMILY_OR_MATCHING")
    validate_model(model)
    m=source.m
    m.y58.install_transposition(None if regime=="steady" else 1,pair,
                                {"anchor_pair_checks":0})
    try:
        reference=m.y50.evaluate(seed,matching,"canonical","continue",family)
        readings=[]
        with install(source,model,readings,arm):
            output=m.candidate(seed,family,matching,
                               "dual_sentinel_decoder_corrected")
        if len(readings)!=1 or output["public_scalar_reads"]!=10 or (
                len(output["rows"])!=len(reference["rows"])):
            raise ValueError("F11_SOURCE_HOOK_NOT_EXECUTED")
        first=output["rows"][-1]["public_detected_swap_first_episode"]
        before=after=0
        for expected,row in zip(reference["rows"],output["rows"]):
            if expected["episode"]!=row["episode"] or row["illegal_physical_assignments"]!=0:
                raise ValueError("F11_INVALID_MATCHING")
            if row["candidate_retained_cache_occupancy"]>9 or (
                len(row["physical_assignment_evaluator_only"])!=7):
                raise ValueError("F11_RETAINED_ACTIVE_BUDGET")
            mismatch=int(any(expected["physical_assignment"][cell]!=
                   row["physical_assignment_evaluator_only"][cell]
                   for cell in expected["physical_assignment"]))
            if first is None or row["episode"]<first:before+=mismatch
            else:after+=mismatch
        return {"arm":arm,"seed":seed,"pair":list(pair),"regime":regime,
                "family":list(family),"matching_policy":matching,
                "pre_mismatch":before,"post_mismatch":after,
                "first_detection":first,"public_reads":10,
                "decoder":"F7-COMMON-PUBLIC-EARLY-V1","sample_trace":readings[0]}
    finally:
        m.y49.restore_environment()
