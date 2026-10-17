"""F125-R prospective TRAIN-only source headroom and public fixed controls.

Headroom gate is a frozen *source eligibility* check, not model performance.
It uses only F125-R TRAIN seeds and authenticated F118/F120 advisory vectors.
No protected confirmation, learned model, or reseeding for favorable scores.
"""
from __future__ import annotations
import argparse,hashlib,json,os,re,sys
from pathlib import Path
import f118_autonomy_feedback as f118
import f120_generated_environment as f120
import f125r_freeze_admission as freeze
import f125r_train_environment as env

SCHEMA="forge.autonomy.f125r.public-train-source-headroom.v1"

def need(ok,why):env.need(bool(ok),"HEADROOM_"+why)

def public_paths(g):
    env.validate(g)
    state=[(g["start"],())]
    for role in g["roles"]:
        next_state=[]
        for node,edges in state:
            for edge in g["edges"]:
                if edge["from"]==node and edge["role"]==role:
                    next_state.append((edge["to"],edges+(edge,)))
                    need(len(next_state)<=256,"PUBLIC_PATH_LIMIT")
        state=next_state
    selected=[route for node,route in state if node==g["target"]]
    need(6<=len(selected)<=10,"FROZEN_PUBLIC_ROUTE_COUNT")
    return selected

def approximate_12_of_16(g):
    # Port of the frozen F123 fixed_soft_path test to new graph lengths.
    return any(all(sum(a==b for a,b in zip(left["dst_bits"],right["src_bits"]))>=12
                   for left,right in zip(route,route[1:]))
               for route in public_paths(g))

def role_only(g):
    return bool(public_paths(g))

def exact_ceiling(g):
    return bool(env.graph_paths(g,require_tokens=True))

def score(rows,predict):
    need(type(rows) is list and len(rows)==128,"FULL_TRAIN_ONLY_DENOMINATOR")
    paired=pos=neg=0
    for k in range(0,len(rows),2):
        p,a=rows[k];n,b=rows[k+1]
        need(a==1 and b==0,"PAIRED_LABEL_ORDER")
        yes,no=bool(predict(p)),not bool(predict(n))
        paired+=int(yes and no)
        pos+=int(yes);neg+=int(no)
    return {"pairs":64,"paired_correct":paired,
            "positive_correct":pos,"negative_correct":neg,
            "balanced_accuracy":round((pos+neg)/128,8)}

def run(advisory,source):
    cfg,freeze_sha=freeze.frozen()
    need(type(source) is str and re.fullmatch(r"[0-9a-f]{40}",source)
         and (not os.environ.get("GITHUB_SHA") or
              os.environ["GITHUB_SHA"]==source),"LIVE_SOURCE_IDENTITY")
    candidates=f120.validate(advisory,source)
    lanes=[]
    min_margin=cfg["evaluation"]["headroom_eligibility"][
        "minimum_TRAIN_ceiling_minus_best_fixed_fraction"]
    need(min_margin==0.08,"HEADROOM_FREEZE_TAMPER")
    for lane in ("Wingless","Yggdrasil"):
        entries=candidates[lane]
        need(len(entries)==2 and entries[0]["candidate_index"]==2
             and entries[1]["candidate_index"]==3,"INDEPENDENT_SOURCE_ID")
        vectors=[e["vector"] for e in entries]
        rows=env.train_rows(lane,vectors)
        exact=score(rows,exact_ceiling)
        soft=score(rows,approximate_12_of_16)
        role=score(rows,role_only)
        need(exact["paired_correct"]==64 and
             all(env.graph_paths(g,True)==int(y) for g,y in rows),
             "FAILED_PUBLIC_EXACT_CEILING")
        fixed=max(soft["paired_correct"],role["paired_correct"])
        headroom=(64-fixed)/64
        lanes.append({"lane":lane,
          "source_candidate_shas":[e["source_candidate_sha256"] for e in entries],
          "vectors_sha256":env.digest(vectors),
          "full_train_rows_sha256":env.digest(rows),
          "train_pairs":64,
          "fixed_12bit_soft":soft,"fixed_role_only":role,
          "exact_public_symbolic_ceiling":exact,
          "best_eligible_fixed_nonlearned_paired":fixed,
          "train_ceiling_minus_best_fixed_fraction":round(headroom,8),
          "minimum_frozen_headroom":min_margin,
          "headroom_eligible":headroom>=min_margin,
          "unfavorable_and_rejected_cases_preserved":True})
    qualified=all(l["headroom_eligible"] for l in lanes)
    return {"schema":SCHEMA,"source_sha":source,
       "freeze_git_blob":freeze.FROZEN_BLOB,
       "freeze_sha256":freeze_sha,
       "advisory_sha256":env.digest(advisory),
       "phase":"PUBLIC_SYNTHETIC_TRAIN_ELIGIBILITY_ONLY",
       "lanes":lanes,
       "disposition":"TRAIN_HEADROOM_ELIGIBLE" if qualified else
                     "UNINFORMATIVE_HEADROOM_DO_NOT_SELECT_OTHER_SEEDS",
       "all_lanes_headroom_eligible":qualified,
       "trained_weights_created":False,
       "reserved_confirm_generated":False,"scientific_acceptance":False,
       "optimizer_promotion":False,"scientific_first_use":False,
       "originals_dispatched":0,
       "no_seed_or_threshold_retuning":True}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--advisory",required=True)
    p.add_argument("--source-sha",required=True)
    p.add_argument("--output",required=True)
    args=p.parse_args()
    doc=run(f118.load_report(args.advisory),args.source_sha)
    out=Path(args.output)
    need(out.parent.is_dir() and not out.exists(),
         "REFUSE_EXISTING_EVIDENCE_OVERWRITE")
    content=(json.dumps(doc,sort_keys=True,separators=(",",":"))+"\n").encode()
    out.open("xb").write(content)
    print("F125R_TRAIN_HEADROOM_RECEIPT_SHA256="+hashlib.sha256(content).hexdigest())
    for lane in doc["lanes"]:
        print("F125R_"+lane["lane"].upper()+"_FIXED_SOFT="+
              str(lane["fixed_12bit_soft"]["paired_correct"])+"/64")
        print("F125R_"+lane["lane"].upper()+"_HEADROOM="+
              str(lane["train_ceiling_minus_best_fixed_fraction"]))
    print("F125R_TRAIN_ELIGIBILITY="+doc["disposition"])
    print("F125R_PROTECTED_CONFIRM_USED=false")

if __name__=="__main__":
    try:main()
    except (env.Invalid,freeze.Invalid,f118.Quarantined,f120.Invalid,
            KeyError,ValueError,TypeError,IndexError,OSError) as exc:
        print("F125R_HEADROOM_QUARANTINED="+str(exc),file=sys.stderr)
        raise SystemExit(1)
