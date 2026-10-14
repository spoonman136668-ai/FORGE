"""Independent F14 verifier: recompute source cases and all learned values.

It does not import F14's producer. Earlier used F3 source cases only.
"""
import argparse
from fractions import Fraction
import hashlib
import json
from pathlib import Path

SOURCE="5797a257a75fe139313e8486cd1a1ae79c44b148"
GRID=(4,12,36,108)

def need(ok,why):
    if not ok:raise ValueError("F14_REVIEW_"+why)

def canonical(x):
    return (json.dumps(x,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n").encode()

def parse(rows,seeds):
    need(type(rows) is list and len(rows)==576,"COMPLETE_SOURCE_ARMS")
    out={}
    for r in rows:
        need(type(r.get("arm")) is int and 0<=r["arm"]<6
             and type(r.get("seed")) is int and r["seed"] in seeds
             and r.get("pair") in ([8,10],[11,13])
             and r.get("regime") in ("steady","onset1")
             and r.get("public_reads")==10,
             "HISTORICAL_SCOPE")
        trace=r["sample_trace"]
        need(trace["addresses"][:2]==[[0,1],[0,1]]
             and len(trace["public_values"])==5
             and all(len(v)==2 for v in trace["public_values"][:2])
             and trace["decision"]["action_index"]==r["arm"]
             and trace["decision"]["reads"]==10,
             "REAL_PUBLIC_SOURCE_TRACE")
        raw=tuple(x for readings in trace["public_values"][:2] for x in readings)
        need(len(raw)==4 and all(type(v) is int and 0<=v<16 for v in raw),
             "PUBLIC_SCALAR_RANGE")
        loss=r["pre_mismatch"]+r["post_mismatch"]
        need(type(loss) is int and 0<=loss<=8,"TASK_LOSS")
        key=(r["seed"],tuple(r["pair"]),r["regime"],
             tuple(r["family"]),r["matching_policy"])
        arms=out.setdefault(key,{})
        need(r["arm"] not in arms,"REPEATED_ACTION")
        arms[r["arm"]]=(raw,loss)
    need(len(out)==96,"96_MATCHED_CASES")
    for arms in out.values():
        need(set(arms)==set(range(6)) and
             len({arms[i][0] for i in range(6)})==1,
             "SIX_MATCHED_COUNTERFACTUALS")
    return out

def estimate(data,smoothing):
    need(smoothing in GRID and len(data)>0,"SMOOTHING_RANGE")
    overall=tuple(Fraction(sum(arms[a][1] for arms in data.values()),len(data))
                  for a in range(6))
    values={}
    for position in range(4):
        for token in range(16):
            matched=[arms for arms in data.values() if arms[0][0][position]==token]
            values[position,token]=tuple(
                (sum(arms[a][1] for arms in matched)+smoothing*overall[a])/
                (len(matched)+smoothing) for a in range(6))
    return overall,values

def select(observed,trained):
    global_values,token_values=trained
    vals=[]
    for arm in range(6):
        subtotal=sum((token_values[p,token][arm]-global_values[arm]
                      for p,token in enumerate(observed)),Fraction(0))
        vals.append(global_values[arm]+subtotal/4)
    return min(range(6),key=lambda a:(vals[a],a))

def fingerprint(trained):
    overall,tokens=trained
    frac=lambda f:[f.numerator,f.denominator]
    x={"global":[frac(y) for y in overall],
       "positions":[{"position":p,"token":v,
            "task_values":[frac(y) for y in tokens[p,v]]}
             for p in range(4) for v in range(16)]}
    return hashlib.sha256(canonical(x)).hexdigest()

def review(document,inputs):
    f11raw,f11wraw,f13raw,f13wraw=inputs
    f11=json.loads(f11raw); f11w=json.loads(f11wraw)
    f13=json.loads(f13raw); f13w=json.loads(f13wraw)
    need(f11.get("schema")=="forge.f11.automatic-task-aligned-information-value-engineering.v1"
         and f11.get("source_commit")==SOURCE
         and f11.get("scientific_dispatch_authorized") is False
         and f11w.get("schema")=="forge.f11.independent-task-aligned-value-review.v1"
         and f11w.get("training_real_source_case_arms")==576
         and f11w.get("validation_real_source_case_arms")==672
         and f11w.get("best_constant_historical_mismatch")==66
         and f11w.get("scientific_dispatch_authorized") is False
         and f13.get("schema")=="forge.f13.raw-public-task-value-transfer.v1"
         and f13.get("status")=="PREVIOUS_F3_SOURCE_ONLY_NOT_SCIENCE"
         and f13.get("source_commit")==SOURCE
         and f13.get("parent_f11_sha256")==hashlib.sha256(f11raw).hexdigest()
         and f13.get("independent_f11_sha256")==hashlib.sha256(f11wraw).hexdigest()
         and f13.get("validation_task_mismatches")==74
         and f13.get("scientific_dispatch_authorized") is False
         and f13w.get("schema")=="forge.f13.independent-raw-public-transfer-review.v1"
         and f13w.get("historical_task_mismatches")==74
         and f13w.get("best_fixed_historical_mismatches")==66
         and f13w.get("scientific_dispatch_authorized") is False,
         "REVIEWED_PARENT_NEGATIVE")
    need(document.get("schema")=="forge.f14.factorized-public-task-value.v1"
         and document.get("status")=="REUSED_F3_HISTORICAL_SOURCE_ONLY"
         and document.get("source_commit")==SOURCE
         and document.get("f11_sha256")==hashlib.sha256(f11raw).hexdigest()
         and document.get("f11_witness_sha256")==hashlib.sha256(f11wraw).hexdigest()
         and document.get("f13_sha256")==hashlib.sha256(f13raw).hexdigest()
         and document.get("f13_witness_sha256")==hashlib.sha256(f13wraw).hexdigest()
         and document.get("training_seeds")==[67204,67205]
         and document.get("validation_seeds")==[67206,67207]
         and document.get("training_family_folds")==16,
         "IMMUTABLE_PROVENANCE")
    training=parse(f11["training"],(67204,67205))
    validation=parse([r for r in f11["validation"]
                      if type(r.get("arm")) is int],(67206,67207))
    families=sorted({key[3] for key in training})
    need(len(families)==4,"FOUR_FAMILIES")
    cv=[]
    for smoothing in GRID:
        losses=0;h=[0]*6
        for family in families:
            part={k:v for k,v in training.items() if k[3]!=family}
            excluded={k:v for k,v in training.items() if k[3]==family}
            need(len(part)==72 and len(excluded)==24,"FAMILY_ISOLATION")
            model=estimate(part,smoothing)
            for arms in excluded.values():
                arm=select(arms[0][0],model)
                losses+=arms[arm][1];h[arm]+=1
        cv.append({"smoothing":smoothing,
                   "training_family_holdout_mismatches":losses,
                   "action_counts":h})
    frozen=min(cv,key=lambda p:(
        p["training_family_holdout_mismatches"],GRID.index(p["smoothing"])))
    model=estimate(training,frozen["smoothing"])
    decisions=[];counts=[0]*6
    for key,arms in sorted(validation.items()):
        observed=arms[0][0]
        arm=select(observed,model)
        counts[arm]+=1
        decisions.append({"seed":key[0],"pair":list(key[1]),
            "regime":key[2],"family":list(key[3]),
            "matching_policy":key[4],"public_anchors":list(observed),
            "chosen_action":arm,"task_mismatch":arms[arm][1]})
    controls={str(i):sum(v[i][1] for v in validation.values()) for i in range(6)}
    total=sum(x["task_mismatch"] for x in decisions)
    need(document.get("candidate_training_scores")==cv
         and document.get("frozen_smoothing")==frozen["smoothing"]
         and document.get("frozen_model_sha256")==fingerprint(model)
         and document.get("validation_choices")==decisions
         and document.get("validation_action_counts")==counts
         and document.get("validation_task_mismatches")==total
         and document.get("six_fixed_validation_mismatches")==controls
         and controls["2"]==66 and min(controls.values())==66,
         "INDEPENDENT_SOURCE_RECOMPUTATION")
    need(document.get("scientific_winner_selected") is False
         and document.get("scientific_dispatch_authorized") is False
         and all(document.get(k)==0 for k in (
             "new_originals","new_cohort_accesses","first_use_claims",
             "paid_api_calls")),"UNAUTHORIZED_SCIENCE")
    return {"schema":"forge.f14.independent-factorized-value-review.v1",
       "status":"HISTORICAL_SOURCE_ONLY_NO_NEW_SCIENCE",
       "source_commit":SOURCE,"training_case_arms":576,
       "validation_case_arms":576,"training_exclusive_folds":16,
       "frozen_smoothing":frozen["smoothing"],
       "model_sha256":fingerprint(model),
       "historical_task_mismatches":total,
       "best_fixed_historical_mismatches":66,
       "scientific_dispatch_authorized":False,
       "new_first_use_claims":0}

def main():
    p=argparse.ArgumentParser()
    for n in ("record","f11","f11-witness","f13","f13-witness","out"):
        p.add_argument("--"+n,required=True)
    x=p.parse_args()
    doc=json.loads(Path(x.record).read_bytes())
    raw=[Path(getattr(x,n.replace("-","_"))).read_bytes()
         for n in ("f11","f11-witness","f13","f13-witness")]
    result=review(doc,raw)
    with Path(x.out).open("xb") as f:f.write(canonical(result))
    print("F14_INDEPENDENT_FACTORIZED_PUBLIC_TASK_REVIEW=PASS")
    print("F14_SOURCE_ONLY_HISTORICAL_MISMATCHES="+str(result["historical_task_mismatches"]))
    print("F14_NEW_FIRST_USE_CLAIMS=ZERO")
if __name__=="__main__":main()
