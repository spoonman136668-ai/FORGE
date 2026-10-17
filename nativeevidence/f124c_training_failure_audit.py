"""F124-C immutable TRAIN-only diagnostic: calibration, latent-slot collapse, causal deletion.

READ ONLY. No training, revised weights, CONFIRM generation, optimizer promotion,
or scientific acceptance. Post-hoc oracle use is solely for diagnostic labels.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import copy
import hashlib
import json
import math
from pathlib import Path
import sys

import f123_cross_os_custody as f123_custody
import f124c_reconvergent_graph as graph
import f124c_node_state_models as learner

F124_SOURCE_HEAD = "ba24e1a7f16023d472d29124caf6524ca9499538"
F124_TRAIN_SHA = "7de031ddfa5dd96df0d55581deca3b98c88a6f3090012ad037d1b8be7b9d1fd3"
F123_TRAIN_SHA = "12da879272212b899c6b942004ff38dc21ffa6bb20e7a81eac21d691746b474d"
F124_GRAPH_BLOB = "dbdae03849da6a161f9f3199a5716f55817224bc"
F124_MODEL_BLOB = "76653b7877cbdc092f12a96e4140a38b381bbddf"
SCHEMA = "forge.research.f124c.posthoc-failure-diagnostic.v1"

def require(predicate, code):
    graph.require(predicate, "TRAIN_DIAGNOSTIC_" + code)

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def canonical(obj):
    return (json.dumps(obj, sort_keys=True, separators=(",", ":")) + "\n").encode()

def read_immutable(path, expected):
    raw = Path(path).read_bytes()
    require(sha(raw) == expected, "IMMUTABLE_TRAIN_RECEIPT_SHA_DRIFT")
    return json.loads(raw)

def fixed_12_of_16(obs):
    """Public role-compatible traversal, approximate nonlearned token comparator.

    Enumerates paths only within this CONTROL, never a learned model.
    Bit-comparison counts are explicit, not asserted equivalent to neural MACs.
    """
    graph.validate(obs)
    states = [(obs["start"], None)]
    edges_scanned = bit_comps = 0
    for role in obs["roles"]:
        next_states=[]
        for node, previous in states:
            for e in obs["edges"]:
                edges_scanned += 1
                if e["from"] != node or e["role"] != role:
                    continue
                if previous is not None:
                    bit_comps += 16
                    if sum(1 for a,b in zip(previous, e["src_bits"]) if a == b) < 12:
                        continue
                next_states.append((e["to"], e["dst_bits"]))
                require(len(next_states) <= 128, "CONTROL_TRAVERSAL_BUDGET")
        states = next_states
    found = any(node == obs["target"] for node,_ in states)
    return found, {"public_edge_scans":edges_scanned,
                   "raw_bit_comparisons":bit_comps}

def rank_and_threshold(rows):
    """TRAIN-label-exposed *diagnostic upper bound*, never a deployed threshold."""
    positives=[r["positive_score"] for r in rows]
    negatives=[r["negative_score"] for r in rows]
    values=sorted(set(positives+negatives))
    choices=[0.,.5,1.]
    choices.extend((a+b)/2. for a,b in zip(values,values[1:]))
    best=None
    for threshold in choices:
        paired=sum(pp>=threshold and pn<threshold
                   for pp,pn in zip(positives,negatives))
        tp=sum(pp>=threshold for pp in positives)
        tn=sum(pn<threshold for pn in negatives)
        trial=(paired,tp+tn,-abs(threshold-.5))
        if best is None or trial>best[0]:
            best=(trial,threshold)
    pred=.5
    return {"observed_training_only_oracle_threshold":round(best[1],12),
            "oracle_train_paired_correct":best[0][0],
            "oracle_train_binary_correct":best[0][1],
            "threshold_label_informed_posthoc":True,
            "operational_threshold_unchanged":pred}

def select_reconvergence_edges(obs):
    """Find a role-compatible >=3-incoming join using only public topology."""
    counts=Counter((e["to"],e["role"]) for e in obs["edges"])
    selected={(node,role) for (node,role),n in counts.items()
              if n >= 3 and role in obs["roles"]}
    require(len(selected)==1, "RECONVERGENCE_TOPOLOGY_AMBIGUOUS")
    node,role=next(iter(selected))
    return [idx for idx,e in enumerate(obs["edges"])
            if e["to"]==node and e["role"]==role]

def deletion_ablation(obs, weights, arm, baseline=None):
    """Measure removal effects; separate oracle scoring AFTER frozen inference."""
    base=learner.forward(obs, weights, arm)[0] if baseline is None else baseline
    require(graph.oracle(obs)==1, "CAUSAL_ABLATION_EXPECTS_POSITIVE")
    causal=[]; distractors=[]
    for idx in select_reconvergence_edges(obs):
        mod=copy.deepcopy(obs)
        del mod["edges"][idx]
        truth=graph.oracle(mod)
        require(truth in (0,1), "ABLATION_AMBIGUOUS")
        score=learner.forward(mod, weights, arm)[0]
        item=round(base-score,12)
        (causal if truth==0 else distractors).append(item)
    require(len(causal)==1 and len(distractors)>=2,
            "EXPECTED_ONE_CAUSAL_JOIN_EDGE")
    return {"causal_probability_drop":causal[0],
            "largest_noncausal_probability_drop":max(distractors),
            "causal_exceeds_distractors":causal[0]>max(distractors),
            "causal_drop_positive":causal[0]>0,
            "number_irrelevant_branches":len(distractors)}

def mean(values):
    return round(sum(values)/len(values),12) if values else None

def diagnose_arm(pairs,weights,arm):
    rows=[]; mass_ratios=[]
    for seed,vec_index,pos,neg in pairs:
        pp,_,ps=learner.forward(pos,weights,arm)
        pn,_,ns=learner.forward(neg,weights,arm)
        replay=learner.forward(copy_reversed(pos),weights,arm)[0]
        require(abs(replay-pp) <= 1e-12, "EDGE_ORDER_PREDICTION_DRIFT")
        cost=fixed_12_of_16(pos)
        counter=fixed_12_of_16(neg)
        ablation=deletion_ablation(pos,weights,arm,pp)
        if arm=="B":
            for stat in (ps,ns):
                slots=stat["slot_mass"]
                require(len(slots)==2 and min(slots)>0,
                        "TWO_SLOT_COLLAPSE_ZERO_MASS")
                mass_ratios.append(min(slots)/max(slots))
        rows.append({"seed":seed,"vector_index":vec_index,
                     "hops":len(pos["roles"]),
                     "stratum":("alias","near_collision","parallel")[seed%3],
                     "positive_score":pp,"negative_score":pn,
                     "positive_correct":pp>=.5,
                     "negative_correct":pn<.5,
                     "paired_correct":pp>=.5 and pn<.5,
                     "positive_ranks_above_negative":pp>pn,
                     "both_predicted_positive":pp>=.5 and pn>=.5,
                     "both_predicted_negative":pp<.5 and pn<.5,
                     "positive_neural_counts":ps,
                     "negative_neural_counts":ns,
                     "fixed_heuristic_positive_correct":bool(cost[0]),
                     "fixed_heuristic_negative_correct":not bool(counter[0]),
                     "fixed_heuristic_positive_counts":cost[1],
                     "causal_join_deletion":ablation})
    require(len(rows)==48,"TRAIN_PAIR_COUNT_DRIFT")
    correct=sum(r["paired_correct"] for r in rows)
    cohorts={}
    for field in ("hops","stratum"):
        for value in sorted({r[field] for r in rows}):
            sub=[r for r in rows if r[field]==value]
            cohorts[f"{field}:{value}"]={"pairs":len(sub),
                "paired_correct":sum(r["paired_correct"] for r in sub),
                "both_positive":sum(r["both_predicted_positive"] for r in sub),
                "both_negative":sum(r["both_predicted_negative"] for r in sub),
                "positive_rank_higher":sum(r["positive_ranks_above_negative"] for r in sub)}
    diagnosis={"arm":arm,"pairs":len(rows),"paired_correct":correct,
        "positive_correct":sum(r["positive_correct"] for r in rows),
        "negative_correct":sum(r["negative_correct"] for r in rows),
        "positive_ranks_above_negative":sum(r["positive_ranks_above_negative"] for r in rows),
        "both_predicted_positive":sum(r["both_predicted_positive"] for r in rows),
        "both_predicted_negative":sum(r["both_predicted_negative"] for r in rows),
        "mean_positive_score":mean([r["positive_score"] for r in rows]),
        "mean_negative_score":mean([r["negative_score"] for r in rows]),
        "mean_score_gap":mean([r["positive_score"]-r["negative_score"] for r in rows]),
        "causal_join_removal_reduces_score":sum(r["causal_join_deletion"]["causal_drop_positive"] for r in rows),
        "causal_join_highest_impact":sum(r["causal_join_deletion"]["causal_exceeds_distractors"] for r in rows),
        "mean_causal_join_probability_drop":mean([r["causal_join_deletion"]["causal_probability_drop"] for r in rows]),
        "mean_largest_distractor_drop":mean([r["causal_join_deletion"]["largest_noncausal_probability_drop"] for r in rows]),
        "mean_public_scans":mean([r["positive_neural_counts"]["public_edge_scans"] for r in rows]),
        "mean_gate_sigmoids":mean([r["positive_neural_counts"]["gate_sigmoids"] for r in rows]),
        "mean_bit_mult_adds_proxy":mean([r["positive_neural_counts"]["bit_multiply_adds_proxy"] for r in rows]),
        "mean_peak_node_slots":mean([r["positive_neural_counts"]["peak_state_slots"] for r in rows]),
        "mean_raw_bit_comparisons_fixed":mean([r["fixed_heuristic_positive_counts"]["raw_bit_comparisons"] for r in rows]),
        "fixed_control_paired_correct":sum(r["fixed_heuristic_positive_correct"] and r["fixed_heuristic_negative_correct"] for r in rows),
        "mean_minor_slot_ratio":mean(mass_ratios),
        "strata":cohorts,
        "posthoc_threshold_upper_bound":rank_and_threshold(rows),
        "cases":rows}
    return diagnosis

def copy_reversed(obs):
    x=copy.deepcopy(obs)
    x["edges"].reverse()
    return x

def run(report_path, f123_dir):
    require(graph.frozen() and
            graph.git_blob(Path(graph.__file__).read_bytes().replace(b"\r\n",b"\n")) == F124_GRAPH_BLOB and
            graph.git_blob(Path(learner.__file__).read_bytes().replace(b"\r\n",b"\n")) == F124_MODEL_BLOB,
            "FROZEN_GRAPH_MODEL_BLOB_DRIFT")
    e=read_immutable(report_path,F124_TRAIN_SHA)
    require(e["schema"]=="forge.research.f124c.train-only-learned-node-state-custody.v1"
            and e["phase"]=="TRAIN_ONLY"
            and e["qualifying_source_sha"]==F124_SOURCE_HEAD
            and e["node_model_git_blob"]==F124_MODEL_BLOB
            and e["graph_git_blob"]==F124_GRAPH_BLOB
            and e["f123_reference_receipt_sha256"]==F123_TRAIN_SHA
            and e["protected_confirm_untouched"] is True
            and e["confirmation_examples_generated"]==0
            and e["scientific_first_use"] is False
            and e["scientific_acceptances"]==0
            and e["optimizer_promotions"]==0,
            "TRAIN_CUSTODY_IDENTITY")
    original,originalsha=f123_custody.read_receipt(f123_dir)
    require(originalsha == F123_TRAIN_SHA
            and original["source_sha"]=="7882849a59964f412a87589be653114e7bf64d52",
            "SOURCE_CANDIDATE_IDENTITY")
    bylane={row["lane"]:row["training_vectors"] for row in original["lanes"]}
    require([x["lane"] for x in e["lanes"]]==["Wingless","Yggdrasil"]
            and set(bylane)==set(graph.TRAIN),"LANE_BINDING")
    out=[]
    for lane in e["lanes"]:
        name=lane["lane"]
        vectors=bylane[name]
        require(learner.value_hash(vectors)==lane["arms"]["A"]["training_source_sha256"]
                ==lane["arms"]["B"]["training_source_sha256"]
                and lane["selected_arm"]=="A"
                and lane["selection"]=="TRAIN_ONLY"
                and lane["confirmation_examples_generated"]==0,
                "AUTHENTIC_ADVISORY_VECTOR_OR_SELECTOR")
        pairs=[]
        for i,vec in enumerate(vectors):
            for seed in graph.TRAIN[name]:
                positive,negative=graph.build(seed,vec,name,"TRAIN")
                pairs.append((seed,i,positive,negative))
        arms={}
        for key in ("A","B"):
            evidence=lane["arms"][key]
            weights=evidence["weights"]
            require(learner.value_hash(weights)==evidence["trained_weight_sha256"]
                    and len(weights)==(learner.P_A if key=="A" else learner.P_B)
                    and evidence["epochs"]==100
                    and evidence["train_pairs"]==48
                    and evidence["train_pairs_correct"]==0,
                    "FROZEN_TRAIN_NEGATIVE_AND_WEIGHT_ID")
            metric=diagnose_arm(pairs,weights,key)
            require(metric["paired_correct"]==evidence["train_pairs_correct"]
                    and metric["positive_correct"]==evidence["positive_correct"]
                    and metric["negative_correct"]==evidence["negative_correct"],
                    "TRAIN_SCORE_REPLAY_FAILURE")
            arms[key]=metric
        out.append({"lane":name,"arms":arms,
                    "a_b_prediction_mean_abs_difference":
                        mean([abs(x["positive_score"]-y["positive_score"])
                            for x,y in zip(arms["A"]["cases"],arms["B"]["cases"])]),
                    "frozen_model_selection":"A",
                    "source_vector_sha256":learner.value_hash(vectors)})
    return {"schema":SCHEMA,"f124_source_commit":F124_SOURCE_HEAD,
        "f124_immutable_train_receipt_sha256":F124_TRAIN_SHA,
        "f123_immutable_train_receipt_sha256":F123_TRAIN_SHA,
        "freeze_git_blob":graph.FREEZE_BLOB,
        "trained_models_retrained":False,
        "thresholds_changed":False,
        "selection_changed":False,
        "confirm_inputs_generated":0,
        "first_use_authorized":False,
        "originals_dispatched":0,
        "scientific_accepted":False,
        "optimizer_promotions":0,
        "budget_matched_controls_proven":False,
        "posthoc_threshold_may_not_be_used_for_acceptance":True,
        "lanes":out}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--f124-report",required=True)
    p.add_argument("--f123-ubuntu-dir",required=True)
    p.add_argument("--output",required=True)
    a=p.parse_args()
    dest=Path(a.output)
    require(dest.parent.is_dir() and not dest.exists(),"EXISTING_OUTPUT")
    report=run(a.f124_report,a.f123_ubuntu_dir)
    dest.write_bytes(canonical(report))

if __name__=="__main__":
    try:main()
    except (graph.Quarantined, f123_custody.Invalid, ValueError, TypeError, KeyError, OSError) as exc:
        print("F124C_FROZEN_TRAIN_DIAGNOSTIC=QUARANTINED "+str(exc),file=sys.stderr)
        raise SystemExit(1)
