"""Independent Yggdrasil bounded original reviewer; never imports scientific worker."""
import argparse,collections,hashlib,json,math
from pathlib import Path
MANIFEST="04bc2ab3cb6c6e0385a9e6cc3e3132f7f254f588"
FIELDS=("mismatch_episodes","pre_detection_mismatch_episodes","post_detection_mismatch_episodes",
        "wrong_assignments","matching_search_calls","candidate_retained_writes",
        "illegal_physical_assignments","public_reads")
def strict(raw):
    def unique(pairs):
        v={}
        for k,x in pairs:
            if k in v:raise ValueError("YGG_REVIEW_DUPLICATE_JSON_FIELD")
            v[k]=x
        return v
    return json.loads(raw,object_pairs_hook=unique,parse_constant=lambda x:(_ for _ in ()).throw(ValueError("YGG_BAD_NUMBER")))
def blob(raw):
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\x00"+raw).hexdigest()
def verify(manifest_raw,original_raw,expected_id,parent_review_raw=None):
    if not 0<len(original_raw)<25_000_000 or blob(manifest_raw)!=MANIFEST:raise ValueError("YGG_FROZEN_SOURCE_DRIFT")
    m=strict(manifest_raw);out=strict(original_raw)
    study=next((s for s in m["studies"] if s["experiment_id"]==expected_id),None)
    if study is None or out.get("experiment_id")!=expected_id or out.get("schema")!="forge.yggdrasil.f2-pair-transfer-original.v1" or out.get("prereg_blob")!=MANIFEST or out.get("ygg_source_commit")!=m["lineage"]["source_commit"] or out.get("parent_worker_blob")!=m["lineage"]["y070_worker_blob"] or out.get("model_calls")!=0 or out.get("original_replay_allowed") is not False or out.get("science_production_accepted") is not False:raise ValueError("YGG_ORIGINAL_IDENTITY_INVALID")
    a=out.get("scientific_result")
    if not isinstance(a,dict) or a.get("sealed_heldout_seeds")!=study["sealed_seeds"] or a.get("development_seeds")!=study["dev_seeds"] or a.get("model_calls")!=0 or a.get("accepted_ref_mutation") is not False or a.get("per_trial_public_scalar_reads")!=10 or a.get("active")!=7 or a.get("retained_limit")!=9 or a.get("development_checks")!=384:raise ValueError("YGG_SCALAR_INVARIANTS_DRIFT")
    if parent_review_raw is None:raise ValueError("YGG_F2_REQUIRES_PARENT_INDEPENDENT_E2")
    p=strict(parent_review_raw)
    if p.get("schema")!="forge.yggdrasil.e3-independent-review.v1" or p.get("experiment_id")!=m["parent"]["experiment_id"] or p.get("outcome")!=m["parent"]["required_outcome"] or p.get("independently_validated") is not True or p.get("original_replay_allowed") is not False:raise ValueError("YGG_F2_PARENT_OUTCOME_UNQUALIFIED")
    if out.get("parent_review_sha256")!=hashlib.sha256(parent_review_raw).hexdigest() or out.get("parent_outcome")!=p["outcome"]:raise ValueError("YGG_F2_ORIGINAL_PARENT_BINDING")
    records=a.get("complete_heldout_records");groups=a.get("groups")
    if not isinstance(records,list) or len(records)!=768 or not isinstance(groups,dict) or len(groups)!=4:raise ValueError("YGG_RECORD_SHAPE_DRIFT")
    pairs=[tuple(p) for p in m["pairs"]]
    keys=[f"{x}_{y}:{reg}" for x,y in pairs for reg in ("steady","onset1")]
    if set(groups)!=set(keys):raise ValueError("YGG_GROUPS_DRIFT")
    seen=set();totals={k:{arm:{f:0 for f in FIELDS} for arm in m["arms"]} for k in keys}
    detection={k:{arm:0 for arm in m["arms"]} for k in keys}
    for row in records:
        pair=row.get("pair");reg=row.get("regime");family=row.get("family");seed=row.get("seed");policy=row.get("policy")
        if pair not in m["pairs"] or reg not in ("steady","onset1") or family not in m["families"] or seed not in study["sealed_seeds"] or policy not in m["policies"]:raise ValueError("YGG_CASE_DOMAIN_DRIFT")
        signature=(tuple(pair),reg,tuple(family),seed,policy)
        if signature in seen:raise ValueError("YGG_DUPLICATE_CASE")
        seen.add(signature);key=f"{pair[0]}_{pair[1]}:{reg}"
        observed=row.get("arms")
        if not isinstance(observed,dict) or set(observed)!=set(m["arms"]):raise ValueError("YGG_ARM_MISSING")
        for arm,z in observed.items():
            first=z.get("first_detection")
            if first is not None:
                if type(first) is not int or first<0 or first>10:raise ValueError("YGG_BAD_DETECTION")
                detection[key][arm]+=1
            for f in FIELDS:
                n=10 if f=="public_reads" else z.get(f)
                if type(n) is not int or n<0:raise ValueError("YGG_NEGATIVE_METRIC")
                totals[key][arm][f]+=n
            if z["pre_detection_mismatch_episodes"]+z["post_detection_mismatch_episodes"]!=z["mismatch_episodes"] or z["illegal_physical_assignments"]!=0:raise ValueError("YGG_METRIC_INCONSISTENT")
    for key in keys:
        group=groups[key]
        if group.get("totals")!=totals[key] or group.get("detections")!=detection[key] or type(group.get("source_anchor_checks")) is not int or group["source_anchor_checks"]<0:raise ValueError("YGG_RECOMPUTED_TOTALS_MISMATCH")
    calculated=[]
    for x,y in pairs:
        name=f"{x}_{y}:onset1";t=totals[name]
        baseline=t["dual_sentinel_detect_only"]["post_detection_mismatch_episodes"]
        corrected=t["dual_sentinel_decoder_corrected"]["post_detection_mismatch_episodes"]
        ori=t["original_rotating_detect_only"]["mismatch_episodes"]
        cor=t["dual_sentinel_decoder_corrected"]["mismatch_episodes"]
        strict_flag=baseline>0 and corrected<=0.5*baseline and cor<ori
        partial=baseline>0 and corrected<=0.8*baseline
        calculated.append({"case":name,"uncorrected_post":baseline,"corrected_post":corrected,
                           "original_total":ori,"corrected_total":cor,
                           "post_gain":None if baseline==0 else 1-corrected/baseline,
                           "strict":strict_flag,"partial":partial})
    steady=all(totals[f"{x}_{y}:steady"][arm]["mismatch_episodes"]==0 for x,y in pairs for arm in m["arms"])
    result="EARLY_CAUSAL_GAIN" if steady and all(z["strict"] for z in calculated) else ("PARTIAL_EARLY_GAIN" if steady and any(z["partial"] for z in calculated) else "NO_GAIN")
    if a.get("comparisons")!=calculated or a.get("steady_zero_mismatches") is not steady or a.get("classification")!=result:raise ValueError("YGG_OUTCOME_NOT_REPRODUCIBLE")
    diagnostic=[]
    for x,y in pairs:
        t=totals[f"{x}_{y}:onset1"]
        corrected=t["dual_sentinel_decoder_corrected"]
        control=t["dual_sentinel_detect_only"]
        pre=corrected["pre_detection_mismatch_episodes"]
        post=corrected["post_detection_mismatch_episodes"]
        baseline=control["post_detection_mismatch_episodes"]
        diagnostic.append({"pair":[x,y],"pre_detection":pre,"post_detection":post,
                           "control_post":baseline,
                           "post_gain_20pct":baseline>0 and post<=0.8*baseline})
    latency=(all(x["pre_detection"]>x["post_detection"] for x in diagnostic)
             and any(x["post_gain_20pct"] for x in diagnostic))
    residual=all(x["post_detection"]>=x["pre_detection"] for x in diagnostic)
    diagnosed=("LATENCY_TRANSFER_GAIN" if latency else
               "DECODER_RESIDUAL_TRANSFER" if residual else
               "MIXED_OR_NO_TRANSFER")
    if out.get("onset_diagnostic")!={"pairs":diagnostic,"outcome":diagnosed}:
        raise ValueError("YGG_F2_INDEPENDENT_DIAGNOSTIC_DRIFT")
    return {"schema":"forge.yggdrasil.f2-independent-review.v1","experiment_id":expected_id,
            "original_sha256":hashlib.sha256(original_raw).hexdigest(),"prereg_blob":MANIFEST,
            "outcome":diagnosed,"native_y070_outcome":result,"independently_validated":True,"original_replay_allowed":False,
            "science_production_accepted":False,"parent_review_sha256":None if parent_review_raw is None else hashlib.sha256(parent_review_raw).hexdigest()}
def main():
    p=argparse.ArgumentParser()
    for x in ("manifest","original","experiment_id","out"):
        p.add_argument("--"+x.replace("_","-"),required=True)
    p.add_argument("--parent-review")
    a=p.parse_args()
    parent=None if not a.parent_review else Path(a.parent_review).read_bytes()
    result=verify(Path(a.manifest).read_bytes(),Path(a.original).read_bytes(),a.experiment_id,parent)
    Path(a.out).write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("YGG_INDEPENDENT_REVIEW=PASS",flush=True)
    print("YGG_SCIENTIFIC_OUTCOME="+result["outcome"],flush=True)
if __name__=="__main__":main()
