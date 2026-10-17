"""F121-O — authentic graph role-selector trained on 2-hop, tested on 3-hop.

Source 3-hop paths have exact joined intermediate nodes and immutable physical
facts. The learned model sees only graph-path role histograms and signed roles,
not node IDs or QA answer labels. The feature 1[role==query] is a PROVIDED prior.
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

import f116o_learned_composition as source
import f119o_root_conditioned_propagation as linear

SCHEMA="forge.optimizer.f121o.authentic-two-to-three-hop-role-transfer.v1"
STATUS="PUBLIC_METAQA_INDUCED_DISJOINT_TWO_TO_THREE_HOP_ROLE_TRANSFER_ENGINEERING_ONLY"
N=18
D=3
TRAIN=64
DEV=16
TEST=32
EPOCHS=120
LR=0.35
L2=0.005
CAP_FIRST=128
CAP_SECOND=4096
CAP_THIRD=8192
CAP_PATHS=8192
CAP_TARGETS=512

class Denied(Exception):pass

def require(ok,why):
    if not ok:raise Denied("F121O_SOURCE_OR_EXPERIMENT_DENIED_"+why)

def digest(s:str)->bytes:
    return hashlib.sha256(s.encode("utf-8","strict")).digest()

def subgraph_partition(node:str)->str:
    raw=hashlib.sha256(b"F121O-graph-v1|"+node.encode("utf-8","strict")).digest()
    v=int.from_bytes(raw[:8],"big")%20
    return "train" if v<=13 else ("dev" if v<=16 else "test")

def candidate_first_positive(root:str)->bool:
    h=hashlib.sha256(b"F121O-order-v1|"+root.encode("utf-8","strict")).digest()
    return (h[0]&1)==0

def induce_source_graphs(triples,roles):
    typeids={(role,d):i for i,(role,d) in enumerate(source.role_types(roles))}
    all_nodes={v for a,r,b in triples for v in (a,b)}
    partition={node:subgraph_partition(node) for node in all_nodes}
    nodes=Counter(partition.values())
    graph={part:defaultdict(list) for part in ("train","dev","test")}
    admitted=Counter()
    crossed=0
    selfloops=0
    for a,r,b in triples:
        if a==b:
            selfloops+=1
            continue
        pa=partition[a]
        if pa!=partition[b]:
            crossed+=1
            continue
        fact=(a,r,b)
        graph[pa][a].append((b,typeids[(r,"F")],fact))
        graph[pa][b].append((a,typeids[(r,"R")],fact))
        admitted[pa]+=1
    for sub in graph.values():
        for node in sub:sub[node].sort(key=lambda e:(e[1],e[0],e[2]))
    ids={part:set(sub)|{target for arcs in sub.values() for target,_,_ in arcs}
         for part,sub in graph.items()}
    require(not(ids["train"] & ids["dev"]) and
            not(ids["train"] & ids["test"]) and
            not(ids["dev"] & ids["test"]),"SHARED_NODE_INDUCED_GRAPHS")
    require(sum(admitted.values())+crossed+selfloops==source.UNIQUE_TRIPLES,
            "SOURCE_TRIPLES_NOT_EXACTLY_PARTITIONED")
    require(sum(nodes.values())==43234 and selfloops==11,
            "WHOLE_AUTHENTIC_GRAPH_NODE_CENSUS")
    return graph,{
        "whole_original_nodes":len(all_nodes),
        "partition_node_census":dict(sorted(nodes.items())),
        "admitted_original_physical_edges":dict(sorted(admitted.items())),
        "signed_arcs":{key:2*admitted[key] for key in graph},
        "cross_split_edges_dropped":crossed,
        "source_self_loops_excluded":selfloops,
        "all_train_dev_test_nodes_and_physical_facts_disjoint":True,
    }

def three_hop_histogram(root,graph):
    first=graph.get(root,())
    if not first or len(first)>CAP_FIRST:return None
    two_seen=0
    three_seen=0
    accepted_paths=0
    hist=defaultdict(Counter)
    for middle_one,r1,fact1 in first:
        second=graph.get(middle_one,())
        two_seen+=len(second)
        if two_seen>CAP_SECOND:return None
        for middle_two,r2,fact2 in second:
            if middle_two==root or middle_two==middle_one or fact2==fact1:
                continue
            third=graph.get(middle_two,())
            three_seen+=len(third)
            if three_seen>CAP_THIRD:return None
            for target,r3,fact3 in third:
                if (target in (root,middle_one,middle_two) or
                        fact3==fact2 or fact3==fact1):
                    continue
                accepted_paths+=1
                if accepted_paths>CAP_PATHS:return None
                hist[target][(r1,r2,r3)]+=1
                if len(hist)>CAP_TARGETS:return None
    return hist

def two_hop_histogram(root,graph):
    # Reuse prior qualified physical exact-join implementation for TRAIN only.
    return linear.full_two_step_histogram(root,graph)

def choose_task(root,hist):
    if hist is None or len(hist)<2:return None
    for query in sorted({q for counts in hist.values() for q in counts}):
        positive=sorted(t for t,counts in hist.items() if counts.get(query,0)>0)
        negative=sorted(t for t,counts in hist.items() if counts.get(query,0)==0
                        and sum(counts.values())>0)
        if positive and negative:
            pos,neg=positive[0],negative[0]
            order=candidate_first_positive(root)
            first,second=(pos,neg) if order else (neg,pos)
            require(pos!=neg and sum(hist[first].values())>0 and
                    sum(hist[second].values())>0,"INVALID_SOURCE_CANDIDATES")
            return (root,query,dict(hist[first]),dict(hist[second]),int(order))
    return None

def choose_frozen_tasks(graphs):
    targets={"train":TRAIN,"dev":DEV,"test":TEST}
    selected={}
    skipped={}
    for part,sub in graphs.items():
        tasks=[]
        denied=0
        for root in sorted(sub,key=lambda v:(digest(v),v.encode("utf-8","strict"))):
            raw=(two_hop_histogram(root,sub) if part=="train" else
                 three_hop_histogram(root,sub))
            if raw is None:
                denied+=1
                continue
            q=choose_task(root,raw)
            if q is None:continue
            require(len(q[1])==(2 if part=="train" else 3),
                    "FROZEN_TRAIN_TEST_DIFFERENT_HOP_COUNTS")
            tasks.append(q)
            if len(tasks)==targets[part]:break
        require(len(tasks)==targets[part],
                "SOURCE_ORIGINAL_HOP_ROOTS_UNDERPOPULATED_"+part.upper())
        selected[part]=tasks
        skipped[part]=denied
    ids=[t[0] for tasks in selected.values() for t in tasks]
    require(len(ids)==len(set(ids)),"CROSS_FAMILY_ROOT_CONTAMINATION")
    return selected,skipped

def init(side,i,k):
    digest=hashlib.sha256(f"F121O-v1|{side}|{i}|{k}".encode("ascii")).digest()
    return (int.from_bytes(digest[:2],"big")/65535.0-0.5)*0.1

def softplus(x):
    return max(0.0,x)+math.log1p(math.exp(-abs(x)))

class AlignedRoleGate:
    def __init__(self):
        self.Q=[[init("Q",i,k) for k in range(D)] for i in range(N)]
        self.E=[[init("E",i,k) for k in range(D)] for i in range(N)]
        self.bias=0.0
        self.eta=0.0

    def params(self):
        vals=[self.bias,self.eta]
        for rows in (self.Q,self.E):
            for row in rows:vals.extend(row)
        return vals

    def gates(self):
        return [[source.sigmoid(self.bias+
                 sum(self.Q[q][k]*self.E[r][k] for k in range(D))+
                 (self.eta if q==r else 0.0))
                 for r in range(N)] for q in range(N)]

    @staticmethod
    def masses(task,gates):
        _,query,first,second,_=task
        def mass(h):
            return sum(count*math.prod(gates[q][r] for q,r in zip(query,roles))
                       for roles,count in h.items())
        return mass(first),mass(second)

    def scores(self,task,gates=None):
        a,b=self.masses(task,self.gates() if gates is None else gates)
        return math.log1p(a),math.log1p(b)

    def loss(self,tasks):
        require(bool(tasks),"EMPTY_TRAINING")
        gates=self.gates()
        value=0.0
        for task in tasks:
            a,b=self.scores(task,gates)
            diff=a-b if task[4] else b-a
            value+=softplus(-diff)
        return value/len(tasks)

    def train(self,tasks):
        require(all(len(t[1])==2 for t in tasks),"ONLY_TWO_HOP_TRAINING")
        before=self.loss(tasks)
        initial=self.params()
        n=len(tasks)
        for _ in range(EPOCHS):
            gates=self.gates()
            dg=[[0.0]*N for _ in range(N)]
            for task in tasks:
                _,(q1,q2),first,second,first_positive=task
                pos,neg=(first,second) if first_positive else (second,first)
                mass_pos,mass_neg=(self.masses(
                    (task[0],task[1],pos,neg,1),gates))
                delta=source.sigmoid(math.log1p(mass_pos)-math.log1p(mass_neg))-1.0
                for hist,coeff in ((pos,delta/(1+mass_pos)),
                                   (neg,-delta/(1+mass_neg))):
                    for (r1,r2),count in hist.items():
                        dg[q1][r1]+=coeff*count*gates[q2][r2]
                        dg[q2][r2]+=coeff*count*gates[q1][r1]
            gq=[[0.0]*D for _ in range(N)]
            ge=[[0.0]*D for _ in range(N)]
            gb=0.0
            geta=0.0
            for q in range(N):
                for r in range(N):
                    d=dg[q][r]*gates[q][r]*(1-gates[q][r])
                    gb+=d
                    if q==r:geta+=d
                    for k in range(D):
                        gq[q][k]+=d*self.E[r][k]
                        ge[r][k]+=d*self.Q[q][k]
            self.bias-=LR*gb/n
            self.eta-=LR*geta/n
            for i in range(N):
                for k in range(D):
                    self.Q[i][k]-=LR*(gq[i][k]/n+L2*self.Q[i][k])
                    self.E[i][k]-=LR*(ge[i][k]/n+L2*self.E[i][k])
        after=self.loss(tasks)
        current=self.params()
        movement=math.sqrt(sum((a-b)**2 for a,b in zip(initial,current)))
        require(after<before and movement>1e-9 and math.isfinite(after),
                "TRAINED_TWO_HOP_GRADIENT_WAS_INEFFECTIVE")
        digest=hashlib.sha256(",".join(f"{v:.8f}" for v in current).encode("ascii")).hexdigest()
        return {"training_epochs":EPOCHS,
                "trainable_parameters":len(current),
                "training_loss_initial":round(before,8),
                "training_loss_final":round(after,8),
                "parameter_movement_l2":round(movement,8),
                "learned_eta_role_identity_bias":round(self.eta,8),
                "parameter_vector_sha256":digest}

def choose(scores):
    return 0 if scores[0]>=scores[1] else 1

def assessment(tasks,decision):
    return source.performance(
        [int(t[4]) for t in tasks],
        [int(decision(t)==0) for t in tasks])

def audit(raw):
    require(source.source_digest(raw),"ORIGINAL_PUBLIC_SOURCE_SHA_OR_GIT_OBJECT")
    triples,roles=source.load_original_triples(raw)
    graphs,census=induce_source_graphs(triples,roles)
    tasks,skipped=choose_frozen_tasks(graphs)
    model=AlignedRoleGate()
    untrained_gates=model.gates()
    classic=linear.LearnedTypedState()
    classic_record=classic.train(tasks["train"])
    record=model.train(tasks["train"])
    def triple_score(task,gates):
        return AlignedRoleGate.masses(task,gates)
    model_gates=model.gates()
    classic_gates=classic.gate()
    fixed_soft=[[0.75 if q==r else 0.25 for r in range(N)] for q in range(N)]
    def hard_oracle(t):
        q=t[1]
        return choose((t[2].get(q,0),t[3].get(q,0)))
    controls={
        "trained_signed_role_identity_alignment":lambda t:choose(triple_score(t,model_gates)),
        "constant_first_candidate":lambda t:0,
        "uniform_untyped_physical_3hop_counts":lambda t:choose((
            sum(t[2].values()),sum(t[3].values()))),
        "same_architecture_frozen_untrained":lambda t:choose(triple_score(t,untrained_gates)),
        "f119_trained_linear_gates_2hop_only":lambda t:choose(triple_score(t,classic_gates)),
        "fixed_soft_role_identity_prior":lambda t:choose(triple_score(t,fixed_soft)),
        "privileged_exact_symbolic_typed_3hop":hard_oracle,
    }
    measured={part:{name:assessment(rows,fn) for name,fn in controls.items()}
              for part,rows in tasks.items() if part in ("dev","test")}
    for part in ("dev","test"):
        oracle=measured[part]["privileged_exact_symbolic_typed_3hop"]
        require(oracle["both_classes_present"] and
                oracle["tp"]+oracle["tn"]==oracle["n"],
                "SOURCE_EXACT_GRAPH_ORACLE_INVALID")
    hold=measured["test"]
    learned=hold["trained_signed_role_identity_alignment"]
    prior=[item for name,item in hold.items() if name not in (
        "trained_signed_role_identity_alignment",
        "privileged_exact_symbolic_typed_3hop")]
    gain=(learned["both_classes_present"] and all(
        p["balanced_accuracy"] is not None for p in prior) and
        learned["balanced_accuracy"]>=max(
            p["balanced_accuracy"] for p in prior)+0.05)
    return {
        "schema":SCHEMA,"status":STATUS,
        "source_repository":"tiantiangao7/kalm-qa",
        "source_commit":source.UPSTREAM,
        "source_git_blob":source.BLOB,
        "source_sha256":source.SOURCE_SHA,
        "original_source_rows":source.MAX_SOURCE_ROWS,
        "original_unique_source_triples":source.UNIQUE_TRIPLES,
        "signed_edge_relation_types":N,
        "new_salted_induced_graph_census":census,
        "train_source_root_tasks_2hop":TRAIN,
        "development_unseen_graph_root_tasks_3hop":DEV,
        "terminal_unseen_graph_root_tasks_3hop":TEST,
        "source_overbudget_or_empty_root_rejections":skipped,
        "physical_source_edges_and_nodes_disjoint":True,
        "source_exact_middle_nodes_connected":True,
        "identity_equality_signed_role_is_supplied_prior":True,
        "no_three_hop_training_labels_used":True,
        "training":record,
        "f119_same_split_twohop_training_only":classic_record,
        "development_inspection_only":measured["dev"],
        "terminal_unseen_three_hop":hold,
        "gain_disposition":(
            "LEARNED_TWO_TO_THREE_HOP_ROLE_ALIGNMENT_GAIN_DEMONSTRATED"
            if gain else "LEARNED_TWO_TO_THREE_HOP_ROLE_ALIGNMENT_GAIN_NOT_DEMONSTRATED"),
        "original_metaqa_qa_read":False,
        "original_metaqa_answers_compared":False,
        "original_freebaseqa_graph_qualified":False,
        "learned_graph_connectivity_proven":False,
        "independent_novel_task_family_science_proven":False,
        "independent_scientific_firstuse":False,
        "accepted_science":False,
        "accepted_ref_mutation":False,
        "dream_pareto_promotion":False,
        "thetaevolve_accepted_training":False,
        "scientific_dispatch":False,
        "codex_calls":0,"model_calls":0,"cloudflare_writes":0,
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    require(not a.out.exists(),"NO_ARTIFACT_OVERWRITE")
    statinfo=a.source.lstat()
    require(stat.S_ISREG(statinfo.st_mode) and 0<statinfo.st_size<=source.MAX_FILE,
            "PINNED_SOURCE_REGULAR_AND_BOUNDED")
    result=audit(a.source.read_bytes())
    data=(json.dumps(result,sort_keys=True,indent=2,ensure_ascii=True)+"\n").encode()
    with a.out.open("xb") as f:f.write(data)
    print("F121O_AUTHENTIC_GRAPH_DISJOINT_2TO3_HOP_HELDOUT_TRANSFER_MEASURED")
    print("F121O_SOURCE_GRAPH_CONNECTIVITY_AND_ROLE_IDENTITY_SUPPLIED_NOT_LEARNED")

if __name__=="__main__":
    try:main()
    except (Denied,source.Denied,linear.Denied,OSError,ValueError,UnicodeError) as err:
        print("F121O_ORIGINAL_GRAPH_OR_TRANSFER_NOT_QUALIFIED",err,file=sys.stderr)
        sys.exit(1)
