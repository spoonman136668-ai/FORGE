"""F124-W Yggdrasil causal-evidence score drift and decision calibration.

An evaluator-only, instrumented mirror of the original O/R/S/U policies.
The true public causal prefix is constructed ONLY after independent prediction
and used only for labelling pre-existing candidates, never for selecting cells.
Require exact hexadecimal identity with the unmodified reference model.
"""
from __future__ import annotations
from collections import Counter
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import f124w_fresh_source as src
import f124v_yggdrasil_causal_trace as V
import f124o_native_learners as O

FREEZE=Path(__file__).resolve().parents[1]/"reference/research-intake/f124w-memory-cap-score-drift-freeze.json"
FREEZE_BLOB="eb36f4e409631127cf155da8afce4515c7fac2e7"
SCHEMA="forge.research.f124w.yggdrasil-score-drift-calibration.v1"
ARMS=("O","R","S","U")


def need(ok,msg):
    src.need(ok,"SCORE_"+msg)


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,
                   separators=(",",":")).encode()).hexdigest()


def frozen():
    raw=FREEZE.read_bytes().replace(b"\r\n",b"\n")
    need(src.git_blob(raw)==FREEZE_BLOB,"PREIMPLEMENTATION_BLOB_DRIFT")
    p=json.loads(raw)
    need(p["schema"]=="forge.research.f124w.memory-cap-score-drift-freeze.v1"
         and p["stage"]=="FROZEN_BEFORE_IMPLEMENTATION"
         and p["parent"]["qualified_sha"]==
               "e862b71c7ca3ec52a399f7054a64db676b6cb54a"
         and p["Yggdrasil"]["arms"]==
               ["O_original","R_continuous_readout","S_cell_value_credit","U_frozen_rank"]
         and all(v is False for v in p["authority"].values()),
         "PREREGISTRATION_DRIFT")
    src.frozen()
    return p


def shadow(arm,g,w,prefix=None):
    src.validate_public(g)
    base=list(w["base"])
    edges=O.sorted_edges(g)
    active=[(g["start"],None,0.)]
    retained=[]
    evictions=0
    readout_sum=readout_n=final_sum=final_n=0.
    hops=[]
    def compat(carried,bits):
        if carried is None:return 1.
        return sum(base[j]*sum(int(a==b) for a,b in zip(
                   carried[j*4:j*4+4],bits[j*4:j*4+4]))/4.
                   for j in range(4))/4.
    def prospect(edge,nextrole):
        if nextrole is None:return .5
        q=[t for t in edges if t["from"]==edge["to"] and t["role"]==nextrole]
        return max((sum(int(a==b) for a,b in zip(edge["dst_bits"],
                        t["src_bits"]))/16. for t in q),default=0.)
    for i,role in enumerate(g["roles"]):
        nextrole=g["roles"][i+1] if i+1<len(g["roles"]) else None
        proposed=[]
        for node,carried,score in active+retained:
            for e in edges:
                if e["from"]!=node or e["role"]!=role:continue
                sim=compat(carried,e["src_bits"])
                normal_score_increment=base[4]*(sim-.35)
                raw_value_credit=0.
                rank_credit=0.
                nextscore=score+normal_score_increment
                rank=base[5]*(sim-.5)
                if arm=="R":
                    soft=O.sigmoid(6.*(sim-.5))
                    readout_sum+=soft
                    readout_n+=1
                    if i==len(g["roles"])-1 and e["to"]==g["target"]:
                        final_sum+=soft;final_n+=1
                elif arm=="S":
                    conf=O.sigmoid(6.*(sim-.5))-.5
                    raw_value_credit=w["S"][0]*conf
                    rank_credit=w["S"][1]*conf
                    nextscore+=raw_value_credit
                    rank+=rank_credit
                elif arm=="U":
                    conf=O.sigmoid(6.*(sim-.5))-.5
                    rank_credit=w["U"][0]*conf+w["U"][1]*(prospect(e,nextrole)-.5)
                    rank+=rank_credit
                cell=(e["to"],tuple(e["dst_bits"]),nextscore)
                proposed.append((nextscore+rank,nextscore-rank,cell,
                      {"prior_score":score,"normal_increment":normal_score_increment,
                       "value_credit":raw_value_credit,"rank_credit":rank_credit,
                       "compatibility":sim,"source_node":node}))
        proposed.sort(key=lambda x:(-x[0],-x[1],x[2][0],x[2][1]))
        active=[x[2] for x in proposed[:7]]
        chosen={id(x) for x in proposed[:7]}
        extras=[x for x in proposed if id(x) not in chosen]
        extras.sort(key=lambda x:(-x[1],-x[0],x[2][0],x[2][1]))
        retained=[x[2] for x in extras[:9]]
        evictions+=max(0,len(proposed)-16)
        need(len(active)<=7 and len(retained)<=9 and
             len(active)+len(retained)<=16,"FIXED_SEVEN_NINE")
        if prefix is not None:
            goal=prefix[i]
            matched=[(j,c) for j,c in enumerate(proposed)
                     if c[2][0]==goal[0] and c[2][1]==goal[1]]
            best=max((c[0] for c in proposed),default=None)
            found=max(matched,key=lambda c:c[1][0]) if matched else None
            selected_score=found[1][2][2] if found else None
            m=found[1][3] if found else None
            hops.append({"hop":i+1,"candidate_count":len(proposed),
             "active_count":len(active),"retained_count":len(retained),
             "evictions":max(0,len(proposed)-16),
             "prefix_candidate_seen":bool(matched),
             "prefix_active":any((x[0],x[1])==goal for x in active),
             "prefix_retained":any((x[0],x[1])==goal for x in retained),
             "prefix_candidate_rank":found[0]+1 if found else None,
             "prefix_accumulated_score":selected_score,
             "prefix_previous_score":m["prior_score"] if m else None,
             "prefix_normal_score_increment":m["normal_increment"] if m else None,
             "prefix_learned_value_credit_this_hop":m["value_credit"] if m else None,
             "prefix_rank_credit_this_hop":m["rank_credit"] if m else None,
             "prefix_public_key_compatibility":m["compatibility"] if m else None,
             "prefix_competitive_priority":found[1][0] if found else None,
             "best_competitive_priority":best,
             "prefix_priority_gap_to_best":(best-found[1][0]
                                            if found else None),
             "best_active_retained_accumulated_score":max(
                 [c[2] for c in active+retained],default=None)})
    terminal=[score for node,_,score in active+retained
              if node==g["target"]]
    best=max(terminal,default=-2.*len(g["roles"]))
    z=4.*(best/max(1,len(g["roles"])-1)-base[6])
    base_logit=z
    readout=0.
    if arm=="R":
        avg=readout_sum/max(1,readout_n)-.5
        end=(final_sum/max(1,final_n)-.5) if final_n else -.5
        # Match exact left-associative operation order of original R.
        contribution1=2.*w["R"][0]*avg
        contribution2=2.*w["R"][1]*end
        z=z+contribution1
        z=z+contribution2
        readout=z-base_logit
    ref,_=V.original_forward(arm,g,w)
    need(z.hex()==ref.hex(),"REFERENCE_MODEL_FLOAT_REPLAY_"+arm)
    return {"margin":z,"margin_hex":z.hex(),
       "prediction":bool(O.sigmoid(z)>=.5),
       "base_logit_before_R_readout":base_logit,
       "R_readout_contribution":readout,
       "final_target_best_accumulated_score":best,
       "final_target_candidates":len(terminal),
       "all_evictions":evictions,"hops":hops,
       "terminal_active":len(active),"terminal_retained":len(retained)}


def evaluate(w,phase):
    result={arm:{"cases":[],"pairs":48,"correct_pairs":0,
                 "false_positives":0,"false_negatives":0,
                 "negative_margins_at_or_above_zero":0,
                 "positive_margins_below_zero":0,
                 "positive_path_absent":0,
                 "per_depth":{str(i):{"pairs":0,"correct":0,
                                      "path_absent":0} for i in (7,8,9)}}
            for arm in ARMS}
    for vec in src.VECTORS:
        for seed in src.COHORTS["Yggdrasil"][phase]:
            p,n=src.build("Yggdrasil",seed,vec,phase)
            need(src.public_routes(p)==1 and src.public_routes(n)==0,
                 "PUBLIC_EXACT_ROUTE_ADMISSION")
            # Compute all authentic model logits and predictions with no
            # access to unique causal reference. Only AFTER this step can
            # evaluator compute and inspect the path, never changing policy.
            blind={arm:(shadow(arm,p,w),shadow(arm,n,w)) for arm in ARMS}
            prefix=V.exact_positive_prefix(p)
            for arm in ARMS:
                pos,neg=blind[arm]
                pos_detail=shadow(arm,p,w,prefix)
                need(pos_detail["margin_hex"]==pos["margin_hex"],
                     "ORACLE_LEAK_MUST_NOT_CHANGE_INFERENCE")
                stages=pos_detail["hops"]
                survived=all(x["prefix_active"] or x["prefix_retained"]
                             for x in stages)
                accurate=pos["prediction"] and not neg["prediction"]
                row=result[arm]
                row["correct_pairs"]+=int(accurate)
                row["false_positives"]+=int(neg["prediction"])
                row["false_negatives"]+=int(not pos["prediction"])
                row["negative_margins_at_or_above_zero"]+=int(neg["margin"]>=0)
                row["positive_margins_below_zero"]+=int(pos["margin"]<0)
                row["positive_path_absent"]+=int(not survived)
                depth=str(len(p["roles"]))
                row["per_depth"][depth]["pairs"]+=1
                row["per_depth"][depth]["correct"]+=int(accurate)
                row["per_depth"][depth]["path_absent"]+=int(not survived)
                row["cases"].append({"seed":seed,"vector":list(vec),
                   "depth":len(p["roles"]),"correct":bool(accurate),
                   "positive_logit":pos["margin"],
                   "negative_logit":neg["margin"],
                   "positive_false_negative":not pos["prediction"],
                   "negative_false_positive":neg["prediction"],
                   "causal_path_survived":survived,
                   "best_target_accumulator":pos["final_target_best_accumulated_score"],
                   "readout_contribution":pos["R_readout_contribution"],
                   "per_hop":stages})
    for arm,row in result.items():
        need(len(row["cases"])==48 and
             all(a["pairs"]==16 for a in row["per_depth"].values()),
             "FULL_DEV_48_PER_DEPTH")
    # Additional per-hop cross-arm drift, always source-matched by seed/vector.
    baseline=result["O"]["cases"]
    for arm,row in result.items():
        perhop={}
        for hop in range(1,10):
            deltas=[]
            for i,case in enumerate(row["cases"]):
                if len(case["per_hop"])<hop:continue
                srcv=case["per_hop"][hop-1]["prefix_accumulated_score"]
                basev=baseline[i]["per_hop"][hop-1]["prefix_accumulated_score"]
                if srcv is not None and basev is not None:deltas.append(srcv-basev)
            perhop[str(hop)]={"comparable":len(deltas),
                "mean_difference_vs_O":sum(deltas)/len(deltas) if deltas else None,
                "min_difference_vs_O":min(deltas) if deltas else None,
                "max_difference_vs_O":max(deltas) if deltas else None}
        row["score_drift_vs_original_O"]=perhop
        row["case_sha256"]=digest(row["cases"])
    return result


def main():
    p=argparse.ArgumentParser()
    for name in ("o","r","s","u"):
        p.add_argument("--original-"+name,required=True)
    p.add_argument("--output",required=True)
    a=p.parse_args()
    frozen()
    w=V.original_weights(a.original_o,a.original_r,a.original_s,a.original_u)
    target=Path(a.output)
    need(target.parent.is_dir() and not target.exists(),"EXCLUSIVE_OUTPUT")
    res={"schema":SCHEMA,"preimplementation_blob":FREEZE_BLOB,
       "original_O_R_S_U_weights_unchanged":True,"new_training_steps":0,
       "development_source_only":True,
       "protected_original_first_use":False,
       "science_accepted":False,"optimizer_promoted":False,
       "accepted_refs_mutated":False,
       "FIT":evaluate(w,"FIT"),"DEV":evaluate(w,"DEV")}
    data=(json.dumps(res,sort_keys=True,indent=2)+"\n").encode()
    target.write_bytes(data)
    print("F124WY_SHA256="+hashlib.sha256(data).hexdigest())
    for arm,row in res["DEV"].items():
        drift=row["score_drift_vs_original_O"]["7"]["mean_difference_vs_O"]
        print("F124WY_DEV_"+arm+":correct="+str(row["correct_pairs"])+
              "/48:causal_path_absent="+str(row["positive_path_absent"])+
              "/48:false_negatives="+str(row["false_negatives"])+
              ":false_positives="+str(row["false_positives"])+
              ":hop7_avg_score_delta_vs_O="+str(drift))


if __name__=="__main__":
    try:main()
    except (ValueError,KeyError,TypeError,ArithmeticError,OSError) as error:
        print("F124WY_QUARANTINED="+str(error),file=sys.stderr)
        sys.exit(1)
