"""Independent row-level R7 scientific reviewer; does NOT import original worker."""
import argparse,hashlib,json,math,pathlib
from protocol import protocol,parent_ok,claim_ok,load,digest,STAGES,LEGACY_BLOB,WING_SHA,reject
def number(x,lo,hi):
    if isinstance(x,bool) or not isinstance(x,(float,int)) or not math.isfinite(x) or x<lo or x>hi:reject("INVALID_ROW_NUMBER")
    return x
def near(a,b):
    if abs(a-b)>1e-8:reject("METRIC_DRIFT")
def verify(manifest_raw,original_raw,parent_raw,claim_raw,stage,run_id,head):
    m=protocol(manifest_raw); parent=parent_ok(parent_raw,stage)
    claim_ok(claim_raw,manifest_raw,stage,run_id,head)
    if len(original_raw)>25000000 or len(original_raw)==0:reject("ORIGINAL_BYTES")
    r=load(original_raw)
    expected=m["stages"][stage]
    required={"schema":"forge.r7.real-wingless-development-original.v1",
      "experiment_id":STAGES[stage],"stage_index":stage,
      "parent_experiment_id":expected["parent_experiment_id"],"parent_outcome":parent["outcome"],
      "parent_review_sha256":digest(parent_raw),"frozen_manifest_sha256":digest(manifest_raw),
      "method_legacy_git_blob":LEGACY_BLOB,"wingless_source_commit":WING_SHA,
      "run_id":run_id,"launch_head_sha":head,"firstuse_budget_consumed_before_compute":True,
      "original_replay_allowed":False,"scientific_accepted":False,"paid_api_calls":0}
    if not isinstance(r,dict) or any(r.get(k)!=v for k,v in required.items()):reject("ORIGINAL_IDENTITY")
    z=r.get("scientific_development_result")
    if (not isinstance(z,dict) or z.get("schema")!="forge.r35.quartile-original.v1" or
        z.get("method_source_sha")!=WING_SHA or z.get("model_calls")!=0 or
        z.get("science_production_accepted") is not False or z.get("candidate_mode")!="quartile025"):
        reject("METHOD_REPLACEMENT_OR_FALSE_AUTHORITY")
    if z.get("parent_r34_experiment_id")!=expected["parent_experiment_id"] or z.get("parent_review_outcome")!=parent["outcome"]:reject("METHOD_PARENT_DRIFT")
    if z.get("development_blocks")!=expected["development_blocks"] or z.get("sealed_heldout_seeds")!=expected["sealed_heldout_seeds"]:reject("METHOD_COHORT_DRIFT")
    runs=z.get("results"); comparisons=z.get("comparisons")
    if not isinstance(runs,dict) or set(runs)!={"1","2","3"} or not isinstance(comparisons,list) or len(comparisons)!=3:reject("EVALUATION_SHAPE")
    strict_count=partial_count=0
    for idx in (1,2,3):
        pair=runs[str(idx)]
        if not isinstance(pair,dict) or set(pair)!={"control","candidate"}:reject("ARM_DRIFT")
        summaries={}
        for arm,x in pair.items():
            if not isinstance(x,dict) or len(x.get("by_seed",[]))!=48:reject("ROW_COUNT")
            fam=x.get("family_accuracy");counts=x.get("source_training_example_counts")
            if not isinstance(fam,dict) or len(fam)!=3 or not isinstance(counts,dict) or set(fam)!=set(counts) or any(counts[k]!=576 for k in fam):reject("FAMILY_TRAINING_BUDGET")
            h=x.get("weights_sha256")
            if not isinstance(h,str) or len(h)!=64 or any(ch not in "0123456789abcdef" for ch in h):reject("MODEL_FINGERPRINT")
            accum={k:0.0 for k in fam}
            total=0.0
            for j,row in enumerate(x["by_seed"]):
                if row.get("seed")!=expected["sealed_heldout_seeds"][j] or row.get("total")!=108:reject("SEALED_ROW_SOURCE")
                correct=number(row.get("correct"),0,108)
                detail=row.get("family_correct")
                if not isinstance(detail,dict) or set(detail)!=set(fam):reject("FAMILY_ROW_SHAPE")
                for k in fam:accum[k]+=number(detail[k],0,36)
                near(correct,sum(detail.values()));total+=correct
            overall=total/(48*108)
            near(number(x.get("accuracy"),0,1),overall)
            for k in fam:near(number(fam[k],0,1),accum[k]/(48*36))
            summaries[arm]=(overall,dict(fam))
        a,b=summaries["control"],summaries["candidate"]
        delta={k:b[1][k]-a[1][k] for k in a[1]}
        gain=min(b[1].values())-min(a[1].values())
        strict=(gain>=0.05 and b[0]>=0.55 and min(delta.values())>=-0.05)
        partial=(gain>=0.02)
        c=comparisons[idx-1]
        if not isinstance(c,dict) or c.get("block")!=idx or c.get("strict") is not strict or c.get("partial") is not partial or set(c.get("family_deltas",{}))!=set(delta):reject("COMPARISON_REAGGREGATION")
        near(number(c.get("worst_family_gain"),-1,1),gain)
        near(number(c.get("candidate_accuracy"),0,1),b[0])
        for k in delta:near(number(c["family_deltas"][k],-1,1),delta[k])
        strict_count+=strict;partial_count+=partial
    outcome="ROBUST_QUARTILE_GAIN" if strict_count==3 else ("PARTIAL_QUARTILE_GAIN" if partial_count>=2 else "NO_CONFIRMED_QUARTILE_GAIN")
    if z.get("classification")!=outcome or r.get("outcome")!=outcome:reject("RESULT_CLASSIFICATION_DRIFT")
    return {"schema":"forge.r7.independent-development-review.v1",
      "experiment_id":STAGES[stage],"stage_index":stage,
      "parent_experiment_id":expected["parent_experiment_id"],"parent_outcome":parent["outcome"],
      "original_sha256":digest(original_raw),"parent_review_sha256":digest(parent_raw),
      "frozen_manifest_sha256":digest(manifest_raw),"outcome":outcome,
      "reaggregated_blocks":3,"reaggregated_sealed_rows_per_arm":3*48,
      "independently_validated":True,"original_replay_allowed":False,
      "science_production_accepted":False,"external_fsa_qualified":False,
      "next_science_dispatch_authorized":False}
def main():
    p=argparse.ArgumentParser()
    for item in ("manifest","original","parent_review","claim","stage","run_id","head","out"):
        p.add_argument("--"+item.replace("_","-"),required=True)
    args=p.parse_args()
    report=verify(pathlib.Path(args.manifest).read_bytes(),
      pathlib.Path(args.original).read_bytes(),pathlib.Path(args.parent_review).read_bytes(),
      pathlib.Path(args.claim).read_bytes(),int(args.stage),args.run_id,args.head)
    with pathlib.Path(args.out).open("x") as f:
        f.write(json.dumps(report,sort_keys=True,indent=2)+"\n")
    print("R7_INDEPENDENT_REAL_DEVELOPMENT_REVIEW=PASS",flush=True)
    print("R7_CLASSIFICATION="+report["outcome"],flush=True)
if __name__=="__main__":main()
