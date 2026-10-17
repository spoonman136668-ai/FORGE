"""F124-F source-pinned TRAIN-only query-conditioned retrieval evidence.

Authentication is by the exact F123 Ubuntu prospective-source TRAIN receipt,
frozen Git source blobs, source ref and actual learned model parameter digests.
Reserved CONFIRM source and independent first-use remain inaccessible.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sys
import f123_cross_os_custody as f123
import f124f_public_graph_source as env
import f124f_conditional_memory as learner

SCHEMA="forge.research.f124f.train-only-query-conditioned-custody.v1"
F123_SHA="12da879272212b899c6b942004ff38dc21ffa6bb20e7a81eac21d691746b474d"
F123_HEAD="7882849a59964f412a87589be653114e7bf64d52"
SOURCE_BLOB="1961628bdc9df47975f8c9ccd44370329ed02ae5"
MODEL_BLOB="30b50f9500a7905378b53613280658b1b95c9a29"

def require(cond,code):
    env.require(cond,"TRAIN_CUSTODY_"+code)

def blob(module):
    return env.git_blob(Path(module.__file__).read_bytes().replace(b"\r\n",b"\n"))

def canonical(report):
    return (json.dumps(report,sort_keys=True,separators=(",",":"))+"\n").encode()

def fixed_hamming(obs):
    env.validate(obs)
    states=[(obs["start"],None)]
    bitops=scans=0
    for role in obs["roles"]:
        next_states=[]
        for node,key in states:
            for edge in obs["edges"]:
                scans+=1
                if edge["from"]!=node or edge["role"]!=role:continue
                if key is not None:
                    bitops+=16
                    if sum(a==b for a,b in zip(key,edge["src_bits"]))<12:continue
                next_states.append((edge["to"],edge["dst_bits"]))
                require(len(next_states)<=128,"FIXED_CONTROL_BUDGET")
        states=next_states
    return any(node==obs["target"] for node,_ in states),{
        "public_edge_scans":scans,"raw_bit_comparisons":bitops}

def control_lane(lane,vectors):
    paired=tp=tn=bitops=scans=0
    for vec in vectors:
        for seed in env.TRAIN[lane]:
            p,n=env.build(seed,vec,lane,"TRAIN")
            pos,pw=fixed_hamming(p);neg,nw=fixed_hamming(n)
            paired+=int(pos and not neg);tp+=int(pos);tn+=int(not neg)
            bitops+=pw["raw_bit_comparisons"]+nw["raw_bit_comparisons"]
            scans+=pw["public_edge_scans"]+nw["public_edge_scans"]
    return {"pairs":48,"paired_correct":paired,"positive_correct":tp,
            "negative_correct":tn,"edge_scans":scans,
            "raw_bit_comparisons":bitops,
            "role_only_paired_correct":0,"exact_symbolic_ceiling_pairs":48}

def evidence(reference_dir,source_sha,run_id):
    require(type(source_sha) is str and re.fullmatch("[0-9a-f]{40}",source_sha)
            and type(run_id) is int and run_id>0 and
            (not os.getenv("GITHUB_SHA") or os.environ["GITHUB_SHA"]==source_sha),
            "UNAUTHENTICATED_GITHUB_SOURCE")
    freeze=env.frozen()
    require(blob(env)==SOURCE_BLOB and blob(learner)==MODEL_BLOB
            and learner.contract(),"SOURCE_MODEL_BLOB_DRIFT")
    original,receipt=f123.read_receipt(reference_dir)
    require(receipt==F123_SHA and original["source_sha"]==F123_HEAD
            and original["cohorts"]=="TRAIN_ONLY"
            and original["confirmation_inputs_generated"]==0
            and len(original["lanes"])==2,"ORIGINAL_VECTOR_OR_RECEIPT_DRIFT")
    lanes=[]
    for row in original["lanes"]:
        lane=row["lane"]
        vectors=row["training_vectors"]
        require(lane in env.TRAIN and len(vectors)==2 and
                len(row["advisory_candidate_source_shas"])==2,
                "LANE_ADVISORY_SOURCE_DRIFT")
        controls=control_lane(lane,vectors)
        arms={arm:learner.train(lane,vectors,arm) for arm in ("A","B")}
        selected=sorted(arms,key=lambda arm:(-arms[arm]["train_paired_correct"],arm))[0]
        require(all(arms[a]["phase"]=="TRAIN_ONLY" and
                    arms[a]["training_epochs"]==100 and
                    arms[a]["paired_examples"]==48 and
                    arms[a]["parameters"]==(19 if a=="A" else 20) and
                    arms[a]["update_l2"]>0 and
                    arms[a]["confirmation_examples"]==0 and
                    arms[a]["scientific_first_use"] is False
                    for a in ("A","B")),"NONFINITE_OR_WRONG_TRAIN_REPORT")
        diff=(arms[selected]["train_paired_correct"]-controls["paired_correct"])/48.
        lanes.append({"lane":lane,"training_source_candidate_shas":row["advisory_candidate_source_shas"],
                      "vectors":vectors,"learned_arms":arms,"fixed_raw_match":controls,
                      "selected_train_arm":selected,
                      "selected_weight_sha256":arms[selected]["weight_sha256"],
                      "train_margin_vs_fixed":round(diff,9),
                      "preregistered_both_lane_development_success":diff>=.05,
                      "resource_matched_advantage_not_established":True,
                      "confirm_examples_generated":0})
    require([x["lane"] for x in lanes]==["Wingless","Yggdrasil"],
            "SCIENTIFIC_LANE_ORDER")
    return {"schema":SCHEMA,"source_sha":source_sha,"run_id":run_id,
            "freeze_git_blob":env.FREEZE_BLOB,"freeze_sha256":freeze,
            "graph_git_blob":SOURCE_BLOB,"model_git_blob":MODEL_BLOB,
            "original_candidate_receipt_sha256":receipt,
            "phase":"TRAIN_ONLY","lanes":lanes,
            "confirmation_examples_generated":0,"scientific_first_use":False,
            "scientific_acceptances":0,"accepted_ref_mutations":0,
            "optimizer_promotions":0,"Codex_calls":0,"paid_API_calls":0,
            "ckb_plane_contact":False,"mind_palace_writes":0,
            "cloudflare_writes":0,"new_scheduler":False,
            "equal_resource_superiority_established":False}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--f123-dir",required=True)
    p.add_argument("--source-sha",required=True)
    p.add_argument("--run-id",type=int,required=True)
    p.add_argument("--output",required=True)
    a=p.parse_args()
    output=Path(a.output)
    require(output.parent.is_dir() and not output.exists(),"DUPLICATE_OR_UNKNOWN_OUTPUT")
    report=evidence(a.f123_dir,a.source_sha,a.run_id)
    with output.open("xb") as f:f.write(canonical(report))

if __name__=="__main__":
    try: main()
    except (env.Invalid,f123.Invalid,ValueError,TypeError,KeyError,OSError) as e:
        print("F124F_FROZEN_TRAIN=QUARANTINED "+str(e),file=sys.stderr)
        raise SystemExit(1)
