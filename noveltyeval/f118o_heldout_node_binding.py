"""F118-O frozen real MetaQA intermediate-node binding on unseen node identities.

Two independently valid original source edges form a 2-hop path IFF the
end of edge one is exactly the start of edge two. Offline evaluator observes
original edges and names; TRAINABLE 9-param model sees only 8 hash-byte equality
flags and train-only labels. This is deliberately NOT learned graph traversal.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
import stat
import sys

import f116o_learned_composition as original

SCHEMA="forge.optimizer.f118o.original-metaqa-node-disjoint-binding.v1"
STATUS="PUBLIC_METAQA_HELDOUT_NODE_IDENTITY_COMPARATOR_ENGINEERING_ONLY"
N_TRAIN=512
N_DEV=128
N_TEST=256
EPOCHS=160
LR=0.35
L2=0.005
D=8

class Denied(Exception): pass

def need(ok,reason):
    if not ok:raise Denied("F118O_GRAPH_BINDING_DENIED_"+reason)

def fingerprint(value:str)->bytes:
    return hashlib.sha256(value.encode("utf-8","strict")).digest()

def partition_node(node:str)->int:
    return int.from_bytes(fingerprint(node)[:8],"big")%10

def partition_label(node:str)->str:
    b=partition_node(node)
    return "train" if b<7 else ("dev" if b==7 else "test")

def sort_key(node:str):
    return fingerprint(node),node.encode("utf-8","strict")

def source_edges(triples):
    # Second-stage EXPLICITLY DIRECTED and source-authentic arcs. An arc
    # carries its complete original physical triple for independent validation.
    # Prevent trivial backtracking over the same original physical fact.
    incoming_all=defaultdict(list)
    outgoing_all=defaultdict(list)
    physical=set(triples)
    for a,r,b in triples:
        if a==b:continue
        fact=(a,r,b)
        arcs=((a,r,"F",b,fact),(b,r,"R",a,fact))
        for arc in arcs:
            outgoing_all[arc[0]].append(arc)
            incoming_all[arc[3]].append(arc)
    incoming={}
    outgoing={}
    for middle in incoming_all.keys() & outgoing_all.keys():
        source_in=min(incoming_all[middle])
        source_out=next((a for a in sorted(outgoing_all[middle])
                         if a[4]!=source_in[4]),None)
        if source_out is None:continue
        incoming[middle]=source_in
        outgoing[middle]=source_out
    eligible=sorted(incoming.keys(),key=sort_key)
    return incoming,outgoing,physical,eligible

def frozen_candidates(eligible):
    buckets={k:[] for k in ("train","dev","test")}
    for node in eligible:
        buckets[partition_label(node)].append(node)
    sizes={"train":N_TRAIN,"dev":N_DEV,"test":N_TEST}
    selected={}
    for key,count in sizes.items():
        need(len(buckets[key])>=count,"INSUFFICIENT_ORIGINAL_SOURCE_BINDING_NODES")
        selected[key]=buckets[key][:count]
    # The negative node may be any eligible source node in the SAME split and
    # first digest nibble bucket; frozen deterministic next-cyclic source order.
    lookup={}
    for section,nodes in buckets.items():
        groups=defaultdict(list)
        for node in nodes:
            groups[fingerprint(node)[0]>>4].append(node)
        for group in groups.values():
            for index,node in enumerate(group):
                if len(group)>1:
                    lookup[node]=group[(index+1)%len(group)]
    for section,nodes in selected.items():
        need(all(node in lookup and node!=lookup[node] for node in nodes),
             "SAME_NIBBLE_NEGATIVE_NOT_AVAILABLE")
        need(all(partition_label(lookup[node])==section for node in nodes),
             "NEGATIVE_NODE_CROSSED_PROTECTED_SPLIT")
    sets={section:set(nodes) for section,nodes in selected.items()}
    need(not(sets["train"] & sets["dev"]) and
         not(sets["train"] & sets["test"]) and
         not(sets["dev"] & sets["test"]),"CROSS_SPLIT_IDENTITY_CONTAMINATION")
    return selected,lookup,{k:len(v) for k,v in buckets.items()}

def features(a:str,b:str)->tuple[int,...]:
    left,right=fingerprint(a)[:D],fingerprint(b)[:D]
    return tuple(int(x==y) for x,y in zip(left,right))

def make_examples(triples):
    incoming,outgoing,source_set,eligible=source_edges(triples)
    chosen,negative,candidate_counts=frozen_candidates(eligible)
    result={}
    raw_provenance_counts={}
    for section,nodes in chosen.items():
        pairs=[]
        seen=set()
        for mid in nodes:
            other=negative[mid]
            # Both candidate edges are authentic; the intermediate-node join
            # is an explicit equality constraint at their shared boundary.
            before=incoming[mid]
            positive_after=outgoing[mid]
            negative_after=outgoing[other]
            need(before[4] in source_set and positive_after[4] in source_set and
                 negative_after[4] in source_set,
                 "SOURCE_PHYSICAL_ORIGINAL_TRIPLES_NOT_VERIFIED")
            need(before[3]==positive_after[0] and
                 before[3]!=negative_after[0] and
                 before[4]!=positive_after[4],
                 "SOURCE_JOIN_LABEL_OR_ORIGINAL_EDGE_REUSE")
            need((fingerprint(mid)[0]>>4)==(fingerprint(other)[0]>>4),
                 "HARD_NEGATIVE_PREFIX_NIBBLE_DRIFT")
            need(fingerprint(mid)[:D]!=fingerprint(other)[:D],
                 "LOSSY_HASH_COLLISION_DISALLOWED")
            need(mid not in seen,"SOURCE_MIDDLE_ID_REUSED")
            seen.add(mid)
            pairs.append((mid,mid,1))
            pairs.append((mid,other,0))
        result[section]=pairs
        raw_provenance_counts[section]=len(nodes)*2
    return result,chosen,candidate_counts,raw_provenance_counts

class LearnedJoinComparator:
    def __init__(self):
        self.w=[0.0]*D
        self.bias=0.0

    def score(self,x):
        return original.sigmoid(self.bias+sum(w*v for w,v in zip(self.w,x)))

    def logloss(self,training):
        need(bool(training),"EMPTY_TRAINING")
        total=0.0
        for x,y in training:
            prob=self.score(x)
            total-=y*math.log(max(prob,1e-12))+(1-y)*math.log(max(1-prob,1e-12))
        return total/len(training)

    def train(self,training):
        first=self.logloss(training)
        n=len(training)
        for epoch in range(EPOCHS):
            gw=[0.0]*D
            gb=0.0
            for x,y in training:
                residual=self.score(x)-y
                gb+=residual
                for d in range(D):
                    gw[d]+=residual*x[d]
            self.bias-=LR*gb/n
            for d in range(D):
                self.w[d]-=LR*(gw[d]/n+L2*self.w[d])
        final=self.logloss(training)
        movement=math.sqrt(sum(z*z for z in self.w)+self.bias*self.bias)
        need(movement>1e-9 and final<first,
             "TRAINING_DID_NOT_CHANGE_AND_REDUCE_LOSS")
        param=",".join(f"{v:.8f}" for v in ([self.bias]+self.w))
        return {
            "training_epochs":EPOCHS,"learned_parameters":D+1,
            "training_logloss_initial":round(first,8),
            "training_logloss_final":round(final,8),
            "learned_parameter_movement_l2":round(movement,8),
            "learned_parameter_sha256":hashlib.sha256(param.encode("ascii")).hexdigest(),
            "training_samples":n,
        }

def metrics(rows,prediction):
    y=[int(value) for _,_,value in rows]
    yp=[int(prediction(a,b)) for a,b,_ in rows]
    return original.performance(y,yp)

def analyze(triples):
    examples,selected,candidate_counts,provenance=make_examples(triples)
    train=[(features(a,b),int(y)) for a,b,y in examples["train"]]
    learner=LearnedJoinComparator()
    trained=learner.train(train)
    # Fixed train-majority constant, tie => 0 by preregistration.
    majority=int(sum(y for _,y in train)>len(train)/2)
    methods={
        "learned_hash_byte_comparator":lambda a,b:learner.score(features(a,b))>=0.5,
        "train_majority":lambda a,b:majority,
        "first_hash_nibble_equal":lambda a,b:(fingerprint(a)[0]>>4)==(fingerprint(b)[0]>>4),
        "fixed_eight_hash_bytes_equal":lambda a,b:fingerprint(a)[:D]==fingerprint(b)[:D],
        "exact_symbolic_node_identity_oracle":lambda a,b:a==b,
    }
    measured={section:{method:metrics(rows,predict)
                       for method,predict in methods.items()}
              for section,rows in examples.items() if section in ("dev","test")}
    require(all(x["n"]==2*len(selected[section])
                for section in measured for x in measured[section].values()),
            "TERMINAL_DENOMINATOR")
    test=measured["test"]
    learned=test["learned_hash_byte_comparator"]
    fixed=test["first_hash_nibble_equal"]
    symbolic=test["exact_symbolic_node_identity_oracle"]
    need(symbolic["tp"]==N_TEST and symbolic["tn"]==N_TEST and
         symbolic["balanced_accuracy"]==1.0,
         "EXACT_IDENTITY_UPPER_BOUND_NOT_PERFECT")
    gain=(learned["both_classes_present"] and
          learned["balanced_accuracy"]>=0.9 and
          learned["balanced_accuracy"]>=fixed["balanced_accuracy"]-0.1)
    return {
        "split_eligible_source_middle_nodes":candidate_counts,
        "node_disjoint_train_middle_ids":len(selected["train"]),
        "node_disjoint_dev_middle_ids":len(selected["dev"]),
        "node_disjoint_terminal_middle_ids":len(selected["test"]),
        "train_edge_pair_examples":provenance["train"],
        "dev_edge_pair_examples":provenance["dev"],
        "terminal_edge_pair_examples":provenance["test"],
        "authentic_original_source_triple_provenance_verified":True,
        "negative_edges_are_real_but_middle_entities_differ":True,
        "explicit_original_forward_reverse_arcs_used":True,
        "original_physical_edge_reuse_in_positive_denied":True,
        "original_forward_only_cohort_underpopulated":True,
        "train_dev_test_candidate_middle_ids_disjoint":True,
        "negative_hash_prefix_nibble_matched":True,
        "no_eight_byte_hash_collision_in_selected_negatives":True,
        "training":trained,
        "dev_inspection_only":measured["dev"],
        "terminal_heldout":measured["test"],
        "engineering_exploratory_disposition":(
            "LEARNED_HASH_EQUALITY_TRANSFER_DEMONSTRATED"
            if gain else "LEARNED_HASH_EQUALITY_TRANSFER_NOT_DEMONSTRATED"),
        "exact_symbolic_node_equality_is_perfect_by_construction":True,
        "hash_equality_features_encode_label_not_graph_semantics":True,
        "learned_query_traversal_qualified":False,
        "genuine_model_variable_binding_qualified":False,
        "developer_or_test_optimizes_model":False,
    }

def audit(raw):
    need(original.source_digest(raw),"ORIGINAL_GIT_BLOB_AND_SHA256_SOURCE")
    triples,roles=original.load_original_triples(raw)
    result=analyze(triples)
    return {
        "schema":SCHEMA,"status":STATUS,
        "evaluation_stage":"F118O_SECOND_STAGE_BIDIRECTIONAL_DEVELOPMENT_DIAGNOSTIC",
        "source_repository":"tiantiangao7/kalm-qa",
        "source_commit":original.UPSTREAM,
        "source_git_blob":original.BLOB,
        "source_sha256":original.SOURCE_SHA,
        "original_source_rows":original.MAX_SOURCE_ROWS,
        "original_unique_triples":original.UNIQUE_TRIPLES,
        "full_source_roles":len(roles),
        "binding_comparator":result,
        "original_metaqa_qa_questions_read":False,
        "original_metaqa_answers_scored":False,
        "original_freebaseqa_graph_qualified":False,
        "learned_general_graph_reasoning":False,
        "independent_scientific_firstuse":False,
        "accepted_science":False,
        "accepted_ref_mutation":False,
        "dream_pareto_promotion":False,
        "thetaevolve_accepted_training":False,
        "science_dispatch":False,
        "model_calls":0,"codex_calls":0,"cloudflare_writes":0,
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source-raw",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    opts=p.parse_args()
    need(not opts.out.exists(),"REFUSE_EVIDENCE_OVERWRITE")
    st=opts.source_raw.lstat()
    need(stat.S_ISREG(st.st_mode) and 0<st.st_size<=original.MAX_FILE,
         "SOURCE_FILE_NOT_REGULAR_OR_WITHIN_BUDGET")
    result=audit(opts.source_raw.read_bytes())
    out=(json.dumps(result,sort_keys=True,indent=2,ensure_ascii=True)+"\n").encode()
    with opts.out.open("xb") as dest:dest.write(out)
    print("F118O_AUTHENTIC_SOURCE_EDGES_NODE_DISJOINT_LEARNED_BINDING_MEASURED")
    print("F118O_MODEL_IS_LOSSY_HASH_EQUALS_NOT_AUTONOMOUS_GRAPH_REASONING")

if __name__=="__main__":
    try:main()
    except (Denied,original.Denied,ValueError,UnicodeError,OSError) as exc:
        print("F118O_AUTHENTIC_NODE_BINDING_DENIED:",exc,file=sys.stderr)
        sys.exit(1)
