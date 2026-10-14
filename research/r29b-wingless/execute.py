"""R29B frozen, bounded smooth robust source-family Wingless scientific original.

First-use launcher is deliberately separate. This module has no network or
GitHub credentials and cannot claim authority.
"""
import argparse
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path

PREREG_BLOB="ccc7896760d07adcbc385ac6f1a04b4a449969d7"
PARENT_SHA="b1e4972f04142f1f35f76f9483b12491dec4846c"
ID="W-FORGE-R29BB-SMOOTH-ROBUST-01"

def load_parent(path):
    spec=importlib.util.spec_from_file_location("w52_r29b_pinned",path)
    if not spec or not spec.loader:raise ValueError("R29B_SOURCE_MISSING")
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module

def families(w52,block):
    out={generator:[] for generator in w52.GEN}
    for seed in block:
        for idx,generator in enumerate(w52.GEN):
            for entity in range(9):
                if entity%3!=(idx+seed)%3:continue
                for site in w52.TRAIN_SITES:
                    for amp in (1,2):
                        base,pos,neg=w52.w37.recoded_example(seed,entity,generator,"identity",site,amp,True)
                        a=w52.w42.feature(base,pos);b=w52.w42.feature(base,neg)
                        delta=tuple(x-y for x,y in zip(a,b))
                        out[generator].extend(((delta,1),(tuple(-x for x in delta),-1)))
    if any(len(rows)!=576 for rows in out.values()):raise ValueError("R29B_TRAIN_BUDGET_DRIFT")
    return out

def smooth_fit(w52,block):
    training=families(w52,block)
    w=[0.0]*16
    for _ in range(32):
        ordered=list(training.items())
        losses=[sum(max(0.0,1.0-y*sum(a*b for a,b in zip(w,x))) for x,y in rows)/576 for _,rows in ordered]
        anchor=max(losses)
        strengths=[math.exp(loss-anchor) for loss in losses]
        norm=sum(strengths)
        if not math.isfinite(norm) or norm<=0:raise ValueError("R29B_INVALID_SOFTMAX")
        weights=[s/norm for s in strengths]
        gradient=[0.0]*16
        for (family,rows),importance in zip(ordered,weights):
            for x,y in rows:
                if y*sum(a*b for a,b in zip(w,x))<=0:
                    for i in range(16):gradient[i]+=importance*y*x[i]/576
        w=[a+0.1*g for a,g in zip(w,gradient)]
        if any(not math.isfinite(a) for a in w):raise ValueError("R29B_NONFINITE_WEIGHTS")
    return {"weights":w,"source_counts":{g:len(rows) for g,rows in training.items()},
            "weights_sha256":hashlib.sha256(json.dumps(w,separators=(",",":")).encode()).hexdigest()}

def minimax_fit(w52,block):
    training=families(w52,block)
    w=[0.0]*16
    for _ in range(32):
        losses=[]
        for generator,rows in training.items():
            loss=sum(max(0.0,1.0-y*sum(a*b for a,b in zip(w,x))) for x,y in rows)/576
            losses.append((loss,generator))
        selected=max(range(len(losses)),key=lambda i:losses[i][0]) # deterministic earliest tie
        rows=training[losses[selected][1]]
        gradient=[0.0]*16
        for x,y in rows:
            if y*sum(a*b for a,b in zip(w,x))<=0:
                for i in range(16):gradient[i]+=y*x[i]
        w=[a+0.1*g/576 for a,g in zip(w,gradient)]
        if any(not math.isfinite(a) for a in w):raise ValueError("R29B_NONFINITE_WEIGHTS")
    return {"weights":w,"source_counts":{g:len(rows) for g,rows in training.items()},
            "weights_sha256":hashlib.sha256(json.dumps(w,separators=(",",":")).encode()).hexdigest()}

def evaluate(w52,model,heldout):
    generator_scores={g:{"correct":0.0,"total":0} for g in w52.GEN}
    rows=[]
    for seed in heldout:
        row={"seed":seed,"correct":0.0,"total":0,"family_correct":{}}
        for generator in w52.GEN:
            subtotal=0.0
            for site in w52.SITES:
                for entity in range(9):
                    base,pos,neg=w52.w37.recoded_example(seed,entity,generator,"identity",site,3,False)
                    a=w52.w42.feature(base,pos);b=w52.w42.feature(base,neg)
                    margin=sum(w*(x-y) for w,x,y in zip(model["weights"],a,b))
                    credit=w52.w45.credit(margin,True)+w52.w45.credit(-margin,False)
                    subtotal+=credit;row["correct"]+=credit;row["total"]+=2
                    generator_scores[generator]["correct"]+=credit
                    generator_scores[generator]["total"]+=2
            row["family_correct"][generator]=subtotal
        if row["total"]!=108:raise ValueError("R29B_SEALED_CASE_DRIFT")
        rows.append(row)
    result={"accuracy":sum(row["correct"] for row in rows)/(len(heldout)*108),
            "family_accuracy":{g:v["correct"]/v["total"] for g,v in generator_scores.items()},
            "by_seed":rows,
            "weights_sha256":model["weights_sha256"],
            "source_training_example_counts":model["source_counts"]}
    return result

def run(m,w52):
    if set(m["arms"])!={"train_only_minimax_source_margin","train_only_smooth_robust_source_margin"}:raise ValueError("R29B_ARM_DRIFT")
    blocks=m["development_blocks"];heldout=m["sealed_heldout_seeds"]
    if len(blocks)!=3 or any(len(b)!=16 for b in blocks) or len(heldout)!=48:raise ValueError("R29B_COHORT_SHAPE_DRIFT")
    if len(set(sum(blocks,[])+heldout))!=96:raise ValueError("R29B_COHORT_OVERLAP")
    results={}
    comparisons=[]
    for i,block in enumerate(blocks,1):
        control=minimax_fit(w52,block)
        candidate=smooth_fit(w52,block)
        a=evaluate(w52,control,heldout);b=evaluate(w52,candidate,heldout)
        results[str(i)]={"control":a,"candidate":b}
        deltas={g:b["family_accuracy"][g]-a["family_accuracy"][g] for g in a["family_accuracy"]}
        gain=min(b["family_accuracy"].values())-min(a["family_accuracy"].values())
        strict=(gain>=0.05 and b["accuracy"]>=0.55 and min(deltas.values())>=-0.05)
        comparisons.append({"block":i,"worst_family_gain":gain,"candidate_accuracy":b["accuracy"],
                            "family_deltas":deltas,"strict":strict,"partial":gain>=0.02})
    label=("ROBUST_SMOOTH_GAIN" if all(c["strict"] for c in comparisons)
           else "PARTIAL_SMOOTH_GAIN" if sum(c["partial"] for c in comparisons)>=2
           else "NO_CONFIRMED_SMOOTH_GAIN")
    return {"schema":"forge.r29b.source-robust-original.v1","experiment_id":ID,
            "parent_r28_run_id":m["parent_run_id"],
            "prereg_git_blob":PREREG_BLOB,"method_source_sha":PARENT_SHA,
            "development_blocks":blocks,"sealed_heldout_seeds":heldout,
            "results":results,"comparisons":comparisons,
            "classification":label,"model_calls":0,
            "science_production_accepted":False}

def main():
    p=argparse.ArgumentParser()
    for key in ("manifest","wingless_root","out","run_id"):p.add_argument("--"+key.replace("_","-"),required=True)
    a=p.parse_args()
    path=Path(a.manifest);raw=path.read_bytes()
    blob=hashlib.sha1(b"blob "+str(len(raw)).encode()+bytes([0])+raw).hexdigest()
    if blob!=PREREG_BLOB or not a.run_id.isdecimal():raise ValueError("R29B_FROZEN_IDENTITY_DRIFT")
    m=json.loads(raw)
    if m["experiment_id"]!=ID or m["method_parent_commit"]!=PARENT_SHA:raise ValueError("R29B_EXPERIMENT_ID_DRIFT")
    root=Path(a.wingless_root)
    w52=load_parent(root/m["method_parent_file"])
    result=run(m,w52);result["github_run_id"]=a.run_id
    payload=(json.dumps(result,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n").encode()
    with Path(a.out).open("xb") as f:
        f.write(payload);f.flush();os.fsync(f.fileno())
    print("R29B_ORIGINAL_SHA256="+hashlib.sha256(payload).hexdigest())
    print("R29B_BOUNDED_ORIGINAL_EXECUTED=PASS")
if __name__=="__main__":main()
