"""F124-J frozen public-comparator resource audit and sealed-CONFIRM preflight.

Audits only previously authenticated F124-H TRAIN graphs and weights. Fixed
C12/C14/C16 public raw-token traversals use no true-path labels. C16 is an
explicit algorithmic ceiling, NOT a retroactively eligible original heuristic.
Original 7–9-hop confirmation is structurally unavailable in the frozen source;
no reserved input is ever constructed, scored or inspected.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import inspect
import json
from pathlib import Path
import sys

import f123_cross_os_custody as f123
import f124h_source as source
import f124h_signed_evidence as model
import f124i_frozen_mechanism_audit as previous

SCHEMA="forge.research.f124j.public-resource-controls-and-confirmation-preflight.v1"
FREEZE_BLOB="c9131287cd30665f5928a15cab63bb7731eb6a78"
PARENT_SHA="87459f4b493242dec090b5f0f748bf3e2e4d9604"
I_REPORT_SHA="c97f51a04769caeadeee03889daf056cad38be826d18aada453a07371e71fb1e"
H_TRAIN_SHA=previous.F124H_TRAIN_SHA
F123_SHA=previous.F123_TRAIN_SHA
TOLERANCES=(12,14,16)

def need(ok,code):
    source.require(ok,"F124J_"+code)

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def json_bytes(value):
    return (json.dumps(value,sort_keys=True,separators=(",",":"))+"\n").encode()

def freeze():
    raw=Path(__file__).resolve().parents[1].joinpath(
        "reference/research-intake/f124j-resource-and-confirm-readiness-freeze.json"
    ).read_bytes().replace(b"\r\n",b"\n")
    need(source.git_blob(raw)==FREEZE_BLOB,"PROTOCOL_DRIFT")
    x=json.loads(raw)
    need(x["status"]=="PRE_AUDIT_FREEZE" and
         x["schema"]=="forge.research.f124j.frozen-public-control-and-confirmation-readiness.v1" and
         x["identity"]["parent_qualified_audit_head"]==PARENT_SHA and
         x["identity"]["parent_audit_report_sha256"]==I_REPORT_SHA and
         x["protected_confirmation_preflight"]["preflight_expected_result"]==
         "BLOCKED_SOURCE_NOT_IMPLEMENTED" and all(x["authority"].values()),
         "PROTOCOL_AUTHORITY")
    return hashlib.sha256(raw).hexdigest()

def public_fixed_traversal(observation,threshold):
    """Only graph public values; no generated labels or route witness.

    Compare all 16 actual raw bits after public role/node compatibility.
    Counts actual edge checks and 16-bit comparisons, no fake padding.
    """
    source.validate(observation)
    need(type(threshold) is int and threshold in TOLERANCES,"CONTROL_NOT_FROZEN")
    frontier=[(observation["start"],None)]
    scans=bits=compare_count=expanded=0
    for role in observation["roles"]:
        nxt=[]
        for node,carried in frontier:
            for edge in observation["edges"]:
                scans+=1
                if edge["from"]!=node or edge["role"]!=role:continue
                if carried is not None:
                    matched=0
                    for a,b in zip(carried,edge["src_bits"]):
                        bits+=1
                        matched+=int(a==b)
                    compare_count+=1
                    if matched<threshold:continue
                nxt.append((edge["to"],edge["dst_bits"]))
                expanded+=1
                need(len(nxt)<=128,"FIXED_FRONTIER_BOUND")
        frontier=nxt
    return any(node==observation["target"] for node,_ in frontier),{
        "public_edge_scans":scans,
        "actual_raw_bit_comparisons":bits,
        "raw_token_pair_comparisons":compare_count,
        "accepted_public_role_edges":expanded,
        "algorithmic_weights":0,
        "sigmoids":0,"exp_evaluations":0,"raw_bit_multiply_adds":0
    }

def confirm_static_preflight():
    """Intentionally never executes source.build/validate on protected seeds."""
    previous.prove_source()
    code_build=inspect.getsource(source.build)
    code_validate=inspect.getsource(source.validate)
    need('phase=="TRAIN"' in code_build and
         'seed in TRAIN[lane]' in code_build and
         'hops=4+(seed%2)' in code_build and
         'len(g["roles"]) in (4,5)' in code_validate and
         len(source.RESERVED_CONFIRM["Wingless"])==48 and
         len(source.RESERVED_CONFIRM["Yggdrasil"])==48 and
         all(not set(source.TRAIN[l]) & set(source.RESERVED_CONFIRM[l])
             for l in source.TRAIN),
         "FROZEN_SOURCE_BOUNDARY_CHANGED")
    return {
        "reserved_examples_generated":0,
        "original_source_accepts_only_phase":"TRAIN",
        "original_source_hops":[4,5],
        "claimed_reserved_hops":[7,9],
        "source_birth_capability":"BLOCKED_SOURCE_NOT_IMPLEMENTED",
        "independent_first_use_authority_present":False,
        "authentication_capability":"NOT_ESTABLISHED",
        "source_preview_performed":False,
        "next_action":"Implement and freeze independent CONFIRM-only 7-9-hop source and validate only with disjoint nonreserved fixtures. Obtain independent first-use authorization after custody qualification."
    }

def read_i_report(path):
    need(sha(path)==I_REPORT_SHA,"IMMUTABLE_F124I_REPORT_DIGEST")
    x=json.loads(Path(path).read_bytes())
    need(x["schema"]==previous.SCHEMA and
         x["parent_original_source_head"]==previous.F124H_HEAD and
         x["original_train_weights_receipt_sha256"]==H_TRAIN_SHA and
         x["authenticated_candidate_vectors_sha256"]==F123_SHA and
         x["reserved_confirmation_examples_generated"]==0 and
         x["resource_matched_superiority_proven"] is False and
         len(x["lanes"])==2,
         "F124I_PARENT_EVIDENCE")
    return x

def _zero_cost():
    return {"public_edge_scans":0,"actual_raw_bit_comparisons":0,
            "raw_token_pair_comparisons":0,"accepted_public_role_edges":0}

def audit(i_path,h_path,f123_dir):
    freeze()
    prior=read_i_report(i_path)
    parent=previous.read_frozen_parent(h_path)
    previous.prove_source()
    origin,orig_sha=f123.read_receipt(f123_dir)
    need(orig_sha==F123_SHA and origin["source_sha"]==previous.F123_HEAD and
         origin["cohorts"]=="TRAIN_ONLY" and
         origin["confirmation_inputs_generated"]==0 and
         [r["lane"] for r in origin["lanes"]]==["Wingless","Yggdrasil"] and
         [r["lane"] for r in parent["lanes"]]==["Wingless","Yggdrasil"] and
         [r["lane"] for r in prior["lanes"]]==["Wingless","Yggdrasil"],
         "ORIGINAL_TRAIN_SOURCE_CUSTODY")
    lanes=[]
    for birth,hrecord,irecord in zip(origin["lanes"],parent["lanes"],prior["lanes"]):
        lane=birth["lane"]
        vectors=birth["training_vectors"]
        need(lane==hrecord["lane"]==irecord["lane"]
             and vectors==hrecord["vectors"] and len(vectors)==2
             and hrecord["selected_arm_train_only"]=="B"
             and irecord["original_train_selected_arm"]=="B"
             and hrecord["arms"]["B"]["weight_sha256"]==
                 irecord["arms"]["B"]["frozen_weight_sha256"],
             "SELECTED_FROZEN_ARM_B_DRIFT")
        cases=[]
        agg={str(t):{"paired_correct":0,"positive_correct":0,
              "negative_correct":0,"strata":{},"work":_zero_cost()}
              for t in TOLERANCES}
        for vector in vectors:
            for seed in source.TRAIN[lane]:
                p,n=source.build(seed,vector,lane,"TRAIN")
                need(source.paired_admit(p,n) and previous.inventory(p)==previous.inventory(n),
                     "PUBLIC_PAIR_SOURCE_IDENTITY")
                name=source.STRATA[seed%len(source.STRATA)]
                row={"train_seed":seed,"stratum":name,"hops":len(p["roles"])}
                for threshold in TOLERANCES:
                    pos,a=public_fixed_traversal(p,threshold)
                    neg,b=public_fixed_traversal(n,threshold)
                    slot=agg[str(threshold)]
                    slot["paired_correct"]+=int(pos and not neg)
                    slot["positive_correct"]+=int(pos)
                    slot["negative_correct"]+=int(not neg)
                    entry=slot["strata"].setdefault(name,{"pairs":0,"paired":0})
                    entry["pairs"]+=1
                    entry["paired"]+=int(pos and not neg)
                    for field in slot["work"]:
                        slot["work"][field]+=a[field]+b[field]
                    row[str(threshold)]={"positive":pos,"negative":neg,
                                         "paired_correct":bool(pos and not neg)}
                cases.append(row)
        need(len(cases)==48,"TRAIN_SOURCE_COHORT_SIZE")
        c12=agg["12"]
        expected=hrecord["control_fixed_12of16"]
        stored_i=irecord["public_fixed_work_total_both_labels"]
        need(c12["paired_correct"]==expected["paired_correct"] and
             c12["positive_correct"]==expected["positive_correct"] and
             c12["negative_correct"]==expected["negative_correct"] and
             c12["work"]["public_edge_scans"]==expected["edge_scans"]==
                 stored_i["public_edge_scans"] and
             c12["work"]["actual_raw_bit_comparisons"]==
                 expected["raw_bit_comparisons"]==stored_i["raw_bit_comparisons"],
             "EXACT_PUBLISHED_CONTROL_REPLAY")
        b=irecord["arms"]["B"]["public_work_total_both_labels"]
        need(irecord["arms"]["B"]["frozen_original_train_paired_correct"]==
                 hrecord["arms"]["B"]["paired_correct"] and
             b["public_edge_scans"]>0 and b["raw_bit_multiply_adds"]>0,
             "LEARNED_SOURCE_BUDGET")
        c16=agg["16"]
        need(c16["paired_correct"]==48 and
             c16["positive_correct"]==48 and c16["negative_correct"]==48,
             "EXACT_PUBLIC_CONSISTENCY_CEILING")
        need(c12["paired_correct"]<=c16["paired_correct"] and
             agg["14"]["paired_correct"]<=c16["paired_correct"],
             "CONTROL_CEILING_INCONSISTENCY")
        lanes.append({
            "lane":lane,
            "frozen_selected_arm":"B",
            "original_train_selected_B_pairs":hrecord["arms"]["B"]["paired_correct"],
            "original_B_public_work":b,
            "controls":agg,
            "full_public_exact_C16_excluded_from_original_plus_5pct_threshold":True,
            "C16_same_information_as_B":True,
            "primitive_costs_not_equated":True,
            "equal_resource_superiority_established":False,
            "observed_C16_uses_no_more_scans_than_B":
                c16["work"]["public_edge_scans"]<=b["public_edge_scans"],
            "observed_C16_bit_tests_not_equated_with_B_multiply_adds":True,
            "cases":cases
        })
    return {
        "schema":SCHEMA,
        "resource_protocol_git_blob":FREEZE_BLOB,
        "original_f124h_head":previous.F124H_HEAD,
        "original_f124i_head":PARENT_SHA,
        "original_f124i_report_sha256":I_REPORT_SHA,
        "original_f124h_train_sha256":H_TRAIN_SHA,
        "original_source_vectors_sha256":F123_SHA,
        "original_B_weights_unchanged":True,
        "original_0_5_threshold_unchanged":True,
        "no_retraining":True,
        "one_time_confirmation_preflight":confirm_static_preflight(),
        "reserved_confirmation_cases_generated":0,
        "independent_original_first_use":False,
        "accepted_scientific_results":0,
        "accepted_ref_mutations":0,
        "optimizer_promotions":0,
        "resource_matched_superiority_established":False,
        "lanes":lanes
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--f124i-report",required=True)
    p.add_argument("--f124h-report",required=True)
    p.add_argument("--f123-dir",required=True)
    p.add_argument("--output",required=True)
    args=p.parse_args()
    path=Path(args.output)
    need(path.parent.is_dir() and not path.exists(),"REFUSE_REPORT_OVERWRITE")
    with path.open("xb") as stream:
        stream.write(json_bytes(audit(args.f124i_report,args.f124h_report,args.f123_dir)))

if __name__=="__main__":
    try:main()
    except (source.Invalid,f123.Invalid,KeyError,OSError,ValueError,TypeError) as e:
        print("F124J_RESOURCE_OR_FIRST_USE_PREFLIGHT=QUARANTINED "+str(e),file=sys.stderr)
        raise SystemExit(1)
