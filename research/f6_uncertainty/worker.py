"""Pinned Y070 engineering trial for F6 learned public uncertainty.

Inference policy gets only public observations plus frozen learned threshold.
All true transposition and evaluator information stay outside sample policy.
ONLY prior F3 consumed development seeds 67206-67207 can be evaluated.
"""
from contextlib import contextmanager
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"f5_native_coverage"))
from policy import PROBES
import importlib.util
from pathlib import Path as _Path
_f5path=_Path(__file__).resolve().parents[1]/"f5_native_coverage"/"worker.py"
_spec=importlib.util.spec_from_file_location("f6_exact_f5_parent_worker",_f5path)
_parent_worker=importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_parent_worker)
load_source=_parent_worker.load_source
decode=_parent_worker.decode
SOURCE_COMMIT=_parent_worker.SOURCE_COMMIT
from learner import choose_f6,CHECK_SEEDS

@contextmanager
def install_model(source,model,trace):
    if model.get("schema")!="forge.f6.public-only.calibrated-memory-threshold.v1" or (
            model.get("status")!="TRAINED_ON_PREVIOUSLY_USED_F3_DEVELOPMENT_ONLY"
            or model.get("scientific_dispatch_authorized") is not False):
        raise ValueError("F6_MODEL_NOT_FROZEN_ENGINEERING")
    threshold=model["frozen_threshold"]
    m=source.m
    sample_before=m.y64.dual_public_samples
    decoder_before=m.y61.y60.public_decoder
    def sample(seed,family):
        history={}
        for episode in PROBES:
            cells=choose_f6(episode,history,threshold)
            history[episode]={cell:m.y64.y46.coordinate(
                cell,seed,episode,family,"late_shock") for cell in cells}
        # Causal policy replay: no hidden seed, family or true pair in chooser.
        replay={}
        for episode in PROBES:
            predicted=choose_f6(episode,replay,threshold)
            if tuple(history[episode])!=predicted:
                raise ValueError("F6_PUBLIC_CASUAL_TRACE_DRIFT")
            replay[episode]=history[episode]
        if sum(map(len,history.values()))!=10:
            raise ValueError("F6_PUBLIC_READ_BUDGET")
        trace.append({"addresses":[list(history[t]) for t in PROBES],
                      "public_values":[[history[t][cell] for cell in history[t]] for t in PROBES],
                      "recheck":set(history[5])==set(history[7])})
        return {t:{str(c):v for c,v in h.items()} for t,h in history.items()}
    try:
        m.y64.dual_public_samples=sample
        m.y61.y60.public_decoder=decode
        yield
    finally:
        m.y64.dual_public_samples=sample_before
        m.y61.y60.public_decoder=decoder_before

def evaluate(source,model,seed,pair,regime,family,matching_policy):
    if seed not in CHECK_SEEDS:
        raise ValueError("F6_NEW_OR_TRAINING_SEED_REFUSED")
    if tuple(pair) not in ((8,10),(11,13)) or regime not in ("steady","onset1"):
        raise ValueError("F6_UNKNOWN_PAIR_OR_REGIME_REFUSED")
    if family not in source.FAMILIES or matching_policy not in source.POLICIES:
        raise ValueError("F6_SOURCE_FIDELITY")
    if model.get("training_seed_ids")!=[67204,67205] or (
            model.get("untouched_validation_seed_ids")!=[67206,67207]):
        raise ValueError("F6_SPLIT_IDENTITY_DRIFT")
    m=source.m
    m.y58.install_transposition(None if regime=="steady" else 1,
                                pair,{"anchor_pair_checks":0})
    try:
        reference=m.y50.evaluate(seed,matching_policy,"canonical","continue",family)
        traces=[]
        with install_model(source,model,traces):
            output=m.candidate(seed,family,matching_policy,
                               "dual_sentinel_decoder_corrected")
        if len(traces)!=1 or output["public_scalar_reads"]!=10:
            raise ValueError("F6_NO_ACTUAL_SOURCE_SAMPLING")
        first=output["rows"][-1]["public_detected_swap_first_episode"]
        pre=post=0
        for truth,row in zip(reference["rows"],output["rows"]):
            if truth["episode"]!=row["episode"] or row["illegal_physical_assignments"]!=0:
                raise ValueError("F6_ILLEGAL_PHYSICAL_ASSIGNMENT")
            if row["candidate_retained_cache_occupancy"]>9 or (
                    len(row["physical_assignment_evaluator_only"])!=7):
                raise ValueError("F6_RETAINED_OR_ACTIVE_BUDGET")
            wrong=int(any(truth["physical_assignment"][k]!=
                          row["physical_assignment_evaluator_only"][k]
                          for k in truth["physical_assignment"]))
            if first is None or row["episode"]<first:pre+=wrong
            else:post+=wrong
        return {
            "arm":"F6-LEARNED-UNCERTAINTY","seed":seed,
            "pair":list(pair),"regime":regime,"family":list(family),
            "matching_policy":matching_policy,
            "public_reads":10,"decoder":"F5-GENERALIZED-PUBLIC-V1",
            "first_detection":first,"pre_mismatch":pre,
            "post_mismatch":post,"sample_trace":traces[0]}
    finally:
        m.y49.restore_environment()
