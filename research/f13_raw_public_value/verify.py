"""Independent F13 source-bound raw public feature / train-only fold replay.

Rebuilds all 576 F11 training and 576 fixed validation action labels
from independently witnessed frozen real Y070 source history. Does not
import the producing F13 learner or use prospective data.
"""
import argparse,hashlib,json
from fractions import Fraction
from pathlib import Path

K=(4,12,24,72)
SOURCE="5797a257a75fe139313e8486cd1a1ae79c44b148"

def need(x,why):
    if not x:raise ValueError("F13_INDEPENDENT_"+why)

def cases(rows,seeds):
    seen={}
    need(type(rows) is list and len(rows)==576,"COMPLETE_ACTION_CASES")
    for row in rows:
        need(type(row["arm"]) is int and 0<=row["arm"]<6
             and row["seed"] in seeds
             and row["pair"] in ([8,10],[11,13])
             and row["regime"] in ("steady","onset1")
             and row["public_reads"]==10,"CASES_SCOPE")
        key=(row["seed"],tuple(row["pair"]),row["regime"],
             tuple(row["family"]),row["matching_policy"])
        trace=row["sample_trace"]
        need(trace["addresses"][:2]==[[0,1],[0,1]] and
             len(trace["public_values"])==5 and
             all(len(pair)==2 for pair in trace["public_values"][:2]),
             "RAW_ANCHOR_SHAPE")
        public=tuple(v for pair in trace["public_values"][:2] for v in pair)
        need(len(public)==4 and all(type(x) is int and 0<=x<16 for x in public),
             "PUBLIC_ONLY_INPUTS")
        loss=row["pre_mismatch"]+row["post_mismatch"]
        need(type(loss) is int and 0<=loss<=8 and
             row["sample_trace"]["decision"]["action_index"]==row["arm"] and
             row["sample_trace"]["decision"]["reads"]==10,"SOURCE_TASK_LABEL")
        arm=seen.setdefault(key,{})
        need(row["arm"] not in arm,"DUPLICATE_ACTION")
        arm[row["arm"]]=(public,loss)
    need(len(seen)==96,"FULL_MATCHED_CASE_COUNT")
    for arms in seen.values():
        need(set(arms)==set(range(6))
             and len({v[0] for v in arms.values()})==1,
             "COUNTERFACTUAL_FEATURE_IDENTITY")
    return seen

def decision(public,training,k):
    need(k in K and len(public)==4 and len(training)>=k,
         "TRAIN_ONLY_K")
    indexed=[]
    for key,arms in training.items():
        reference=arms[0][0]
        d=sum(min((a-b)%16,(b-a)%16) for a,b in zip(public,reference))
        indexed.append((d,key,arms))
    indexed.sort(key=lambda item:(item[0],item[1]))
    selected=indexed[:k]
    n=len(training)
    costs=[]
    for arm in range(6):
        all_loss=sum(arms[arm][1] for arms in training.values())
        near_loss=sum(arms[arm][1] for _,_,arms in selected)
        costs.append((Fraction(near_loss,1)+Fraction(8*all_loss,n))/(k+8))
    return min(range(6),key=lambda a:(costs[a],a))

def verify(doc,inputs):
    f11raw,f11wraw,f12raw,f12wraw=inputs
    f11=json.loads(f11raw);f11w=json.loads(f11wraw)
    f12=json.loads(f12raw);f12w=json.loads(f12wraw)
    need(f11.get("schema")=="forge.f11.automatic-task-aligned-information-value-engineering.v1"
         and f11.get("source_commit")==SOURCE and
         f11.get("new_first_use_claims")==0
         and f11.get("scientific_dispatch_authorized") is False and
         f11w.get("schema")=="forge.f11.independent-task-aligned-value-review.v1"
         and f11w.get("training_real_source_case_arms")==576
         and f11w.get("validation_real_source_case_arms")==672
         and f11w.get("best_constant_historical_mismatch")==66
         and f11w.get("learned_historical_mismatch")==71
         and f11w.get("scientific_dispatch_authorized") is False and
         f12.get("schema")=="forge.f12.cross-context-task-value-transfer.v1"
         and f12.get("historical_validation_mismatches")==71
         and f12.get("scientific_dispatch_authorized") is False
         and f12w.get("schema")=="forge.f12.independent-cross-context-review.v1"
         and f12w.get("historical_validation_mismatches")==71,
         "PARENT_EVIDENCE")
    need(doc.get("schema")=="forge.f13.raw-public-task-value-transfer.v1"
         and doc.get("status")=="PREVIOUS_F3_SOURCE_ONLY_NOT_SCIENCE"
         and doc.get("source_commit")==SOURCE
         and doc.get("parent_f11_sha256")==hashlib.sha256(f11raw).hexdigest()
         and doc.get("independent_f11_sha256")==hashlib.sha256(f11wraw).hexdigest()
         and doc.get("parent_f12_sha256")==hashlib.sha256(f12raw).hexdigest()
         and doc.get("independent_f12_sha256")==hashlib.sha256(f12wraw).hexdigest()
         and doc.get("train_seed_ids")==[67204,67205]
         and doc.get("validation_seed_ids")==[67206,67207],
         "SOURCE_PROVENANCE")
    trained=cases(f11["training"],(67204,67205))
    validation=cases([x for x in f11["validation"] if type(x["arm"]) is int],
                     (67206,67207))
    families=sorted({x[3] for x in trained})
    need(len(families)==4,"SOURCE_FAMILY_FOLDS")
    candidates=[]
    for k in K:
        loss=0;counts=[0]*6
        for family in families:
            fit={key:v for key,v in trained.items() if key[3]!=family}
            excluded={key:v for key,v in trained.items() if key[3]==family}
            need(len(fit)==72 and len(excluded)==24,"NO_FAMILY_LEAK")
            for arms in excluded.values():
                action=decision(arms[0][0],fit,k)
                counts[action]+=1
                loss+=arms[action][1]
        candidates.append({"neighbors":k,
                           "training_crossfamily_mismatches":loss,
                           "action_counts":counts})
    chosen=min(candidates,key=lambda x:(
        x["training_crossfamily_mismatches"],K.index(x["neighbors"])))
    need(doc.get("training_crossfamily_candidate_scores")==candidates
         and doc.get("frozen_neighbors")==chosen["neighbors"],"TRAINING_ONLY_FIT")
    selected=[];h=[0]*6
    for key,arms in sorted(validation.items()):
        public=arms[0][0]
        arm=decision(public,trained,chosen["neighbors"])
        h[arm]+=1
        selected.append({"seed":key[0],"pair":list(key[1]),
            "regime":key[2],"family":list(key[3]),
            "matching_policy":key[4],"public_anchors":list(public),
            "chosen_action":arm,"task_mismatch":arms[arm][1]})
    baseline={str(i):sum(arms[i][1] for arms in validation.values())
              for i in range(6)}
    score=sum(x["task_mismatch"] for x in selected)
    need(baseline["0"]==74 and baseline["2"]==66 and
         min(baseline.values())==66
         and doc.get("validation_choices")==selected
         and doc.get("validation_action_counts")==h
         and doc.get("validation_task_mismatches")==score
         and doc.get("six_fixed_validation_mismatches")==baseline,
         "REAL_Y070_SOURCE_LABEL_REPLAY")
    need(doc.get("scientific_winner_selected") is False
         and doc.get("scientific_dispatch_authorized") is False
         and all(doc.get(k)==0 for k in (
             "new_cohort_accesses","new_originals","first_use_claims",
             "paid_api_calls")),"FALSE_AUTHORITY")
    return {"schema":"forge.f13.independent-raw-public-transfer-review.v1",
        "status":"HISTORICAL_SOURCE_ONLY_NO_PROSPECTIVE_SCIENCE",
        "training_case_arms":576,"fixed_validation_case_arms":576,
        "training_family_folds":16,
        "frozen_neighbors":chosen["neighbors"],
        "historical_task_mismatches":score,
        "best_fixed_historical_mismatches":66,
        "scientific_dispatch_authorized":False,
        "first_use_claims":0}

def main():
    p=argparse.ArgumentParser()
    for key in ("record","f11","f11-witness","f12","f12-witness","out"):
        p.add_argument("--"+key,required=True)
    x=p.parse_args()
    inputs=[Path(getattr(x,k.replace("-","_"))).read_bytes()
            for k in ("f11","f11-witness","f12","f12-witness")]
    out=verify(json.loads(Path(x.record).read_bytes()),inputs)
    with Path(x.out).open("xb") as f:
        f.write((json.dumps(out,sort_keys=True,separators=(",",":"))+"\n").encode())
    print("F13_INDEPENDENT_RAW_PUBLIC_TASK_REPLAY=PASS")
    print("F13_REVIEW_HISTORICAL_MISMATCHES="+str(out["historical_task_mismatches"]))
    print("F13_NEW_SCIENTIFIC_FIRST_USE=ZERO")
if __name__=="__main__":main()
