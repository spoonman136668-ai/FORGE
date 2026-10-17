"""F124-H source-pinned, genuine TRAIN-only depth-invariant learner evidence.

Original F123 independently qualified TRAIN vectors only. Exact source/model
Git blobs checked before weight updates. Reserved CONFIRM never constructed.
"""
from __future__ import annotations
import argparse
import json
import math
import os
from pathlib import Path
import re
import sys

import f123_cross_os_custody as upstream
import f124h_source as graph
import f124h_signed_evidence as model

SCHEMA="forge.research.f124h.train-only-signed-competing-evidence.v1"
F123_SHA="12da879272212b899c6b942004ff38dc21ffa6bb20e7a81eac21d691746b474d"
F123_HEAD="7882849a59964f412a87589be653114e7bf64d52"
SOURCE_BLOB="3feab91460f29ec169e1904479a134bb04691937"
MODEL_BLOB="599d7a87f0812f3a7d2c8680861b6360d3640bc0"

def need(value,code):
    graph.require(value,"TRAIN_CUSTODY_"+code)

def blob(module):
    return graph.git_blob(Path(module.__file__).read_bytes().replace(b"\r\n",b"\n"))

def canonical(obj):
    return (json.dumps(obj,sort_keys=True,separators=(",",":"))+"\n").encode()

def fixed_comparator(obs):
    graph.validate(obs)
    frontier=[(obs["start"],None)]
    scans=bitops=0
    for role in obs["roles"]:
        following=[]
        for node,carried in frontier:
            for e in obs["edges"]:
                scans+=1
                if e["from"]!=node or e["role"]!=role:continue
                if carried is not None:
                    bitops+=16
                    if sum(a==b for a,b in zip(carried,e["src_bits"]))<12:continue
                following.append((e["to"],e["dst_bits"]))
                need(len(following)<=128,"CONTROL_TRAVERSAL_BUDGET")
        frontier=following
    return any(n==obs["target"] for n,_ in frontier),{
        "public_edge_scans":scans,"bit_comparisons":bitops}

def control_lane(lane,vectors):
    paired=tp=tn=rawops=scans=0
    for v in vectors:
        for seed in graph.TRAIN[lane]:
            p,n=graph.build(seed,v,lane,"TRAIN")
            yp,pc=fixed_comparator(p)
            yn,nc=fixed_comparator(n)
            paired+=int(yp and not yn);tp+=int(yp);tn+=int(not yn)
            rawops+=pc["bit_comparisons"]+nc["bit_comparisons"]
            scans+=pc["public_edge_scans"]+nc["public_edge_scans"]
    return {"train_pairs":48,"paired_correct":paired,
            "positive_correct":tp,"negative_correct":tn,
            "edge_scans":scans,"raw_bit_comparisons":rawops,
            "exact_symbolic_ceiling_pairs":48,
            "role_only_paired_correct":0}

def evidence(parent_dir,source_sha,run_id):
    need(type(source_sha) is str and re.fullmatch(r"[a-f0-9]{40}",source_sha)
         and type(run_id) is int and run_id>0 and
         (not os.getenv("GITHUB_SHA") or os.getenv("GITHUB_SHA")==source_sha),
         "EXACT_HEAD_IDENTITY")
    freeze=graph.frozen()
    need(blob(graph)==SOURCE_BLOB and blob(model)==MODEL_BLOB
         and model.frozen(),"MODEL_OR_SOURCE_BLOB_DRIFT")
    original,prior_sha=upstream.read_receipt(parent_dir)
    need(prior_sha==F123_SHA and original["source_sha"]==F123_HEAD
         and original["cohorts"]=="TRAIN_ONLY"
         and original["confirmation_inputs_generated"]==0
         and len(original["lanes"])==2,"AUTHENTIC_SOURCE_VECTORS")
    out=[]
    for row in original["lanes"]:
        lane=row["lane"];vectors=row["training_vectors"]
        need(lane in graph.TRAIN and len(vectors)==2
             and len(row["advisory_candidate_source_shas"])==2,
             "LANE_ADVISORY_IDENTITY")
        comparator=control_lane(lane,vectors)
        arms={a:model.train(lane,vectors,a) for a in ("A","B")}
        selected=sorted(("A","B"),key=lambda a:(-arms[a]["paired_correct"],a))[0]
        need(all(arms[a]["phase"]=="TRAIN_ONLY" and
                 arms[a]["epochs"]==100 and arms[a]["pairs"]==48 and
                 arms[a]["trainable_parameters"]==(20 if a=="A" else 21) and
                 arms[a]["update_l2"]>0 and
                 arms[a]["confirmation_generated"]==0 and
                 arms[a]["scientific_first_use"] is False
                 for a in ("A","B")),"TRAINED_MODEL_AUTHORITY")
        out.append({"lane":lane,"vectors":vectors,
                    "candidate_source_shas":row["advisory_candidate_source_shas"],
                    "arms":arms,"control_fixed_12of16":comparator,
                    "selected_arm_train_only":selected,
                    "selected_weight_sha256":arms[selected]["weight_sha256"],
                    "margin_vs_fixed_train_only":round(
                        (arms[selected]["paired_correct"]-comparator["paired_correct"])/48.,9),
                    "development_criterion_met_train_only":
                        (arms[selected]["paired_correct"]-comparator["paired_correct"])/48.>=.05,
                    "resource_matched":False,
                    "confirmation_generated":0})
    need([r["lane"] for r in out]==["Wingless","Yggdrasil"],
         "INDEPENDENT_LANE_IDENTITY")
    return {"schema":SCHEMA,"source_sha":source_sha,"run_id":run_id,
            "frozen_protocol_git_blob":graph.FREEZE_BLOB,
            "frozen_protocol_sha256":freeze,
            "source_git_blob":SOURCE_BLOB,"model_git_blob":MODEL_BLOB,
            "authenticated_candidate_receipt_sha256":prior_sha,
            "phase":"TRAIN_ONLY","lanes":out,
            "protected_confirmation_cases_generated":0,
            "independent_original_first_use":False,
            "scientific_acceptances":0,"accepted_ref_mutations":0,
            "optimizer_promotions":0,"paid_API_calls":0,"Codex_calls":0,
            "new_scheduler":False,"ckb_plane_contact":False,
            "mind_palace_writes":0,"cloudflare_writes":0,
            "resource_matched_superiority_not_proven":True}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--parent-dir",required=True)
    p.add_argument("--source-sha",required=True)
    p.add_argument("--run-id",type=int,required=True)
    p.add_argument("--output",required=True)
    args=p.parse_args()
    path=Path(args.output)
    need(path.parent.is_dir() and not path.exists(),"OUTPUT_OVERWRITE_FORBIDDEN")
    with path.open("xb") as f:f.write(canonical(evidence(args.parent_dir,args.source_sha,args.run_id)))

if __name__=="__main__":
    try:main()
    except (graph.Invalid,upstream.Invalid,KeyError,OSError,ValueError,TypeError) as e:
        print("F124H_TRAIN_CUSTODY=QUARANTINED "+str(e),file=sys.stderr)
        raise SystemExit(1)
