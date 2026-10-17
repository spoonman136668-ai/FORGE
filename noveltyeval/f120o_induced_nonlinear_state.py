"""F120-O: nonlinear query-conditioned intermediate-state updates across node-disjoint KG partitions.

Graph connectivity, including the exact shared middle entity, is PROVIDED by
source adjacency. No entity hash-equality features or QA source labels enter
the model. The learner trains role gates and nonlinear intermediate state only.
"""
from __future__ import annotations
import argparse
from collections import Counter,defaultdict
import hashlib
import json
import math
from pathlib import Path
import stat
import sys

import f116o_learned_composition as original
import f119o_root_conditioned_propagation as linear

SCHEMA="forge.optimizer.f120o.induced-graph-nonlinear-state.v1"
STATUS="PUBLIC_METAQA_INDUCED_NODE_DISJOINT_NONLINEAR_STATE_LEARNING_ENGINEERING_ONLY"
N=18
D=3
EPOCHS=120
LR=0.35
L2=0.005
CAP_FIRST=128
CAP_PATHS=4096
CAP_TARGETS=512
TRAIN=64
DEV=24
TEST=48

class Denied(Exception):pass

def need(ok,reason):
    if not ok:raise Denied("F120O_INDUCED_GRAPH_OR_LEARNING_DENIED_"+reason)

def sha(value:str)->bytes:
    return hashlib.sha256(value.encode("utf-8","strict")).digest()

def partition(node:str)->str:
    bucket=int.from_bytes(sha(node)[:8],"big")%20
    return "train" if bucket<=13 else ("dev" if bucket<=16 else "test")

def shuffle_order(root:str)->bool:
    return (hashlib.sha256(b"F120O-order|"+root.encode("utf-8","strict")).digest()[0]&1)==0

def induce_graphs(triples,roles):
    typed={(role,d):i for i,(role,d) in
           enumerate(original.role_types(roles))}
    groups={k:defaultdict(list) for k in ("train","dev","test")}
    all_nodes={v for a,r,b in triples for v in (a,b)}
    label={node:partition(node) for node in all_nodes}
    node_counts=Counter(label.values())
    accepted=Counter()
    crossed=0
    self_denied=0
    for a,r,b in triples:
        if a==b:
            self_denied+=1
            continue
        segment=label[a]
        if segment!=label[b]:
            crossed+=1
            continue
        fact=(a,r,b)
        groups[segment][a].append((b,typed[(r,"F")],fact))
        groups[segment][b].append((a,typed[(r,"R")],fact))
        accepted[segment]+=1
    for subgraph in groups.values():
        for root in subgraph:
            subgraph[root].sort(key=lambda z:(z[1],z[0],z[2]))
    need(sum(accepted.values())+crossed+self_denied==original.UNIQUE_TRIPLES,
         "PARTITION_CENSUS_INCOMPLETE")
    need(len(all_nodes)==43234 and all(node_counts[s]>0 for s in groups),
         "PUBLISHER_COMPLETE_ORIGINAL_NODE_POPULATION")
    used_nodes={g:set(edges.keys()) |
                {dst for children in edges.values() for dst,_,_ in children}
                for g,edges in groups.items()}
    need(not(used_nodes["train"]&used_nodes["dev"]) and
         not(used_nodes["train"]&used_nodes["test"]) and
         not(used_nodes["dev"]&used_nodes["test"]),
         "SOURCE_SPLIT_NODES_LEAKED")
    census={
        "full_original_distinct_nodes":len(all_nodes),
        "node_partition_nominal_counts":dict(sorted(node_counts.items())),
        "admitted_source_unique_nonself_triples":dict(sorted(accepted.items())),
        "original_cross_partition_triples_excluded":crossed,
        "original_self_loops_excluded":self_denied,
        "signed_arcs_by_split":{k:2*accepted[k] for k in groups},
        "nonoverlapping_source_nodes_and_edges":True,
    }
    return groups,census

def source_root_paths(root,graph):
    initial=graph.get(root,())
    if not initial or len(initial)>CAP_FIRST:return None
    examined=0
    # middle -> (first-role counts, target -> second-role counts)
    mids={}
    target_hist=defaultdict(Counter)
    for middle,role1,fact1 in initial:
        next_arcs=graph.get(middle,())
        examined+=len(next_arcs)
        if examined>CAP_PATHS:return None
        for target,role2,fact2 in next_arcs:
            if target==root or fact1==fact2:continue
            if middle not in mids:
                mids[middle]=[Counter(),defaultdict(Counter)]
            # Role one will be counted in the first-hop pass once per arc,
            # outside this nested loop, even if the middle has multiple edges.
            mids[middle][1][target][role2]+=1
            target_hist[target][(role1,role2)]+=1
            if len(target_hist)>CAP_TARGETS:return None
    # For a specific middle, first-hop counts MUST be from entire source arcs,
    # but target_out counts above were multiplied by number of root->middle
    # arcs. Recompute to remove this unintended multiplicity.
    mids={}
    for middle,role1,fact1 in initial:
        if middle not in mids:
            mids[middle]=[Counter(),defaultdict(Counter)]
        mids[middle][0][role1]+=1
    for middle,(first_counts,out_counts) in mids.items():
        for target,role2,fact2 in graph.get(middle,()):
            if target==root:continue
            # physical fact reuse can only return to root for non-self edges.
            out_counts[target][role2]+=1
    return target_hist,mids

def freeze_task(root,source_result):
    if source_result is None:return None
    histogram,mids=source_result
    if len(histogram)<2:return None
    for query in sorted({pair for h in histogram.values() for pair in h}):
        positives=sorted(t for t,h in histogram.items() if h.get(query,0)>0)
        negatives=sorted(t for t,h in histogram.items() if h.get(query,0)==0 and
                         sum(h.values())>0)
        if not positives or not negatives:continue
        pos,neg=positives[0],negatives[0]
        first_positive=shuffle_order(root)
        first,second=(pos,neg) if first_positive else (neg,pos)
        # Compress each actual node state to exact first/second role counts;
        # do not expose middle source identity to learned features.
        states=[]
        for middle,(one,out) in mids.items():
            c0=out.get(first,Counter())
            c1=out.get(second,Counter())
            if c0 or c1:
                states.append((tuple(sorted(one.items())),
                               tuple(sorted(c0.items())),
                               tuple(sorted(c1.items()))))
        need(bool(states) and
             (histogram[first].get(query,0)>0)!=
             (histogram[second].get(query,0)>0),
             "EXACT_SOURCE_QUERY_WITNESS_CONTRADICTORY")
        return (root,query,states,dict(histogram[first]),
                dict(histogram[second]),int(first_positive))
    return None

def select_tasks(graphs):
    quotas={"train":TRAIN,"dev":DEV,"test":TEST}
    tasks={}
    skipped={}
    for name,graph in graphs.items():
        roots=sorted(graph,key=lambda x:(sha(x),x.encode("utf-8","strict")))
        group=[]
        denied=0
        for root in roots:
            result=source_root_paths(root,graph)
            if result is None:
                denied+=1
                continue
            task=freeze_task(root,result)
            if task is None:continue
            group.append(task)
            if len(group)==quotas[name]:break
        need(len(group)==quotas[name],
             "FROZEN_DISJOINT_GRAPH_ROOT_COHORT_UNDERPOPULATED_"+name.upper())
        tasks[name]=group
        skipped[name]=denied
    need(len({t[0] for g in tasks.values() for t in g})==
         TRAIN+DEV+TEST,"SOURCE_ROOT_COHORTS_OVERLAP")
    return tasks,skipped

def init_embed(side,i,k):
    raw=hashlib.sha256(f"F120O-v1|{side}|{i}|{k}".encode("ascii")).digest()
    return (int.from_bytes(raw[:2],"big")/65535.0-0.5)*0.1

def softplus(value):
    return max(0.,value)+math.log1p(math.exp(-abs(value)))

def sigmoid(value):
    return original.sigmoid(value)

class NonlinearMessagePass:
    def __init__(self):
        self.Q=[[init_embed("Q",i,k) for k in range(D)] for i in range(N)]
        self.E=[[init_embed("E",i,k) for k in range(D)] for i in range(N)]
        self.bias=0.0
        self.alpha=1.0

    def params(self):
        vals=[self.bias,self.alpha]
        for group in (self.Q,self.E):
            for row in group:vals.extend(row)
        return vals

    def gates(self):
        return [[sigmoid(self.bias+sum(self.Q[i][d]*self.E[j][d]
                 for d in range(D))) for j in range(N)] for i in range(N)]

    @staticmethod
    def state(task,gates,alpha):
        _,(q1,q2),states,_,_,_=task
        left_mass=right_mass=0.0
        stored=[]
        for incoming,out0,out1 in states:
            f=sum(count*gates[q1][role] for role,count in incoming)
            hidden=math.tanh(alpha*f)
            a=sum(count*gates[q2][role] for role,count in out0)
            b=sum(count*gates[q2][role] for role,count in out1)
            left_mass+=hidden*a
            right_mass+=hidden*b
            stored.append((incoming,out0,out1,f,hidden,a,b))
        return left_mass,right_mass,stored

    def scores(self,task,gates=None,alpha=None):
        g=self.gates() if gates is None else gates
        scaling=self.alpha if alpha is None else alpha
        a,b,_=self.state(task,g,scaling)
        return math.log1p(a),math.log1p(b)

    def loss(self,train):
        need(bool(train),"EMPTY_TRAIN")
        g=self.gates()
        total=0.
        for task in train:
            first,second=self.scores(task,g)
            d=(first-second) if task[5] else (second-first)
            total+=softplus(-d)
        return total/len(train)

    def train(self,train):
        need(bool(train),"NO_TRAIN_TASKS")
        before=self.loss(train)
        initial=self.params()
        for _ in range(EPOCHS):
            gate_gradient=[[0.0]*N for _ in range(N)]
            ga=0.0
            g=self.gates()
            for task in train:
                _,(q1,q2),_,_,_,first_positive=task
                ma,mb,states=self.state(task,g,self.alpha)
                d=(math.log1p(ma)-math.log1p(mb))
                if not first_positive:d=-d
                delta=sigmoid(d)-1.0
                coef_a=(delta if first_positive else -delta)/(1+ma)
                coef_b=(-delta if first_positive else delta)/(1+mb)
                for incoming,out0,out1,f,hidden,a,b in states:
                    grad_hidden=coef_a*a+coef_b*b
                    slope=(1-hidden*hidden)
                    ga+=grad_hidden*slope*f
                    for role,count in incoming:
                        gate_gradient[q1][role]+=grad_hidden*slope*self.alpha*count
                    for role,count in out0:
                        gate_gradient[q2][role]+=hidden*coef_a*count
                    for role,count in out1:
                        gate_gradient[q2][role]+=hidden*coef_b*count
            grad_q=[[0.0]*D for _ in range(N)]
            grad_e=[[0.0]*D for _ in range(N)]
            gb=0.0
            for q in range(N):
                for r in range(N):
                    chain=gate_gradient[q][r]*g[q][r]*(1-g[q][r])
                    gb+=chain
                    for k in range(D):
                        grad_q[q][k]+=chain*self.E[r][k]
                        grad_e[r][k]+=chain*self.Q[q][k]
            denom=len(train)
            self.bias-=LR*gb/denom
            self.alpha-=LR*ga/denom
            for role in range(N):
                for k in range(D):
                    self.Q[role][k]-=LR*(grad_q[role][k]/denom+L2*self.Q[role][k])
                    self.E[role][k]-=LR*(grad_e[role][k]/denom+L2*self.E[role][k])
        after=self.loss(train)
        current=self.params()
        change=math.sqrt(sum((a-b)**2 for a,b in zip(initial,current)))
        need(change>1e-9 and after<before and math.isfinite(after),
             "NO_GENUINE_NONLINEAR_GRADIENT_PROGRESS")
        digest=hashlib.sha256(",".join(f"{v:.8f}" for v in current).encode("ascii")).hexdigest()
        return {"training_epochs":EPOCHS,
                "trainable_parameters":len(current),
                "train_logloss_initial":round(before,8),
                "train_logloss_final":round(after,8),
                "parameter_l2_movement":round(change,8),
                "parameter_sha256":digest,
                "learned_alpha":round(self.alpha,8)}

def decide(pair):
    return 0 if pair[0]>=pair[1] else 1

def metrics(tasks,predictor):
    labels=[int(t[5]) for t in tasks]
    preds=[int(predictor(t)==0) for t in tasks]
    return original.performance(labels,preds)

def audit(raw:bytes):
    need(original.source_digest(raw),"AUTHENTIC_SOURCE_SHA_AND_GIT_OBJECT")
    triples,roles=original.load_original_triples(raw)
    graphs,census=induce_graphs(triples,roles)
    tasks,skipped=select_tasks(graphs)
    net=NonlinearMessagePass()
    frozen_g=net.gates()
    frozen_alpha=net.alpha
    # F119's linear role-gating model is trained only on this F120 TRAIN
    # graph family, never on old F119 source tasks.
    linear_tasks=[(t[0],t[1],t[3],t[4],t[5]) for t in tasks["train"]]
    comparator=linear.LearnedTypedState()
    comparator_training=comparator.train(linear_tasks)
    training=net.train(tasks["train"])
    controls={
        "learned_nonlinear_intermediate_state":lambda t:decide(net.scores(t)),
        "constant_first_candidate":lambda t:0,
        "untyped_connected_path_count":lambda t:decide(
            (sum(t[3].values()),sum(t[4].values()))),
        "same_nonlinear_architecture_untrained":lambda t:decide(
            net.scores(t,frozen_g,frozen_alpha)),
        "trained_f119_linear_gate_same_split":lambda t:decide(
            comparator.scores((t[0],t[1],t[3],t[4],t[5]))),
        "privileged_exact_symbolic_twohop":lambda t:decide(
            (t[3].get(t[1],0),t[4].get(t[1],0))),
    }
    collected={name:{key:metrics(g,method) for key,method in controls.items()}
               for name,g in tasks.items() if name in ("dev","test")}
    for name in ("dev","test"):
        oracle=collected[name]["privileged_exact_symbolic_twohop"]
        need(oracle["n"]==len(tasks[name]) and
             oracle["both_classes_present"] and
             oracle["tp"]+oracle["tn"]==oracle["n"],
             "SOURCE_TRAVERSAL_ORACLE_FAILED")
    terminal=collected["test"]
    actual=terminal["learned_nonlinear_intermediate_state"]
    baselines=[v for key,v in terminal.items() if key not in (
        "learned_nonlinear_intermediate_state","privileged_exact_symbolic_twohop")]
    gain=(actual["both_classes_present"] and
          all(b["balanced_accuracy"] is not None for b in baselines) and
          actual["balanced_accuracy"]>=max(
              b["balanced_accuracy"] for b in baselines)+0.05)
    return {
        "schema":SCHEMA,"status":STATUS,
        "source_repository":"tiantiangao7/kalm-qa",
        "source_commit":original.UPSTREAM,
        "source_git_blob":original.BLOB,
        "source_sha256":original.SOURCE_SHA,
        "original_graph_rows":original.MAX_SOURCE_ROWS,
        "original_distinct_source_triples":original.UNIQUE_TRIPLES,
        "source_signed_role_types":N,
        "induced_disjoint_source_graph_census":census,
        "train_roots":TRAIN,"dev_roots":DEV,"terminal_roots":TEST,
        "overbudget_empty_roots_denied":skipped,
        "source_partitions_share_no_nodes_or_physical_edges":True,
        "inference_messages_follow_real_source_middle_nodes":True,
        "nonlinear_middle_node_update_trained":True,
        "graph_adjacency_and_middle_equality_are_provided":True,
        "training":training,
        "linear_f119_same_train_partition_control":comparator_training,
        "development_inspection_only":collected["dev"],
        "terminal_heldout":terminal,
        "gain_disposition":(
            "LEARNED_NONLINEAR_INDUCED_GRAPH_GAIN_DEMONSTRATED"
            if gain else "LEARNED_NONLINEAR_INDUCED_GRAPH_GAIN_NOT_DEMONSTRATED"),
        "original_metaqa_qa_source_read":False,
        "original_metaqa_question_answers_scored":False,
        "original_freebaseqa_graph_qualified":False,
        "independent_unseen_task_family_science_proven":False,
        "learned_graph_connectivity_proven":False,
        "independent_scientific_firstuse":False,
        "accepted_science":False,"accepted_ref_mutation":False,
        "dream_pareto_promotion":False,"thetaevolve_accepted_training":False,
        "scientific_dispatch":False,
        "model_calls":0,"codex_calls":0,"cloudflare_writes":0,
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source-raw",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    options=p.parse_args()
    need(not options.out.exists(),"EVIDENCE_OVERWRITE_NOT_ALLOWED")
    st=options.source_raw.lstat()
    need(stat.S_ISREG(st.st_mode) and 0<st.st_size<=original.MAX_FILE,
         "REGULAR_PINNED_SOURCE_AND_BUDGET")
    content=(json.dumps(audit(options.source_raw.read_bytes()),sort_keys=True,
                        indent=2,ensure_ascii=True)+"\n").encode("utf-8")
    with options.out.open("xb") as file:file.write(content)
    print("F120O_AUTHENTIC_NODE_DISJOINT_INDUCED_GRAPH_NONLINEAR_STATE_AUDITED")
    print("F120O_SOURCE_CONNECTIVITY_PROVIDED_NO_INDEPENDENT_SCIENTIFIC_ACCEPTANCE")

if __name__=="__main__":
    try:main()
    except (Denied,original.Denied,linear.Denied,OSError,UnicodeError,ValueError) as ex:
        print("F120O_INDUCED_GRAPH_OR_MODEL_NOT_QUALIFIED",ex,file=sys.stderr)
        sys.exit(1)
