"""F7 source-pinned real Y070 public-only engineering evaluation.

The trial sampler receives seed/family only to obtain public coordinates;
it passes ONLY the previously read public values and time to F7.select.
True pair and onset exist solely in the external evaluator environment.
Only F3 already-consumed seeds 67206/67207 and original F3 pairs.
"""
import sys
import importlib.util
from pathlib import Path
from contextlib import contextmanager
from policy import POLICIES,READ_TIMES,select,common_decoder,verify_observations

parent_path=Path(__file__).resolve().parents[1]/"f5_native_coverage"/"worker.py"
spec=importlib.util.spec_from_file_location("f7_pinned_source_adapter",parent_path)
parent=importlib.util.module_from_spec(spec)
spec.loader.exec_module(parent)
load_source=parent.load_source
SOURCE_COMMIT=parent.SOURCE_COMMIT
SEEDS=(67206,67207)
PAIRS=((8,10),(11,13))

@contextmanager
def install(source,policy,record):
    if policy not in POLICIES:raise ValueError("F7_UNKNOWN_POLICY")
    m=source.m
    old_sampler=m.y64.dual_public_samples
    old_decoder=m.y61.y60.public_decoder
    def sampler(seed,family):
        history={}
        for time in READ_TIMES:
            addresses=select(policy,time,history)
            history[time]={cell:m.y64.y46.coordinate(
                cell,seed,time,family,"late_shock") for cell in addresses}
        checked=verify_observations(policy,history)
        record.append({"addresses":[list(history[t]) for t in READ_TIMES],
                       "public_values":[[history[t][addr] for addr in history[t]]
                                        for t in READ_TIMES],
                       "coverage":checked})
        return {t:{str(c):v for c,v in hist.items()} for t,hist in history.items()}
    try:
        m.y64.dual_public_samples=sampler
        m.y61.y60.public_decoder=common_decoder
        yield
    finally:
        m.y64.dual_public_samples=old_sampler
        m.y61.y60.public_decoder=old_decoder

def evaluate(source,seed,pair,regime,family,policy,arm):
    if seed not in SEEDS:
        raise ValueError("F7_NEW_SEED_OR_FIRST_USE_REFUSED")
    if tuple(pair) not in PAIRS or regime not in ("steady","onset1"):
        raise ValueError("F7_UNAUTHORIZED_NEW_PAIR_OR_REGIME")
    if arm not in POLICIES:
        raise ValueError("F7_UNAUTHORIZED_ARM")
    if family not in source.FAMILIES or policy not in source.POLICIES:
        raise ValueError("F7_FAMILY_OR_MATCH_POLICY")
    m=source.m
    m.y58.install_transposition(None if regime=="steady" else 1,
                                pair,{"anchor_pair_checks":0})
    try:
        canonical=m.y50.evaluate(seed,policy,"canonical","continue",family)
        record=[]
        with install(source,arm,record):
            observed=m.candidate(seed,family,policy,
                                 "dual_sentinel_decoder_corrected")
        if len(record)!=1 or observed["public_scalar_reads"]!=10:
            raise ValueError("F7_ACTUAL_PUBLIC_HOOK_NOT_EXECUTED")
        first=observed["rows"][-1]["public_detected_swap_first_episode"]
        pre=post=0
        for truth,row in zip(canonical["rows"],observed["rows"]):
            if truth["episode"]!=row["episode"] or (
                    row["illegal_physical_assignments"]!=0):
                raise ValueError("F7_SOURCE_MATCHING")
            if row["candidate_retained_cache_occupancy"]>9 or (
                    len(row["physical_assignment_evaluator_only"])!=7):
                raise ValueError("F7_CAPACITY")
            wrong=int(any(truth["physical_assignment"][k]!=
                          row["physical_assignment_evaluator_only"][k]
                          for k in truth["physical_assignment"]))
            if first is None or row["episode"]<first:pre+=wrong
            else:post+=wrong
        return {
            "arm":arm,"seed":seed,"pair":list(pair),"regime":regime,
            "family":list(family),"matching_policy":policy,
            "first_detection":first,"pre_mismatch":pre,"post_mismatch":post,
            "decoder":"F7-COMMON-PUBLIC-EARLY-V1","public_reads":10,
            "sample_trace":record[0]}
    finally:
        m.y49.restore_environment()
