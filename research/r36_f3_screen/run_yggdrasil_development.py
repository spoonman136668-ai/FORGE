"""F3 Yggdrasil genuine source-pinned development baseline; NO scientific original.

Invokes the immutable Y070 simulator directly on 8 preregistered
development seeds, never its run() method (which touches sealed cohorts).
The four experimental samplers are NOT admitted by this baseline gate.
"""
import argparse
import importlib.util
import json
import pathlib
import subprocess

SOURCE_COMMIT="5797a257a75fe139313e8486cd1a1ae79c44b148"
SOURCE_PATH="research/contrib/chatgpt/20261013-y070-onset1/execute.py"
DEV=tuple(range(67200,67208))
PAIRS=((8,10),(11,13))
ARM="dual_sentinel_decoder_corrected"

def git(root,*args):
    return subprocess.check_output(["git","-C",str(root),*args],stderr=subprocess.DEVNULL).decode().strip()

def load_pinned(root):
    root=pathlib.Path(root).resolve(strict=True)
    if git(root,"rev-parse","HEAD")!=SOURCE_COMMIT or git(root,"status","--porcelain"):
        raise ValueError("F3_YGG_PINNED_SOURCE_IDENTITY_DRIFT")
    path=root/SOURCE_PATH
    if git(root,"ls-files","--error-unmatch",SOURCE_PATH)!=SOURCE_PATH:
        raise ValueError("F3_YGG_WORKER_PATH_DRIFT")
    spec=importlib.util.spec_from_file_location("f3_pinned_y070",path)
    if not spec or not spec.loader:
        raise ValueError("F3_YGG_WORKER_IMPORT_DENIED")
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def validate_portfolio():
    from run_wingless_development import audit_frozen
    p=audit_frozen()["yggdrasil"]
    if p["method_source_commit"]!=SOURCE_COMMIT or p["development_seeds"]!=list(DEV) or p["legal_novel_pairs"]!=[list(x) for x in PAIRS]:
        raise ValueError("F3_YGG_FROZEN_DEV_IDENTITY_DRIFT")
    if set(DEV)&set(p["reserved_sealed_heldout_seeds"]):
        raise ValueError("F3_YGG_SEALED_COHORT_COLLISION")
    return p

def measure(ygg_root):
    portfolio=validate_portfolio()
    y070=load_pinned(ygg_root)
    m=y070.m
    records=[]
    try:
        for pair in PAIRS:
            for regime,onset in (("steady",None),("onset1",1)):
                integrity={"anchor_pair_checks":0}
                m.y58.install_transposition(onset,pair,integrity)
                for family in y070.FAMILIES:
                    for seed in DEV:
                        for policy in y070.POLICIES:
                            canonical=m.y50.evaluate(seed,policy,"canonical","continue",family)
                            candidate=m.candidate(seed,family,policy,ARM)
                            if candidate["public_scalar_reads"]!=10:
                                raise ValueError("F3_YGG_PUBLIC_READ_BUDGET")
                            first=next((r["public_detected_swap_first_episode"] for r in reversed(candidate["rows"])
                                        if r["public_detected_swap_first_episode"] is not None),None)
                            pre=post=illegal=0
                            if len(candidate["rows"])!=len(canonical["rows"]):
                                raise ValueError("F3_YGG_EPISODE_COUNT_DRIFT")
                            for truth,observed in zip(canonical["rows"],candidate["rows"]):
                                if truth["episode"]!=observed["episode"]:
                                    raise ValueError("F3_YGG_EPISODE_DRIFT")
                                wrong=int(any(truth["physical_assignment"][key]!=observed["physical_assignment_evaluator_only"][key]
                                              for key in truth["physical_assignment"]))
                                if first is None or observed["episode"]<first:pre+=wrong
                                else:post+=wrong
                                illegal+=observed["illegal_physical_assignments"]
                                if observed["candidate_retained_cache_occupancy"]>9 or len(observed["physical_assignment_evaluator_only"])!=7:
                                    raise ValueError("F3_YGG_CAPACITY_DRIFT")
                            if illegal:
                                raise ValueError("F3_YGG_ILLEGAL_ASSIGNMENT")
                            records.append({"pair":list(pair),"regime":regime,"seed":seed,"family":list(family),
                                            "policy":policy,"first_detection":first,"pre_mismatch":pre,
                                            "post_mismatch":post,"public_reads":10,"illegal_assignments":illegal})
                m.y49.restore_environment()
    finally:
        m.y49.restore_environment()
    if len(records)!=len(PAIRS)*2*len(y070.FAMILIES)*len(DEV)*len(y070.POLICIES):
        raise ValueError("F3_YGG_TRIAL_COUNT")
    return {"schema":"forge.f3.yggdrasil.real-development-baseline.v1",
            "status":"PINNED_BASELINE_DEVELOPMENT_ONLY_CANDIDATES_NOT_QUALIFIED",
            "source_commit":SOURCE_COMMIT,"development_seeds":list(DEV),
            "baseline_arm":ARM,"records":records,
            "scientific_winners_selected":0,"scientific_originals_executed":0,
            "sealed_first_uses_consumed":0,"model_api_calls":0}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--yggdrasil-root",required=True)
    p.add_argument("--out",required=True)
    opts=p.parse_args()
    result=measure(opts.yggdrasil_root)
    with pathlib.Path(opts.out).open("xb") as fd:
        fd.write((json.dumps(result,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n").encode())
    print("F3_YGG_REAL_BASELINE_DEVELOPMENT=PASS")
    print("F3_YGG_DEVELOPMENT_TRIALS="+str(len(result["records"])))
    print("F3_YGG_ORIGINAL_FIRST_USE=ZERO")

if __name__=="__main__":
    main()
