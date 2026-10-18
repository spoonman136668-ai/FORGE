"""F124-BA source-blind public-CHECK and key-identifiability rejection.

No graph labels, source names, oracle truth, or source-side operators enter.
The joint affine branch is never altered. New confidence gates ONLY the Feistel
branch, based on public FIT key separation and eight independent public CHECK
rows. Additional 256-key FIT scan costs are explicitly reported.
"""
from __future__ import annotations
import f124az_joint_public_inverse as original
import f124ay_learned_composition as feistel
import f124q_fresh_source as q

CONFIGS=(
 ("balanced_basis48",112,12,0),
 ("balanced_basis48",120,14,0),
 ("balanced_basis48",112,12,8),
 ("random48",112,12,0),
 ("random48",120,14,0),
 ("random48",112,12,8))
FIT=40
TOTAL=48
def need(ok,why):q.need(ok,"F124BA_CONFIDENCE_"+why)
def check_rows(model,demos):
    need(len(demos)==TOTAL,"UNMODIFIED_PUBLIC_48")
    return [sum(a==b for a,b in zip(
        feistel.predict(model,d["output_bits"]),d["input_bits"]))
        for d in demos[FIT:]]

def public_fit_gap(demos,model):
    """Top vs runner-up FIT error across all 256 PUBLIC parameter hypotheses."""
    need(len(demos)==TOTAL and model["mode"]=="learned_two_round_keyed",
         "PUBLIC_40_ONLY")
    fit=demos[:FIT]
    ranked=[]
    for key in range(256):
        wrong=sum((feistel.int16(feistel.forward_bits(d["input_bits"],key))^
                   feistel.int16(d["output_bits"])).bit_count()
                  for d in fit)
        ranked.append((wrong,key))
    ranked.sort()
    need(ranked[0][1]==model["learned_key"] and
         ranked[0][0]==model["public_FIT_bit_errors"],
         "EXACT_PARENT_256_KEY_MODEL_REPLAY")
    return ranked[1][0]-ranked[0][0],ranked[0][0],ranked[1][0]

def gate_public_feistel(model,demos,minimum_total,minimum_each,gap_min):
    need((minimum_total,minimum_each,gap_min) in
         {(a,b,c) for _,a,b,c in CONFIGS},"ONLY_FROZEN_GRID")
    scores=check_rows(model,demos)
    gap,best,runner=public_fit_gap(demos,model)
    agree=sum(scores)
    allowed=(agree>=minimum_total and min(scores)>=minimum_each
             and gap>=gap_min)
    return allowed,{"public_CHECK_total":agree,"public_CHECK_each":scores,
         "min_CHECK_each":min(scores),"sourceblind_FIT_runnerup_gap":gap,
         "FIT_best_errors":best,"FIT_runnerup_errors":runner,
         "feistel_public_rejection":not allowed,
         "extra_key_search_candidates":256,
         "extra_key_fit_observation_evaluations":256*FIT,
         "operator_name_seen":False,"graph_label_seen":False,
         "oracle_key_used":False}

def train(demos,nonce,query,total,each,gap):
    need((query,total,each,gap) in CONFIGS and
         len(demos)==TOTAL and type(nonce) is str and nonce,
         "ONLY_PRECOMMITTED_PUBLIC_POLICY")
    base=original.train(demos,nonce,0)
    choice=base["choice"]
    need(choice in ("affine","feistel","abstain"),"ORIGINAL_ROUTE_ONLY")
    meta={"choice_before":choice,"choice_after":choice,
          "feistel_public_rejection":False,
          "public_CHECK_total":base["feistel_check"],
          "public_CHECK_each":None,
          "sourceblind_FIT_runnerup_gap":None,
          "extra_key_search_candidates":0,
          "extra_key_fit_observation_evaluations":0,
          "new_confidence_bits_lower":0,
          "affine_route_untouched":choice=="affine",
          "query":query,"thresholds":[total,each,gap]}
    if choice=="feistel":
        passed,confidence=gate_public_feistel(
            base["feistel_model"],demos,total,each,gap)
        meta.update(confidence)
        if not passed:base["choice"]="abstain"
        meta["choice_after"]=base["choice"]
        meta["new_confidence_bits_lower"]=32
    need(not(choice=="affine" and base["choice"]!="affine"),
         "AFFINE_POSITIVE_ROUTE_CANNOT_BE_REJECTED_BY_NEW_CONFIDENCE")
    base["f124ba_confidence"]=meta
    base["fit_operations_lower"]+=meta["extra_key_fit_observation_evaluations"]*2
    base["extra_task_model_bits_lower"]+=meta["new_confidence_bits_lower"]
    return base

def score(graph,base,delta,model,demos):
    need("f124ba_confidence" in model
         and model["f124ba_confidence"]["choice_after"]==model["choice"],
         "IMMUTABLE_PUBLIC_DECISION")
    return original.score(graph,base,delta,model,demos)
