"""Real, pinned Y070 F9 public-order worker, F3-used cohorts only.

The evaluator installs the hidden transposition outside the sensor policy.
The chooser receives only past public observations, time and fitted rule.
Nothing here requests or issues scientific first-use authority.
"""
from contextlib import contextmanager
import importlib.util
from pathlib import Path
import subprocess
from policy import (TRAIN_SEEDS,VALIDATION_SEEDS,PAIRS,RULES,EPISODES,
                    choose,trace_audit,f8)

SOURCE_COMMIT="5797a257a75fe139313e8486cd1a1ae79c44b148"
SOURCE_PATH="research/contrib/chatgpt/20261013-y070-onset1/execute.py"
SEEDS=TRAIN_SEEDS+VALIDATION_SEEDS

def load_source(root):
    root=Path(root).resolve(strict=True)
    def git(*args):
        return subprocess.check_output(["git","-C",str(root),*args],
                                       stderr=subprocess.DEVNULL).decode().strip()
    if git("rev-parse","HEAD")!=SOURCE_COMMIT or git("status","--porcelain"):
        raise ValueError("F9_IMMUTABLE_Y070_SOURCE_DRIFT")
    if git("ls-files","--error-unmatch",SOURCE_PATH)!=SOURCE_PATH:
        raise ValueError("F9_PINNED_SOURCE_PATH_DRIFT")
    spec=importlib.util.spec_from_file_location("f9_original_y070",root/SOURCE_PATH)
    if spec is None or spec.loader is None:
        raise ValueError("F9_PARENT_SOURCE_MISSING")
    source=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(source)
    return source

@contextmanager
def installed(source,rule,trace):
    if rule not in RULES:
        raise ValueError("F9_UNFROZEN_RULE")
    m=source.m
    previous_sampler=m.y64.dual_public_samples
    previous_decoder=m.y61.y60.public_decoder
    def sampler(seed,family):
        history={}
        for episode in EPISODES:
            sensors=choose(episode,history,rule)
            history[episode]={cell:m.y64.y46.coordinate(
                cell,seed,episode,family,"late_shock") for cell in sensors}
        verified=trace_audit(rule,history)
        trace.append({"addresses":[list(history[t]) for t in EPISODES],
                      "public_values":[[history[t][cell] for cell in history[t]]
                                       for t in EPISODES],
                      "decision":verified})
        return {t:{str(c):v for c,v in row.items()} for t,row in history.items()}
    try:
        m.y64.dual_public_samples=sampler
        m.y61.y60.public_decoder=f8.common_decoder
        yield
    finally:
        m.y64.dual_public_samples=previous_sampler
        m.y61.y60.public_decoder=previous_decoder

def evaluate(source,seed,pair,regime,family,matching_policy,rule):
    if type(seed) is not int or seed not in SEEDS:
        raise ValueError("F9_NEW_FIRST_USE_OR_SEED_REFUSED")
    if tuple(pair) not in PAIRS or regime not in ("steady","onset1"):
        raise ValueError("F9_NEW_PAIR_OR_REGIME_REFUSED")
    if rule not in RULES:
        raise ValueError("F9_UNFROZEN_POLICY_REFUSED")
    if family not in source.FAMILIES or matching_policy not in source.POLICIES:
        raise ValueError("F9_FAMILY_OR_POLICY_DRIFT")
    m=source.m
    m.y58.install_transposition(None if regime=="steady" else 1,pair,
                                {"anchor_pair_checks":0})
    try:
        baseline=m.y50.evaluate(seed,matching_policy,"canonical","continue",family)
        trace=[]
        with installed(source,rule,trace):
            candidate=m.candidate(seed,family,matching_policy,
                                  "dual_sentinel_decoder_corrected")
        if len(trace)!=1 or candidate["public_scalar_reads"]!=10 or (
                len(candidate["rows"])!=len(baseline["rows"])):
            raise ValueError("F9_PUBLIC_SOURCE_NOT_ACTUALLY_EXECUTED")
        first=candidate["rows"][-1]["public_detected_swap_first_episode"]
        pre=post=0
        for truth,row in zip(baseline["rows"],candidate["rows"]):
            if truth["episode"]!=row["episode"] or (
                    row["illegal_physical_assignments"]!=0):
                raise ValueError("F9_INVALID_MATCHING")
            if row["candidate_retained_cache_occupancy"]>9 or (
                    len(row["physical_assignment_evaluator_only"])!=7):
                raise ValueError("F9_NATIVE_RETAINED_BUDGET")
            wrong=int(any(truth["physical_assignment"][k]!=
                          row["physical_assignment_evaluator_only"][k]
                          for k in truth["physical_assignment"]))
            if first is None or row["episode"]<first:pre+=wrong
            else:post+=wrong
        return {"seed":seed,"pair":list(pair),"regime":regime,
                "family":list(family),"matching_policy":matching_policy,
                "rule":rule,"first_detection":first,
                "pre_mismatch":pre,"post_mismatch":post,
                "public_reads":10,"decoder":"F7-COMMON-PUBLIC-EARLY-V1",
                "sample_trace":trace[0]}
    finally:
        m.y49.restore_environment()
