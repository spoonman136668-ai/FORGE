"""Independent R26 reviewer: no import of Wingless evaluator or its training code.

Validates a REAL first-use raw original against frozen cohorts, exact budgets,
per-seed numbers, source counts and independently recomputed thresholds.
A passed review is a bounded research finding, not FORGE production authority.
"""
import argparse
import hashlib
import json
import math
import pathlib

EXPERIMENT="W-FORGE-R26-OUT-OF-COHORT-REPLICATION-01"
SOURCE="b1e4972f04142f1f35f76f9483b12491dec4846c"
FROZEN_BLOB="dc11dc29ac8d885e37096f896706b9d795220173"
ARMS=("affine_only_full_batch","three_source_balanced_full_batch")

def bad():
    raise ValueError("FORGE_R26_INDEPENDENT_REVIEW_REJECTED")

def bounded(value, maximum=None):
    if isinstance(value,bool) or not isinstance(value,(float,int)) or not math.isfinite(value) or value < 0:
        bad()
    if maximum is not None and value > maximum:bad()
    return value

def canonical_load(raw):
    def duplicate(pairs):
        seen={}
        for key,value in pairs:
            if key.casefold() in seen:bad()
            seen[key.casefold()]=value
        return dict(pairs)
    return json.loads(raw,object_pairs_hook=duplicate,parse_constant=lambda v:bad())

def verify(manifest_bytes, original_bytes):
    if len(original_bytes)>15<<20 or len(manifest_bytes)>20<<10:bad()
    h=hashlib.sha1(b"blob "+str(len(manifest_bytes)).encode()+b"\0"+manifest_bytes).hexdigest()
    if h != FROZEN_BLOB:bad()
    m=canonical_load(manifest_bytes)
    r=canonical_load(original_bytes)
    if not isinstance(m,dict) or not isinstance(r,dict):bad()
    if (r.get("schema")!="forge.r26.wingless.original.v1"
            or r.get("experiment_id")!=EXPERIMENT
            or r.get("method_source_sha")!=SOURCE
            or r.get("manifest_git_blob")!=FROZEN_BLOB
            or str(r.get("github_run_id","")).isdecimal() is False
            or r.get("science_production_accepted") is not False
            or r.get("original_replay_authorized") is not False):bad()
    s=r.get("source_result")
    if not isinstance(s,dict) or s.get("schema")!="wingless.w-r52-family-balanced-batch.v1" or s.get("model_calls")!=0:bad()
    blocks=m["development_blocks"]
    seeds=m["sealed_heldout_seeds"]
    if s.get("development_blocks")!=blocks or s.get("sealed_heldout_seeds")!=seeds:bad()
    if len(blocks)!=3 or any(len(b)!=16 for b in blocks) or len(seeds)!=48:bad()
    if len(set(seeds+sum(blocks,[]))) != 96:bad()
    if (s.get("new_model_selection_from_heldout") is not False
            or s.get("claim_limit")!="Synthetic paired-choice full-batch equal-example generator-mix study; source-family/entity exposure changes by design; no real-world learning claims."):bad()
    by_encoding=s.get("all_models_by_encoding")
    if not isinstance(by_encoding,dict) or set(by_encoding)!={"identity","xor55"}:bad()
    generators=None
    summaries={}
    for encoding,models in by_encoding.items():
        if not isinstance(models,dict) or set(models)!={f"{i}:{arm}" for i in (1,2,3) for arm in ARMS}:bad()
        for key,model in models.items():
            if not isinstance(model,dict) or len(model.get("by_seed",[]))!=48:bad()
            if not (isinstance(model.get("weights_sha256"),str) and len(model["weights_sha256"])==64):bad()
            if not (isinstance(model.get("training_corpus_sha256"),str) and len(model["training_corpus_sha256"])==64):bad()
            if not isinstance(model.get("batch_misclassification_updates"),int) or model["batch_misclassification_updates"]<0:bad()
            per=model["by_seed"]
            family=model["family_accuracy"]
            if not isinstance(family,dict) or len(family)!=3:bad()
            if generators is None:generators=set(family)
            if set(family)!=generators:bad()
            total_correct=0
            by_family={k:0.0 for k in generators}
            for n,row in enumerate(per):
                if row.get("seed")!=seeds[n] or row.get("total")!=108:bad()
                correct=bounded(row.get("correct"),108)
                if not isinstance(row.get("ties"),int) or not 0<=row["ties"]<=108:bad()
                fc=row.get("family_correct")
                if not isinstance(fc,dict) or set(fc)!=generators:bad()
                for k,value in fc.items():
                    by_family[k]+=bounded(value,36)
                if abs(sum(fc.values())-correct)>1e-7:bad()
                total_correct+=correct
            expected_accuracy=total_correct/(48*108)
            if abs(bounded(model.get("accuracy"),1)-expected_accuracy)>1e-8:bad()
            for k in generators:
                if abs(bounded(family[k],1)-by_family[k]/(48*36))>1e-8:bad()
            counts=model.get("source_training_example_counts")
            if not isinstance(counts,dict) or set(counts)!=generators or sum(counts.values())!=1728:bad()
            if key.endswith("three_source_balanced_full_batch"):
                if any(count!=576 for count in counts.values()):bad()
            elif sorted(counts.values()) != [0,0,1728]:bad()
            summaries[(encoding,key)]=(expected_accuracy,dict(family))
    for key in by_encoding["identity"]:
        a=summaries[("identity",key)]
        b=summaries[("xor55",key)]
        if abs(a[0]-b[0])>1e-9:bad()
        if any(abs(a[1][g]-b[1][g])>1e-9 for g in generators):bad()
    comparisons=s.get("arm_comparisons")
    if not isinstance(comparisons,list) or len(comparisons)!=3:bad()
    thresholds=m["thresholds"]
    stricts,partials=0,0
    reconstructed=[]
    for idx,c in enumerate(comparisons,1):
        baseline=summaries[("identity",f"{idx}:affine_only_full_batch")]
        mixed=summaries[("identity",f"{idx}:three_source_balanced_full_batch")]
        delta={k:mixed[1][k]-baseline[1][k] for k in generators}
        min_gain=min(mixed[1].values())-min(baseline[1].values())
        strict=(min_gain>=thresholds["worst_source_gain_min"]
                and mixed[0]>=thresholds["mixed_overall_accuracy_min"]
                and min(delta.values())>=-thresholds["max_source_harm"])
        partial=min_gain>=thresholds["partial_gain_min"]
        if (c.get("development_block")!=idx
                or abs(c.get("min_source_gain",1e99)-min_gain)>1e-8
                or abs(c.get("mixed_overall_accuracy",1e99)-mixed[0])>1e-8
                or abs(c.get("affine_only_overall_accuracy",1e99)-baseline[0])>1e-8
                or set(c.get("source_deltas",{}))!=generators
                or any(abs(c["source_deltas"][k]-delta[k])>1e-8 for k in generators)
                or c.get("strict_gate") is not strict or c.get("partial_gate") is not partial):
            bad()
        stricts+=strict;partials+=partial
        reconstructed.append({"block":idx,"min_source_gain":min_gain,"strict":strict,"partial":partial})
    label=("FAMILY_DIVERSITY_ROBUST" if stricts==3 else
           "PARTIAL_FAMILY_GAIN" if partials>=thresholds["partial_cohorts_min"] else
           "NO_CONFIRMED_DIVERSITY_GAIN")
    if s.get("classification")!=label:bad()
    return {"schema":"forge.r26.independent-scientific-review.v1",
            "experiment_id":EXPERIMENT,
            "original_sha256":hashlib.sha256(original_bytes).hexdigest(),
            "frozen_prereg_blob":FROZEN_BLOB,
            "reported_outcome":label,
            "independent_bounded_validation":True,
            "model_calls":0,
            "reconstructed_comparisons":reconstructed,
            "original_first_use_replayed":False,
            "science_production_accepted":False,
            "external_fsa_qualified":False}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--manifest",required=True)
    p.add_argument("--raw",required=True)
    p.add_argument("--out",required=True)
    args=p.parse_args()
    result=verify(pathlib.Path(args.manifest).read_bytes(),pathlib.Path(args.raw).read_bytes())
    path=pathlib.Path(args.out)
    with path.open("x",encoding="utf8") as f:
        json.dump(result,f,indent=2,sort_keys=True,allow_nan=False)
        f.write("\n")
    print("R26_INDEPENDENT_BOUNDED_SCIENCE_REVIEW=PASS")
    print("SCIENTIFIC_OUTCOME="+result["reported_outcome"])
    print("PRODUCTION_SCIENCE_ACCEPTED=FALSE")
if __name__=="__main__":main()
