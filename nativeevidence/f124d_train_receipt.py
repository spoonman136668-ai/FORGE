"""F124-D source-pinned original TRAIN-only learned mechanism and control receipt.

Runs two independent lanes, two genuinely learned competitive arms, frozen
100-epoch paired objective. No read path for RESERVED_CONFIRM, no first-use,
controller dispatch, accepted refs, Codex or paid inference.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys

import f123_cross_os_custody as f123
import f124d_reconvergent_source as source
import f124d_competitive_states as learner

SCHEMA="forge.research.f124d.train-only-competitive-state-evidence.v1"
F123_TRAIN_SHA="12da879272212b899c6b942004ff38dc21ffa6bb20e7a81eac21d691746b474d"
F123_SOURCE_HEAD="7882849a59964f412a87589be653114e7bf64d52"
GRAPH_BLOB="d3023d94c891a70bfa1d027d2b87d26275903e58"
MODEL_BLOB="04677202c75e29a29c75bc3a9e71688aecfaa12d"

def need(ok,code):
    source.require(ok,"TRAIN_CUSTODY_"+code)

def canonical(value):
    return (json.dumps(value,sort_keys=True,separators=(",",":"))+"\n").encode()

def source_blob(path):
    return source.git_blob(Path(path).read_bytes().replace(b"\r\n",b"\n"))

def fixed_control(graph):
    """Nonlearned approximate Hamming public graph traversal, not symbolic oracle."""
    source.validate(graph)
    states=[(graph["start"],None)]
    bit_comps=scans=0
    for role in graph["roles"]:
        next_states=[]
        for node,value in states:
            for edge in graph["edges"]:
                scans+=1
                if edge["from"]!=node or edge["role"]!=role:
                    continue
                if value is not None:
                    bit_comps+=16
                    if sum(a==b for a,b in zip(value,edge["src_bits"]))<12:
                        continue
                next_states.append((edge["to"],edge["dst_bits"]))
                need(len(next_states)<=128,"FIXED_CONTROL_TRAVERSAL_BUDGET")
        states=next_states
    return any(n==graph["target"] for n,_ in states), {
        "public_edge_scans":scans,"raw_bit_comparisons":bit_comps}

def comparator_cohort(lane,vectors):
    pairs=positive=negative=0
    scan=bits=0
    for v in vectors:
        for seed in source.TRAIN[lane]:
            p,n=source.build(seed,v,lane,"TRAIN")
            good_pos,cp=fixed_control(p); good_neg,cn=fixed_control(n)
            positive+=int(good_pos)
            negative+=int(not good_neg)
            pairs+=int(good_pos and not good_neg)
            scan+=cp["public_edge_scans"]+cn["public_edge_scans"]
            bits+=cp["raw_bit_comparisons"]+cn["raw_bit_comparisons"]
    return {"pairs":48,"paired_correct":pairs,"positive_correct":positive,
            "negative_correct":negative,"public_edge_scans":scan,
            "raw_bit_comparisons":bits,
            "exact_symbolic_ceiling_pairs":48,
            "role_only_pairs_correct":0}

def evidence(reference_dir,current_source,run_id):
    need(type(current_source) is str and re.fullmatch("[0-9a-f]{40}",current_source)
         and type(run_id) is int and run_id>0
         and (not os.getenv("GITHUB_SHA") or os.getenv("GITHUB_SHA")==current_source),
         "CURRENT_SOURCE_IDENTITY")
    freeze=source.frozen()
    need(source_blob(source.__file__)==GRAPH_BLOB and
         source_blob(learner.__file__)==MODEL_BLOB and learner.contract(),
         "PINNED_NEW_MECHANISM_DRIFT")
    source_receipt,sha=f123.read_receipt(reference_dir)
    need(sha==F123_TRAIN_SHA and source_receipt["source_sha"]==F123_SOURCE_HEAD
         and source_receipt["cohorts"]=="TRAIN_ONLY"
         and source_receipt["confirmation_inputs_generated"]==0
         and len(source_receipt["lanes"])==2,
         "AUTHENTIC_TRAIN_VECTOR_SOURCE")
    out=[]
    for row in source_receipt["lanes"]:
        lane=row["lane"]
        need(lane in source.TRAIN and
             len(row["training_vectors"])==2 and
             len(row["advisory_candidate_source_shas"])==2,
             "LANE_VECTOR_IDENTITY")
        vectors=row["training_vectors"]
        control=comparator_cohort(lane,vectors)
        arms={a:learner.train(lane,vectors,a) for a in ("A","B")}
        selected=sorted(arms,key=lambda a:(-arms[a]["train_paired_correct"],a))[0]
        need(all(arms[a]["train_pairs"]==48 and
                 arms[a]["training_epochs"]==100 and
                 arms[a]["parameters"]<=768 and
                 arms[a]["updates_l2"]>0 and
                 arms[a]["confirm_generated"]==0 and
                 arms[a]["scientific_acceptances"]==0 for a in ("A","B")),
                 "UNQUALIFIED_LEARNER_UPDATE")
        out.append({"lane":lane,"source_candidate_shas":row["advisory_candidate_source_shas"],
                    "train_vectors":vectors,"control_fixed_12of16":control,
                    "selected_train_arm":selected,
                    "selected_weights_sha256":arms[selected]["weight_sha256"],
                    "arms":arms,
                    "margin_vs_fixed_train_only":round(
                        (arms[selected]["train_paired_correct"]-control["paired_correct"])/48,9),
                    "stronger_than_frozen_threshold_train_only":
                        (arms[selected]["train_paired_correct"]-control["paired_correct"])/48>=.05,
                    "confirmation_graphs_opened":0})
    need([x["lane"] for x in out]==["Wingless","Yggdrasil"],
         "INDEPENDENT_LANE_ORDER")
    return {"schema":SCHEMA,"phase":"TRAIN_ONLY",
            "current_source_sha":current_source,"run_id":run_id,
            "freeze_git_blob":source.FREEZE_BLOB,
            "freeze_sha256":freeze,
            "graph_source_git_blob":GRAPH_BLOB,
            "model_source_git_blob":MODEL_BLOB,
            "authenticated_vector_receipt_sha256":sha,
            "lanes":out,"confirmation_cases_generated":0,
            "independent_scientific_first_use":False,
            "scientific_acceptances":0,"accepted_ref_mutations":0,
            "optimizer_promotions":0,"Codex_calls":0,"paid_API_calls":0,
            "new_scheduler":False,"ckb_plane_contact":False,
            "cloudflare_writes":0,"mind_palace_writes":0,
            "resource_matched_superiority_established":False}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--f123-reference-dir",required=True)
    parser.add_argument("--current-source-sha",required=True)
    parser.add_argument("--run-id",required=True,type=int)
    parser.add_argument("--output",required=True)
    arg=parser.parse_args()
    target=Path(arg.output)
    need(target.parent.is_dir() and not target.exists(),"REFUSE_OUTPUT_OVERWRITE")
    report=evidence(arg.f123_reference_dir,arg.current_source_sha,arg.run_id)
    with target.open("xb") as handle:handle.write(canonical(report))

if __name__=="__main__":
    try:main()
    except (source.Invalid, f123.Invalid, ValueError,TypeError,KeyError,OSError) as err:
        print("F124D_SCIENTIFIC_TRAIN_RECEIPT=QUARANTINED "+str(err),file=sys.stderr)
        raise SystemExit(1)
