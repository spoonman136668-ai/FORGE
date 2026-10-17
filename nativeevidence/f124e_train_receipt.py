"""F124-E immutable TRAIN-only associative key-value binding evidence.

Authenticates original F123 prospective-source candidate vectors from a fixed
Ubuntu receipt. Never dispatches original science or generates reserved seeds.
"""
from __future__ import annotations
import argparse
import json
import math
import os
from pathlib import Path
import re
import sys
import f123_cross_os_custody as parent
import f124e_key_value_environment as src
import f124e_learned_associative_memory as model

SCHEMA="forge.research.f124e.train-only-associative-key-value-custody.v1"
ORIGIN_SHA="12da879272212b899c6b942004ff38dc21ffa6bb20e7a81eac21d691746b474d"
F123_HEAD="7882849a59964f412a87589be653114e7bf64d52"
GRAPH_BLOB="a310c8f285b18a73bdce864335153beba4e1ea3d"
MODEL_BLOB="83c55510d329f11c6552c927e80f2435b855a427"

def need(condition,msg):
    src.require(condition,"TRAIN_SOURCE_"+msg)

def code_blob(module):
    return src.git_blob(Path(module.__file__).read_bytes().replace(b"\r\n",b"\n"))

def canonical(v):
    return (json.dumps(v,sort_keys=True,separators=(",",":"))+"\n").encode()

def fixed_approx(graph):
    src.validate(graph)
    states=[(graph["start"],None)]
    edge_scans=bit_comps=0
    for role in graph["roles"]:
        next_states=[]
        for node,key in states:
            for edge in graph["edges"]:
                edge_scans+=1
                if edge["from"]!=node or edge["role"]!=role:
                    continue
                if key is not None:
                    bit_comps+=16
                    if sum(a==b for a,b in zip(key,edge["src_bits"]))<12:continue
                next_states.append((edge["to"],edge["dst_bits"]))
                need(len(next_states)<=128,"CONTROL_BOUND")
        states=next_states
    return any(n==graph["target"] for n,_ in states),{
        "edge_scans":edge_scans,"bit_comparisons":bit_comps}

def cohort_control(lane,vectors):
    pairs=pos_correct=neg_correct=0
    scans=rawcomp=0
    for v in vectors:
        for seed in src.TRAIN[lane]:
            p,n=src.build(seed,v,lane,"TRAIN")
            yes,c1=fixed_approx(p);no,c2=fixed_approx(n)
            pairs+=int(yes and not no)
            pos_correct+=int(yes)
            neg_correct+=int(not no)
            scans+=c1["edge_scans"]+c2["edge_scans"]
            rawcomp+=c1["bit_comparisons"]+c2["bit_comparisons"]
    return {"pairs":48,"paired_correct":pairs,
            "positive_correct":pos_correct,"negative_correct":neg_correct,
            "edge_scans":scans,"raw_bit_comparisons":rawcomp,
            "role_only_paired_correct":0,
            "symbolic_ceiling_pairs":48}

def evidence(f123_source_dir,current_sha,run_id):
    need(type(current_sha) is str and re.fullmatch(r"[a-f0-9]{40}",current_sha)
         and type(run_id) is int and run_id>0
         and (not os.getenv("GITHUB_SHA") or os.getenv("GITHUB_SHA")==current_sha),
         "CURRENT_COMMIT_NOT_AUTHENTICATED")
    fhash=src.frozen()
    need(code_blob(src)==GRAPH_BLOB and code_blob(model)==MODEL_BLOB
         and model.contract(),"GENERATOR_OR_MODEL_DRIFT")
    ref,ref_sha=parent.read_receipt(f123_source_dir)
    need(ref_sha==ORIGIN_SHA and ref["source_sha"]==F123_HEAD
         and ref["cohorts"]=="TRAIN_ONLY" and
         ref["confirmation_inputs_generated"]==0 and len(ref["lanes"])==2,
         "ORIGINAL_SOURCE_VECTOR_CUSTODY")
    out=[]
    for row in ref["lanes"]:
        lane=row["lane"]
        vectors=row["training_vectors"]
        need(lane in src.TRAIN and len(vectors)==2
             and len(row["advisory_candidate_source_shas"])==2,
             "TRAIN_VECTOR_COHORT_INVALID")
        control=cohort_control(lane,vectors)
        learned={arm:model.train(lane,vectors,arm) for arm in ("A","B")}
        selected=sorted(learned,key=lambda arm:(-learned[arm]["train_paired_correct"],arm))[0]
        need(all(learned[arm]["parameter_count"] in (132,156)
                 and learned[arm]["epochs"]==100
                 and learned[arm]["train_pairs"]==48
                 and learned[arm]["training_displacement_l2"]>0
                 and learned[arm]["confirm_generated"]==0
                 and learned[arm]["first_use"] is False
                 and learned[arm]["science_accepted"] is False for arm in ("A","B")),
                 "UNQUALIFIED_TRAIN_UPDATE")
        margin=(learned[selected]["train_paired_correct"]-control["paired_correct"])/48
        out.append({"lane":lane,"source_candidate_shas":row["advisory_candidate_source_shas"],
                    "train_vectors":vectors,"model_arms":learned,
                    "frozen_selector_arm":selected,
                    "frozen_weight_sha256":learned[selected]["trained_weight_sha256"],
                    "control_fixed_12_of_16":control,"train_margin_vs_control":round(margin,9),
                    "training_success_threshold_met":margin>=.05,
                    "resource_matched":False,
                    "confirmation_generated":0})
    need([x["lane"] for x in out]==["Wingless","Yggdrasil"],
         "LANE_ORDER_DRIFT")
    return {"schema":SCHEMA,"phase":"TRAIN_ONLY",
            "source_sha":current_sha,"run_id":run_id,
            "freeze_git_blob":src.FREEZE_BLOB,"freeze_sha256":fhash,
            "generator_git_blob":GRAPH_BLOB,"model_git_blob":MODEL_BLOB,
            "original_candidate_source_sha256":ref_sha,"lanes":out,
            "scientific_first_use":False,"scientific_acceptances":0,
            "confirmation_cases_generated":0,"accepted_ref_mutations":0,
            "optimizer_promotions":0,"Codex_calls":0,"paid_model_calls":0,
            "ckb_plane_contact":False,"mind_palace_writes":0,
            "new_scheduler":False,"cloudflare_writes":0,
            "resource_matched_superiority_established":False}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--f123-receipt-dir",required=True)
    p.add_argument("--source-sha",required=True)
    p.add_argument("--run-id",required=True,type=int)
    p.add_argument("--output",required=True)
    a=p.parse_args()
    file=Path(a.output)
    need(file.parent.is_dir() and not file.exists(),"OUTPUT_OVERWRITE_FORBIDDEN")
    with file.open("xb") as stream:
        stream.write(canonical(evidence(a.f123_receipt_dir,a.source_sha,a.run_id)))

if __name__=="__main__":
    try:main()
    except (src.Invalid,parent.Invalid,ValueError,TypeError,KeyError,OSError) as e:
        print("F124E_TRAIN_CUSTODY=QUARANTINED "+str(e),file=sys.stderr)
        raise SystemExit(1)
