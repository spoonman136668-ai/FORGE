"""F124-X S: independently source-born causal retention capacity stress.

The true public token-valid positive path is computed only AFTER scoring and
used by the evaluator to inspect candidate competition, not as predictor input.
No new training or cell budget increase. Hard cap 7 active +9 retained.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys

import f124x_source as src
import f124v_yggdrasil_causal_trace as V

ARMS=("O","R","S","U")
SCHEMA="forge.research.f124x.independent-capacity-saturation.v1"


def need(x,k):src.need(x,"SATURATION_"+k)


def evaluate(phase,w):
    out={}
    for arm in ARMS:
        out[arm]={"paired":0,"pairs":0,"negative_false_positive":0,
                  "positive_false_negative":0,"first_path_loss":0,
                  "positive_candidate_pressure_above_16":0,
                  "max_candidates_any_hop":0,
                  "per_depth":{str(n):{"pairs":0,"paired":0,"lost":0,
                                      "over16":0} for n in (7,8,9)},
                  "cases":[]}
    for vec in src.VECTORS:
        for seed in src.COHORTS["YggdrasilStress"][phase]:
            plain_p,plain_n=src.build("YggdrasilStress",seed,vec,phase)
            p,n=src.stress_pair(seed,vec,phase)
            need(src.public_routes(plain_p)==1 and src.public_routes(plain_n)==0
                 and src.paired_admit(p,n),"STRESS_PAIR_CAUSAL_IDENTITY")
            # The public path is observer-only and constructed AFTER original
            # models have already predicted on each independent stressed graph.
            pre={arm:(V.original_forward(arm,p,w)[0],
                      V.original_forward(arm,n,w)[0]) for arm in ARMS}
            path=V.exact_positive_prefix(p)
            depth=str(len(p["roles"]))
            for arm in ARMS:
                pos,neg=pre[arm]
                original_pos=V.trace_model(arm,p,w)
                original_neg=V.trace_model(arm,n,w)
                need(original_pos["logit_hex"]==pos.hex() and
                     original_neg["logit_hex"]==neg.hex(),
                     "ORIGINAL_IDENTICAL_LOGITS")
                detail=V.trace_model(arm,p,w,positive_prefix=path)
                need(detail["logit_hex"]==pos.hex(),"ORACLE_TRACE_LEAK")
                hop=detail["hops"]
                lost=any(x["stage"] in ("pruned","not_generated") for x in hop)
                pressure=max(x["number_candidates"] for x in hop)
                over16=pressure>16
                success=original_pos["prediction"] and not original_neg["prediction"]
                row=out[arm]
                row["pairs"]+=1;row["paired"]+=int(success)
                row["negative_false_positive"]+=int(original_neg["prediction"])
                row["positive_false_negative"]+=int(not original_pos["prediction"])
                row["first_path_loss"]+=int(lost)
                row["positive_candidate_pressure_above_16"]+=int(over16)
                row["max_candidates_any_hop"]=max(row["max_candidates_any_hop"],pressure)
                d=row["per_depth"][depth]
                d["pairs"]+=1;d["paired"]+=int(success)
                d["lost"]+=int(lost);d["over16"]+=int(over16)
                row["cases"].append({"seed":seed,"vector":list(vec),"depth":int(depth),
                   "public_graph_edge_count":len(p["edges"]),
                   "public_graph_node_count":len({p["start"],p["target"]}|{
                      x[k] for x in p["edges"] for k in ("from","to")}),
                   "max_candidates":pressure,"saturated_preselection":over16,
                   "positive_causal_prefix_lost":lost,
                   "first_loss":next((x["hop"] for x in hop if
                         x["stage"] in ("pruned","not_generated")),None),
                   "original_positive_prediction":original_pos["prediction"],
                   "original_negative_prediction":original_neg["prediction"],
                   "per_hop":hop})
    for name,row in out.items():
        need(row["pairs"]==48 and len(row["cases"])==48
             and all(v["pairs"]==16 for v in row["per_depth"].values()),
             "COMPLETE_48_STRESS_DENOMINATOR")
        # Hardness is a property of proposed contenders, not correctness or
        # the presence/absence of memory loss. Never promote weak stress.
        row["saturation_witness_met"]=(
            row["positive_candidate_pressure_above_16"]>0)
        row["case_sha256"]=hashlib.sha256(json.dumps(
            row["cases"],sort_keys=True,separators=(",",":")).encode()).hexdigest()
    return out


def main():
    p=argparse.ArgumentParser()
    for name in ("o","r","s","u"):p.add_argument("--original-"+name,required=True)
    p.add_argument("--output",required=True)
    a=p.parse_args()
    src.frozen()
    w=V.original_weights(a.original_o,a.original_r,a.original_s,a.original_u)
    result={"schema":SCHEMA,"freeze_blob":src.PROTOCOL_BLOB,
       "source_birth":"F124X_Y_CAPACITY_STRESS_NONPROTECTED",
       "no_original_model_or_capacity_changed":True,"new_training_steps":0,
       "FIT":evaluate("FIT",w),"DEV":evaluate("DEV",w),
       "protected_first_use":False,"scientific_acceptances":0,
       "optimizer_promotions":0,"accepted_refs":0}
    out=Path(a.output);need(out.parent.is_dir() and not out.exists(),
                             "EXCLUSIVE_OUTPUT")
    data=(json.dumps(result,sort_keys=True,indent=2)+"\n").encode()
    with out.open("xb") as f:f.write(data)
    print("F124XS_SHA256="+hashlib.sha256(data).hexdigest())
    for arm,row in result["DEV"].items():
        print("F124XS_DEV_"+arm+":paired="+str(row["paired"])+"/48"+
              ":path_lost="+str(row["first_path_loss"])+"/48"+
              ":candidate_over16="+str(row["positive_candidate_pressure_above_16"])+
              "/48:max_candidates="+str(row["max_candidates_any_hop"]))


if __name__=="__main__":
    try:main()
    except (ValueError,OSError,KeyError,TypeError,ArithmeticError) as err:
        print("F124XS_QUARANTINE="+str(err),file=sys.stderr)
        sys.exit(1)
