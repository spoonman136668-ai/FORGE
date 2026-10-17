"""F124-R disjoint TRAIN-only frozen controls, dense comparator and prune audit.

Consumes complete F124-R TRAIN model receipts from the SAME source commit.
No protected CONFIRM seed is constructible; no tuned S2 model changes. This
report is independent diagnostics, not scientific acceptance or cost parity.
"""
from __future__ import annotations
from collections import defaultdict
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sys

import f120_generated_environment as f120
import f123_controls as old_controls
import f123_learned_routing as dense
import f124r_freeze_admission as freeze
import f124r_train_environment as graphs
import f124r_sparse_model as sparse

SCHEMA = "forge.autonomy.f124r.train-controls-resource-pruning.v1"
DENSE_B_GIT_BLOB = "6f90560c331e20967d0b13892668da8060e06cdc"
ROWS_PER_LANE = 128


def need(ok, reason):
    graphs.require(bool(ok), "AUDIT_" + reason)


def sealed_json(path):
    p = Path(path)
    raw = p.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    seal = p.with_suffix(p.suffix + ".sha256")
    need(seal.exists() and
         seal.read_text(encoding="utf-8").strip() == digest + "  " + p.name,
         "INPUT_SHA256_NOT_VALID")
    return json.loads(raw.decode("utf-8-sig")), digest


def fresh_dense_fit(rows):
    """Unmodified F123 dense B forward and fixed 100-epoch optimizer, new TRAIN.

    Do not mutate/import F123's original frozen cohort or fit (96-row gate).
    Only resize the batch divisor to this already frozen 128-row F124-R TRAIN.
    """
    need(len(rows) == ROWS_PER_LANE and
         sum(y for _, y in rows) == 64 and
         dense.EPOCHS == 100 and dense.LIMIT == 768, "DENSE_PROTOCOL")
    weights = [-1.2] + [0.17]*16 + [0.05, 3.0, 0.5]
    original = list(weights)
    for _ in range(dense.EPOCHS):
        gradient = [0.]*20
        for obs, label in rows:
            p, dp = dense.predict_b(obs, weights)
            for k, value in enumerate(dp):
                gradient[k] += (p - label)*value
        for k, value in enumerate(gradient):
            step = max(-1., min(1., value/len(rows)))
            weights[k] = max(-8., min(8., weights[k] - .22*step))
        need(all(math.isfinite(x) for x in weights), "DENSE_NONFINITE")
    moved = sum((a-b)**2 for a,b in zip(original, weights))**.5
    need(moved > .0001, "DENSE_NOT_TRAINED")
    return weights, moved


def query_only_fit(rows):
    """Frozen F123 query topology control, retrained on F124-R TRAIN only."""
    need(len(rows) == ROWS_PER_LANE, "QUERY_SOURCE")
    weights = [0.]*20
    for _ in range(100):
        gradients = [0.]*20
        for graph, label in rows:
            x = old_controls.topology_features(graph)
            p = sparse.sigmoid(sum(a*b for a,b in zip(weights, x)))
            for k in range(20):
                gradients[k] += (p-label)*x[k]
        for k, grad in enumerate(gradients):
            weights[k] = max(-8., min(8., weights[k] -
                         .25*max(-1., min(1., grad/len(rows)))))
    need(all(math.isfinite(x) for x in weights), "QUERY_NONFINITE")
    return weights


def paired(rows, predict):
    yes = no = pairs = 0
    need(len(rows) == ROWS_PER_LANE, "FULL_PAIRED_COHORT")
    for k in range(0,len(rows),2):
        pos,a = rows[k]
        neg,b = rows[k+1]
        need(a == 1 and b == 0, "LABEL_ORDER")
        p, n = bool(predict(pos)), not bool(predict(neg))
        yes += int(p)
        no += int(n)
        pairs += int(p and n)
    return {"pairs":64,"paired_correct":pairs,
            "positive_correct":yes,"negative_correct":no,
            "balanced_accuracy":round((yes+no)/len(rows),8)}


def dense_work(obs, weights):
    """Instrument the unchanged F123 dense graph-propagation semantics.

    Counts every public edge scan by each live state, 16 bit interactions,
    18 raw feature multiply-adds and state allocations. No hidden route
    shortcut and no fixed constant per graph substituted for actual search.
    """
    graphs.validate(obs)
    states = [(obs["start"], None)]
    scans = bitops = multiplies = allocations = 0
    for step,role in enumerate(obs["roles"]):
        next_states = []
        for node,prev in states:
            for edge in obs["edges"]:
                scans += 1
                if edge["from"] != node or edge["role"] != role:
                    continue
                if prev is not None:
                    bitops += 16
                    multiplies += 18
                next_states.append((edge["to"], edge["dst_bits"]))
                allocations += 1
                need(len(next_states) <= 256, "DENSE_STATE_BOUND")
        states = next_states
    # All model outputs are independently checked by dense.predict_b.
    return {"public_edge_visits":scans,
            "attention_bit_interactions":bitops,
            "attention_multiply_adds":multiplies,
            "allocated_states":allocations,
            "index_operations":0, "hashed_edge_bytes":0,
            "sort_comparison_upper":0, "pruned_states":0}


def sparse_work(obs, trace):
    w = trace["work"]
    # Descriptor hashing cost must count bytes, not a zero-cost hash.
    raw_bytes = sum(len(json.dumps(e,sort_keys=True,separators=(",", ":")).encode())
                    for e in obs["edges"])
    return {"public_edge_visits":w["public_edge_visits"],
            "attention_bit_interactions":w["attention_bit_interactions"],
            "attention_multiply_adds":w["attention_multiply_adds"],
            "allocated_states":w["allocated_states"],
            "index_operations":w["index_operations"],
            "hashed_edge_bytes":raw_bytes,
            "sort_comparison_upper":w["sort_comparison_upper"],
            "pruned_states":w["pruned_states"]}


def cost(work):
    """A disclosed unit-event proxy, not wallclock or measured equal FLOPs.

    Hash-byte processing deliberately counts every byte, ensuring sparse
    pre-indexing/hashing is NEVER assigned free compute versus dense scanning.
    Sorting is counted by bounded comparisons. Separately disclose all events.
    """
    return sum(work.values())


def route_witness_hash(path):
    chain = [sparse.edge_id(e) for e in path]
    return hashlib.sha256("|".join(chain).encode()).hexdigest()


def public_exact_paths(obs):
    """Oracle diagnostic AFTER learned inference only; never a model input."""
    graphs.validate(obs)
    states = [(obs["start"], None, ())]
    for role in obs["roles"]:
        candidates=[]
        for node,previous,path in states:
            for e in obs["edges"]:
                if e["from"] != node or e["role"] != role:
                    continue
                if previous is not None and previous != e["src_bits"]:
                    continue
                candidates.append((e["to"],e["dst_bits"],path+(e,)))
                need(len(candidates) <= 256, "ORACLE_DIAGNOSTIC_LIMIT")
        states=candidates
    return [path for node,_,path in states if node==obs["target"]]


def strata(rows, probabilities, controls_predict):
    out = {}
    for k in range(0,len(rows),2):
        pos,_=rows[k]
        hops=len(pos["roles"])
        # Structural stratum only. No orientation or seed index entered model.
        key="depth-"+str(hops)
        if key not in out:
            out[key]={"pairs":0,"s2_paired":0,"control_paired":0}
        metric=out[key]
        metric["pairs"]+=1
        p,n=probabilities[k],probabilities[k+1]
        metric["s2_paired"]+=int(p>=.5 and n<.5)
        metric["control_paired"]+=int(controls_predict(rows[k][0]) and
                                    not controls_predict(rows[k+1][0]))
    return out


def audit_lane(lane, receipt):
    vectors = receipt["source_vectors"]
    need(lane==receipt["lane"] and type(vectors) is list and
         len(vectors)==2 and vectors[0]!=vectors[1] and
         receipt["selected_model"]=="S2" and
         receipt["protected_confirm_generated"] is False and
         receipt["resource_matched_superiority"] is False,
         "SAVED_LANE_AUTHORITY")
    rows = graphs.train_rows(lane,vectors)
    weights = receipt["trained_weights"]
    need(len(weights)==20 and sparse.sha(weights)==receipt["weights_sha256"]
         and sparse.sha(rows)==receipt["train_rows_sha256"] and
         receipt["train_scores"]==sparse.score(rows,weights),
         "SAVED_WEIGHT_OR_SCORE_DRIFT")
    dense_w,movement=fresh_dense_fit(rows)
    query_w=query_only_fit(rows)
    foundation=dense.frozen_f122(lane,vectors)
    controls={
        "CTRL_F123_DENSE_B": paired(rows,lambda o:
                                  dense.predict_b(o,dense_w)[0]>=.5),
        "CTRL_F122_NO_ROUTING": paired(rows,lambda o:
                                  old_controls.f122_no_routing(o,foundation)),
        "CTRL_FIXED_SOFT_PATH": paired(rows,old_controls.fixed_soft_path),
        "CTRL_ROLE_ONLY":paired(rows,lambda o:
                                bool(graphs.symbolic_count(o,True))),
        "CTRL_QUERY_ONLY":paired(rows,lambda o:
                                sparse.sigmoid(sum(w*x for w,x in
                                 zip(query_w,old_controls.topology_features(o))))>=.5),
        "CTRL_EXACT_SYMBOLIC_CEILING":
                              paired(rows,lambda o:bool(graphs.symbolic_count(o)))
    }
    need(controls["CTRL_EXACT_SYMBOLIC_CEILING"]["paired_correct"]==64,
         "SYMBOLIC_AUDIT_FAILED")
    s2_score=receipt["train_scores"]["paired_correct"]
    strong=max(controls[x]["paired_correct"] for x in
               ("CTRL_F122_NO_ROUTING","CTRL_FIXED_SOFT_PATH",
                "CTRL_ROLE_ONLY","CTRL_QUERY_ONLY"))
    totals={"sparse_primitive_event_proxy":0,"dense_primitive_event_proxy":0}
    aggregate={name:{"sparse":0,"dense":0} for name in dense_work(rows[0][0],dense_w)}
    trace=[]
    for i,(obs,label) in enumerate(rows):
        probability,_,info=sparse.forward(obs,weights,trace=True)
        sparse_count=sparse_work(obs,info)
        dense_count=dense_work(obs,dense_w)
        # Same graph used for both predictors; no retuned S2 weights.
        dp=dense.predict_b(obs,dense_w)[0]
        need(math.isfinite(probability) and math.isfinite(dp) and
             info["work"]["retained_max"] <= 2, "MODEL_TRACE_BOUND")
        for name in aggregate:
            aggregate[name]["sparse"]+=sparse_count[name]
            aggregate[name]["dense"]+=dense_count[name]
        totals["sparse_primitive_event_proxy"]+=cost(sparse_count)
        totals["dense_primitive_event_proxy"]+=cost(dense_count)
        oracle=public_exact_paths(obs)
        need(len(oracle)==int(label), "ORACLE_INPUT_LABEL_CONFLICT")
        retained={s["route_sha256"] for s in info["surviving_routes"]
                  if s["hops"]==len(obs["roles"])}
        captured=bool(set(map(route_witness_hash,oracle)) & retained)
        trace.append({"train_graph_index":i,"source_index":i//64,
            "label":label,"hops":len(obs["roles"]),
            "graph_sha256":sparse.sha(obs),
            "sparse_p":round(probability,12),"dense_p":round(dp,12),
            "s2_retained_true_route":captured,
            "retained_state_count":len(info["surviving_routes"]),
            "pruned_states":info["work"]["pruned_states"],
            "sparse_primitive_event_proxy":cost(sparse_count),
            "dense_primitive_event_proxy":cost(dense_count)})
    ratio=totals["sparse_primitive_event_proxy"]/max(1,totals["dense_primitive_event_proxy"])
    control_key=sorted(("CTRL_F122_NO_ROUTING","CTRL_FIXED_SOFT_PATH",
                        "CTRL_ROLE_ONLY","CTRL_QUERY_ONLY"),
                key=lambda k:(-controls[k]["paired_correct"],k))[0]
    depth=strata(rows,[r["sparse_p"] for r in trace],
                 {"CTRL_F122_NO_ROUTING":lambda o:
                    old_controls.f122_no_routing(o,foundation),
                  "CTRL_FIXED_SOFT_PATH":old_controls.fixed_soft_path,
                  "CTRL_ROLE_ONLY":lambda o:bool(graphs.symbolic_count(o,True)),
                  "CTRL_QUERY_ONLY":lambda o:
                    sparse.sigmoid(sum(w*x for w,x in
                    zip(query_w,old_controls.topology_features(o))))>=.5
                 }[control_key])
    return {"lane":lane,"source_vectors_sha256":sparse.sha(vectors),
            "sparse_weights_sha256":sparse.sha(weights),
            "dense_fresh_train_weights_sha256":sparse.sha(dense_w),
            "dense_fresh_train_weight_movement":round(movement,10),
            "query_control_weights_sha256":sparse.sha(query_w),
            "f122_train_foundation_sha256":sparse.sha(foundation),
            "train_pairs":64,"sparse_paired_correct":s2_score,
            "control_paired_scores":controls,
            "strongest_nonoracle_control_name":control_key,
            "strongest_nonoracle_control_paired":strong,
            "sparse_minus_best_nonoracle":round((s2_score-strong)/64,8),
            "margin_at_least_point05_on_train":(s2_score-strong)/64>=.05,
            "noninferior_to_fresh_dense_on_train":
                s2_score>=controls["CTRL_F123_DENSE_B"]["paired_correct"],
            "retained_true_path_on_train_positives":
                sum(r["s2_retained_true_route"] for r in trace if r["label"]==1),
            "positive_train_graphs":64,
            "false_negative_train_positive_count":
                sum(r["sparse_p"]<.5 for r in trace if r["label"]==1),
            "pruned_state_events":sum(r["pruned_states"] for r in trace),
            "feature_work_event_totals":aggregate,
            "costs_are_mixed_primitive_event_proxies_not_runtime":True,
            "cost_proxy_totals":totals,
            "cost_proxy_sparse_over_dense":round(ratio,8),
            "frozen_proxy_ratio_at_most_point75":ratio<=.75,
            "measured_equal_compute_cost_established":False,
            "depth_strata":depth,
            "train_trace_sha256":sparse.sha(trace),
            "trace_rows":trace,
            "protected_confirmation_read":False,
            "scientific_first_use":False}


def audit(advisory, saved, source):
    cfg,_=freeze.frozen()
    need(isinstance(source,str) and
         re.fullmatch(r"[0-9a-f]{40}",source) is not None
         and (not os.environ.get("GITHUB_SHA") or
              os.environ["GITHUB_SHA"]==source)
         and saved.get("source_commit_sha")==source
         and saved.get("advisory_sha256")==sparse.sha(advisory)
         and saved.get("f124r_freeze_git_blob")==freeze.EXPECTED_FREEZE_BLOB
         and saved.get("phase")=="PUBLIC_SYNTHETIC_TRAIN_ONLY"
         and saved.get("protected_confirmation_read") is False
         and saved.get("scientific_acceptance") is False
         and saved.get("optimizer_promotion") is False,
         "SOURCE_OR_CUSTODY")
    # Only on fresh F124-R TRAIN; no previous saved F123 fitting here.
    provenance=f120.validate(advisory,source)
    need(len(saved["lanes"])==2 and
         [r["lane"] for r in saved["lanes"]]==["Wingless","Yggdrasil"],
         "LANE_ORDER")
    from pathlib import Path
    raw=Path(dense.__file__).read_bytes().replace(b"\r\n",b"\n")
    need(f120.blob(raw)==DENSE_B_GIT_BLOB and
         saved["f123_model_git_blob"]==DENSE_B_GIT_BLOB,
         "F123_COMPARATOR_SOURCE_DRIFT")
    for lane,rec in zip(("Wingless","Yggdrasil"),saved["lanes"]):
        entries=provenance[lane]
        need([x["vector"] for x in entries]==rec["source_vectors"]
             and [x["source_candidate_sha256"] for x in entries]==
             rec["source_candidate_sha256"],"ADVISORY_CANDIDATE_DRIFT")
    result=[audit_lane(lane,rec)
            for lane,rec in zip(("Wingless","Yggdrasil"),saved["lanes"])]
    return {"schema":SCHEMA,"source_commit_sha":source,
        "f124r_freeze_git_blob":freeze.EXPECTED_FREEZE_BLOB,
        "lanes":result,
        "frozen_train_margin_met_in_both":all(
            r["margin_at_least_point05_on_train"] for r in result),
        "equal_runtime_or_true_cost_parity_established":False,
        "protected_confirmation_read":False,
        "scientific_first_use":False,
        "scientific_acceptance":False,
        "optimizer_promotion":False,
        "negative_findings_retained":True}


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--advisory",required=True)
    p.add_argument("--train-report",required=True)
    p.add_argument("--source-ref",required=True)
    p.add_argument("--output",required=True)
    a=p.parse_args()
    advisory,_=sealed_json(a.advisory)
    saved,_=sealed_json(a.train_report)
    output=a.output
    result=audit(advisory,saved,a.source_ref)
    dest=Path(output)
    need(dest.parent.is_dir() and not dest.exists(),"MUTABLE_OUTPUT_DENIED")
    b=(json.dumps(result,sort_keys=True,separators=(",",":"))+"\n").encode()
    dest.open("xb").write(b)
    print("F124R_CONTROLS_TRAIN_SHA256="+hashlib.sha256(b).hexdigest())
    for item in result["lanes"]:
        print("F124R_"+item["lane"].upper()+"_S2="+str(item["sparse_paired_correct"])+"/64")
        print("F124R_"+item["lane"].upper()+"_BEST_CONTROL="+
              str(item["strongest_nonoracle_control_paired"])+"/64")
        print("F124R_"+item["lane"].upper()+"_DENSE="+
              str(item["control_paired_scores"]["CTRL_F123_DENSE_B"]["paired_correct"])+"/64")
        print("F124R_"+item["lane"].upper()+"_PRUNE_RETAINED="+
              str(item["retained_true_path_on_train_positives"])+"/64")
        print("F124R_"+item["lane"].upper()+"_COST_PROXY_RATIO="+
              str(item["cost_proxy_sparse_over_dense"]))
    print("F124R_PROTECTED_CONFIRM_READ=false")
    print("F124R_SCIENTIFIC_ACCEPTANCE=false")

if __name__=="__main__":
    try:
        main()
    except (graphs.Invalid,freeze.Invalid,ValueError,KeyError,
            TypeError,IndexError,OSError) as err:
        print("F124R_CONTROLS_TRAIN_QUARANTINED="+str(err),file=sys.stderr)
        raise SystemExit(1)
