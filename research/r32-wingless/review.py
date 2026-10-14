"""Independent R32 result reviewer. Never imports or executes the research worker."""
import argparse
import hashlib
import json
import math
from pathlib import Path

BLOB="057c14cc786ae3d1a11735c8c8dddde85d339c20"
EXPERIMENT="W-FORGE-R32-T05-REPLICATION-01"
SOURCE="b1e4972f04142f1f35f76f9483b12491dec4846c"

def reject(message="R32_INDEPENDENT_SCIENTIFIC_REVIEW_REJECTED"):
    raise ValueError(message)
def exact_json(raw):
    def unique(pairs):
        o={}
        for k,v in pairs:
            if k in o:reject("R32_DUPLICATE_JSON_KEY")
            o[k]=v
        return o
    return json.loads(raw,object_pairs_hook=unique,parse_constant=lambda _:reject("R32_BAD_FLOAT"))
def number(x,lo=0,hi=1):
    if isinstance(x,bool) or not isinstance(x,(float,int)) or not math.isfinite(x) or not lo<=x<=hi:reject()
    return x
def compare(a,b):
    if abs(a-b)>1e-8:reject("R32_RAW_COMPARISON_DRIFT")
def verify(manifest_raw,original_raw,parent_review_raw):
    if not 0<len(manifest_raw)<20000 or not 0<len(original_raw)<25000000:reject()
    git_blob=hashlib.sha1(b"blob "+str(len(manifest_raw)).encode()+bytes([0])+manifest_raw).hexdigest()
    if git_blob!=BLOB:reject("R32_FROZEN_PREREG_DRIFT")
    m=exact_json(manifest_raw);r=exact_json(original_raw)
    if not isinstance(r,dict) or r.get("schema")!="forge.r32.replication-original.v1" or r.get("experiment_id")!=EXPERIMENT or r.get("prereg_git_blob")!=BLOB or r.get("method_source_sha")!=SOURCE or r.get("model_calls")!=0 or r.get("science_production_accepted") is not False:reject()
    parent=exact_json(parent_review_raw)
    if parent.get("schema")!="forge.r31.independent-original-review.v1" or parent.get("experiment_id")!=m["parent_experiment_id"] or parent.get("independently_validated") is not True or parent.get("original_replay_allowed") is not False or parent.get("outcome")!=m["parent_outcome"]:reject()
    expected_mode="temperature05"
    if r.get("parent_r31_experiment_id")!=m["parent_experiment_id"] or r.get("parent_review_outcome")!=parent["outcome"] or r.get("candidate_mode")!=expected_mode or r.get("parent_review_sha256")!=hashlib.sha256(parent_review_raw).hexdigest():reject()
    if r.get("development_blocks")!=m["development_blocks"] or r.get("sealed_heldout_seeds")!=m["sealed_heldout_seeds"]:reject()
    if not isinstance(r.get("github_run_id"),str) or not r["github_run_id"].isdecimal():reject()
    seeds=m["sealed_heldout_seeds"];blocks=m["development_blocks"]
    if len(blocks)!=3 or any(len(b)!=16 for b in blocks) or len(seeds)!=48 or len(set(sum(blocks,[])+seeds))!=96:reject()
    outputs=r.get("results");comparisons=r.get("comparisons")
    if not isinstance(outputs,dict) or set(outputs)!={"1","2","3"} or not isinstance(comparisons,list) or len(comparisons)!=3:reject()
    strict_count=partial_count=0
    for idx in (1,2,3):
        group=outputs[str(idx)]
        if set(group)!={"control","candidate"}:reject()
        summaries={}
        for arm,model in group.items():
            if not isinstance(model,dict) or len(model.get("by_seed",[]))!=48:reject()
            fam=model.get("family_accuracy")
            counts=model.get("source_training_example_counts")
            if not isinstance(fam,dict) or len(fam)!=3 or set(counts)!=set(fam) or any(counts[g]!=576 for g in fam):reject()
            if not isinstance(model.get("weights_sha256"),str) or len(model["weights_sha256"])!=64:reject()
            per_fam={g:0.0 for g in fam};total=0.0
            for i,row in enumerate(model["by_seed"]):
                if row.get("seed")!=seeds[i] or row.get("total")!=108:reject()
                score=number(row.get("correct"),0,108)
                detail=row.get("family_correct")
                if not isinstance(detail,dict) or set(detail)!=set(fam):reject()
                for g in fam:per_fam[g]+=number(detail[g],0,36)
                compare(sum(detail.values()),score)
                total+=score
            overall=total/(48*108)
            compare(number(model.get("accuracy")),overall)
            for g in fam:compare(number(fam[g]),per_fam[g]/(48*36))
            summaries[arm]=(overall,dict(fam))
        a=summaries["control"];b=summaries["candidate"]
        delta={g:b[1][g]-a[1][g] for g in a[1]}
        gain=min(b[1].values())-min(a[1].values())
        strict=gain>=.05 and b[0]>=.55 and min(delta.values())>=-.05
        partial=gain>=.02
        c=comparisons[idx-1]
        if c.get("block")!=idx or c.get("strict") is not strict or c.get("partial") is not partial or set(c.get("family_deltas",{}))!=set(delta):reject()
        compare(c.get("worst_family_gain"),gain);compare(c.get("candidate_accuracy"),b[0])
        for g in delta:compare(c["family_deltas"][g],delta[g])
        strict_count+=strict;partial_count+=partial
    outcome=("ROBUST_REPLICATION_GAIN" if strict_count==3 else "PARTIAL_REPLICATION_GAIN" if partial_count>=2 else "NO_CONFIRMED_REPLICATION_GAIN")
    if r.get("classification")!=outcome:reject()
    return {"schema":"forge.r32.independent-original-review.v1","experiment_id":EXPERIMENT,"original_sha256":hashlib.sha256(original_raw).hexdigest(),"prereg_blob":BLOB,"outcome":outcome,"independently_validated":True,"science_production_accepted":False,"original_replay_allowed":False}

def main():
    p=argparse.ArgumentParser()
    for k in ("manifest","raw","out"):p.add_argument("--"+k,required=True)
    p.add_argument("--parent-review",required=True)
    a=p.parse_args()
    review=verify(Path(a.manifest).read_bytes(),Path(a.raw).read_bytes(),Path(a.parent_review).read_bytes())
    Path(a.out).write_text(json.dumps(review,sort_keys=True,indent=2)+"\n")
    print("R32_INDEPENDENT_SCIENTIFIC_REVIEW=PASS")
    print("R32_SCIENTIFIC_OUTCOME="+review["outcome"])
if __name__=="__main__":main()
