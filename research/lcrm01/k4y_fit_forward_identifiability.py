#!/usr/bin/env python3
"""K4Y. Historical original FIT-only movement identifiability; no simulator.

All original K4X CHECK/DEV rows are excluded. This is a retrospective
engineering information-sufficiency audit, never FSA/source first-use.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
import math
import os
from pathlib import Path
import random
import re
import resource
import time
import zipfile

HERE=Path(__file__).resolve().parent
FREEZE=HERE/"k4y_frozen_forward_identifiability.json"
FIELDS=("Direction","FrontBlocked","GoalX","GoalY","X","Y")

def require(x,msg):
    if not x: raise ValueError("K4Y_FAIL_CLOSED_"+msg)
def sha(blob):return hashlib.sha256(blob).hexdigest()
def canon(obj):return json.dumps(obj,sort_keys=True,separators=(",",":"),allow_nan=False).encode()

def extract_fit_only(raw):
    # Deliberately decode one exact top-level FIT JSON subtree, not CHECK or DEV.
    text=raw.decode("utf-8")
    match=re.search(r'(?<!\\)"FIT"\s*:',text)
    require(match is not None and text.count('"FIT"')==1,"FIT_FIELD_MISSING_OR_DUPLICATE")
    pos=match.end()
    while pos<len(text) and text[pos].isspace():pos+=1
    fit,end=json.JSONDecoder().raw_decode(text,pos)
    require(type(fit) is dict,"FIT_SUBTREE_TYPE")
    return fit

def read_original(archive,protocol):
    original=protocol["original"]
    require(sha(archive.read_bytes())==original["zip_sha256"],"ORIGINAL_ZIP")
    with zipfile.ZipFile(archive) as z:
        require(set(original["member_hashes"])==set(z.namelist()),"ORIGINAL_ZIP_MEMBER_SET")
        raw={}
        for name,pin in original["member_hashes"].items():
            raw[name]=z.read(name)
            require(sha(raw[name])==pin,"ORIGINAL_MEMBER_"+name)
    compare=json.loads(raw["comparison.json"])
    require(compare["result"]=="NO_REPEATABLE_BOUNDED_NATIVE_CURRICULUM_SOURCE_GAIN"
            and compare["exact_original_science_agreement"] is True
            and compare["scientific_first_use"] is False
            and compare["scientific_accepted"] is False
            and compare["two_processes_one_host"] is True,
            "ORIGINAL_K4X_NEGATIVE_OR_ORIGIN")
    a=extract_fit_only(raw["process-a.json"])
    b=extract_fit_only(raw["process-b.json"])
    # Original FIT includes measured wall/CPU and native IPC training times;
    # these vary between genuine independent processes. Require every frozen
    # scientific source byte/content to agree, but do NOT compare wall timing.
    stable=("fit_stream","FIT_source_gate","conventional_state_sha256",
            "original_public_fit_episodes","source_balance")
    for role in protocol["roles"]["curricula"]:
        require(set(a[role])==set(b[role]),"ORIGINAL_FIT_SCHEMA_DRIFT")
        for key in stable:
            require(canon(a[role][key])==canon(b[role][key]),
                    "ORIGINAL_FIT_SOURCE_SCIENCE_DRIFT_"+role+"_"+key)
    require(set(a)==set(protocol["roles"]["curricula"]),"SOURCE_CURRICULUM_SET")
    return a,sha(canon(a))

def forward_rows(fit,protocol):
    observed={}
    for method in protocol["roles"]["curricula"]:
        block=fit[method]
        require(block["FIT_source_gate"]["qualified"] is True,"ORIGINAL_FIT_UNQUALIFIED")
        rows=block["fit_stream"]
        require(len(rows)==protocol["original"]["expected_original_fit_transitions_per_curriculum"],
                "FIT_SOURCE_COUNT")
        family_steps=Counter(r["family"] for r in rows)
        require(all(family_steps[f]==6000 for f in ("empty","fourrooms")),"FIT_FAMILY_STEP_BUDGET")
        require(all(r["action"] in (0,1,2) and r["family"] in ("empty","fourrooms") and
                    type(r["seed"]) is int and 7300<=r["seed"]<=7323 for r in rows),
                "FIT_ROLE_OR_ACTION_DRIFT")
        full=[]
        for r in rows:
            if r["action"]!=2:continue  # never infer outcomes for unexecuted forward
            bef,aft=r["before"],r["after"]
            require(set(bef)==set(FIELDS) and set(aft)==set(FIELDS),"PUBLIC_FIELD_WHITELIST")
            for s in (bef,aft):
                require(type(s["FrontBlocked"]) is bool and
                        all(type(s[k]) is int and 0<=s[k]<=64 for k in ("X","Y","GoalX","GoalY")) and
                        type(s["Direction"]) is int and 0<=s["Direction"]<=3,
                        "PUBLIC_FEATURE_TYPE")
            require(bef["Direction"]==aft["Direction"],"FORWARD_ROTATION")
            moved=(bef["X"],bef["Y"])!=(aft["X"],aft["Y"])
            distance=abs(bef["X"]-aft["X"])+abs(bef["Y"]-aft["Y"])
            require(distance in (0,1),"FORWARD_NONLOCAL_PHYSICS")
            full.append({"family":r["family"],"seed":r["seed"],"blocked":bef["FrontBlocked"],
                         "dir":bef["Direction"],"moved":int(moved)})
        observed[method]=full
    return observed

def majority(labels):
    require(bool(labels),"EMPTY_TRAIN_GROUP")
    return int(sum(labels)*2>len(labels))
def predict_count(train,test,keyfn,default):
    by={}
    for r in train:
        key=keyfn(r)
        if key is None: continue
        by.setdefault(key,[]).append(r["moved"])
    result=[]
    for r in test:
        key=keyfn(r)
        if key not in by:
            result.append(default)
        else:
            vals=by[key]
            # Laplace empirical Bernoulli; tie picks majority fallback.
            p=(sum(vals)+1)/(len(vals)+2)
            result.append(int(p>0.5) if p!=0.5 else default)
    return result

def metrics(rows,predicted):
    require(len(rows)==len(predicted) and bool(rows),"UNACCOUNTED_HELDOUT")
    counts={"TP":0,"TN":0,"FP":0,"FN":0}
    for r,pred in zip(rows,predicted):
        require(pred in (0,1),"INVALID_PREDICTION")
        label=r["moved"]
        counts[{(1,1):"TP",(0,0):"TN",(0,1):"FP",(1,0):"FN"}[(label,pred)]]+=1
    tp,tn,fp,fn=[counts[k] for k in ("TP","TN","FP","FN")]
    require(tp+fn>0 and tn+fp>0,"MISSING_BINARY_CLASS")
    return {"n":len(rows),**counts,
            "accuracy":(tp+tn)/len(rows),
            "balanced_accuracy":0.5*(tp/(tp+fn)+tn/(tn+fp))}

def analyze(forward,protocol):
    out={}
    for curriculum,rows in forward.items():
        out[curriculum]={}
        for family in protocol["roles"]["families"]:
            family_rows=[r for r in rows if r["family"]==family]
            train=[r for r in family_rows if r["seed"]<=7315]
            held=[r for r in family_rows if r["seed"]>=7316]
            require(bool(train) and bool(held) and len(train)+len(held)==len(family_rows),
                    "FIT_ROLE_SPLIT")
            require({r["blocked"] for r in train}=={False,True} and
                    {r["blocked"] for r in held}=={False,True},
                    "INSUFFICIENT_SENSOR_VARIATION")
            base=majority([r["moved"] for r in train])
            common=[base]*len(held)
            direct=[int(not r["blocked"]) for r in held]
            learned=predict_count(train,held,lambda r:r["blocked"],base)
            direction=predict_count(train,held,lambda r:r["dir"],base)
            rng=random.Random(20261024)
            shuffled=[dict(r) for r in train]
            sensor=[r["blocked"] for r in shuffled]
            rng.shuffle(sensor)
            for r,sh in zip(shuffled,sensor):r["blocked"]=sh
            shuffled_result=predict_count(shuffled,held,lambda r:r["blocked"],base)
            out[curriculum][family]={
              "FIT_original_forward_train":len(train),
              "FIT_original_forward_retrospective_hold":len(held),
              "FIT_held_true_blocked":sum(r["blocked"] for r in held),
              "FIT_held_forward_moved":sum(r["moved"] for r in held),
              "sensor_invariance":sum(r["moved"]==int(not r["blocked"]) for r in family_rows)==len(family_rows),
              "comparators":{
                "unconditional_majority":metrics(held,common),
                "public_direction_count":metrics(held,direction),
                "learned_public_blocked_count":metrics(held,learned),
                "direct_published_public_sensor":metrics(held,direct),
                "shuffled_public_blocked_count":metrics(held,shuffled_result)
              }}
    acc=protocol["evaluation"]
    sensor_good=all(
      z["sensor_invariance"] and
      z["comparators"]["learned_public_blocked_count"]["balanced_accuracy"]==1.0 and
      z["comparators"]["direct_published_public_sensor"]["balanced_accuracy"]==1.0
      for fam in out.values() for z in fam.values())
    weak_control=all(
       out["random_equal_budget"][fam]["comparators"]["learned_public_blocked_count"]["balanced_accuracy"]-
       out["random_equal_budget"][fam]["comparators"]["unconditional_majority"]["balanced_accuracy"]>=0.05
       for fam in protocol["roles"]["families"])
    return out,("K4Y_PUBLIC_FORWARD_CONSEQUENCE_IDENTIFIABLE_IN_RECORDED_FIT"
                if sensor_good and weak_control else "K4Y_NOT_IDENTIFIED")

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--archive",required=True,type=Path)
    p.add_argument("--output",required=True,type=Path)
    args=p.parse_args()
    require(not args.output.exists() and args.output.parent.is_dir(),"NO_OUTPUT_OVERWRITE")
    contract=json.loads(FREEZE.read_text())
    require(contract["schema"]=="mass.lcrm01.k4y.frozen-forward-feasibility-fit-only-v1","CONTRACT")
    require(contract["governance"]["no_minigrid_install_import_reset"],"SIMULATOR_BAN")
    start=time.monotonic();cpu=time.process_time()
    fit,digest=read_original(args.archive,contract)
    fwd=forward_rows(fit,contract)
    by_group,verdict=analyze(fwd,contract)
    receipt={"schema":"mass.lcrm01.k4y.retrospective-fit-public-forward-identifiability-v1",
             "verdict":verdict,"original_archive_sha256":contract["original"]["zip_sha256"],
             "original_fit_digest_sha256":digest,"source_original_episodes_executed":0,
             "original_CHECK_DEV_rows_evaluated":False,"original_scientific_NO_GO_preserved":True,
             "native_architecture_superiority_claim":False,"source_only_fit_roles":True,
             "original_two_process_same_host":True,"comparisons":by_group,
             "cpu_seconds":time.process_time()-cpu,"wall_seconds":time.monotonic()-start,
             "peak_rss_bytes":resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024}
    args.output.write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
    print("K4Y_ORIGINAL_SHA256_FIT_ONLY_CUSTODY=PASS")
    for method,items in by_group.items():
        for family,z in items.items():
            print("K4Y_EVIDENCE="+json.dumps({"curriculum":method,"family":family,
                "count":z["FIT_original_forward_retrospective_hold"],
                "blocked":z["FIT_held_true_blocked"],
                "learned_bacc":z["comparators"]["learned_public_blocked_count"]["balanced_accuracy"],
                "majority_bacc":z["comparators"]["unconditional_majority"]["balanced_accuracy"]},
                sort_keys=True))
    print("K4Y_FROZEN_DECISION="+verdict)
    print("K4Y_ORIGINAL_EPISODES=0_SCINCE_FIRSTUSE_DENIED")
if __name__=="__main__":main()
