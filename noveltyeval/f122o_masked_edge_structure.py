"""F122-O trainable masked-edge inference from incomplete unlabeled topology.

Original author MetaQA physical edges withheld *globally*, including all
relations and reciprocal directions per unordered pair. Only residual
8-dimensional local topology features enter either learned model. Source
truth and ID hashes used ONLY by offline frozen cohort constructor.
"""
from __future__ import annotations
import argparse
from collections import Counter,defaultdict
from bisect import bisect_left
import hashlib
import json
import math
from pathlib import Path
import stat
import sys

import f116o_learned_composition as source

SCHEMA="forge.optimizer.f122o.original-masked-structural-inference.v1"
STATUS="PUBLIC_METAQA_INDUCED_DISJOINT_MASKED_EDGE_STRUCTURAL_INFERENCE_ENGINEERING_ONLY"
TRAIN=192
DEV=48
TEST=64
D=8
H=6
EPOCHS=180
LR=0.45
L2=0.002
MAX_DEGREE=128
MAX_SECOND_EXAMINED=4096

class Denied(Exception):pass

def need(ok,reason):
    if not ok:raise Denied("F122O_AUTHENTIC_MASKED_SOURCE_DENIED_"+reason)

def sha(data:bytes)->bytes:
    return hashlib.sha256(data).digest()

def entity_bytes(entity:str)->bytes:
    return entity.encode("utf-8","strict")

def split_node(node:str)->str:
    h=sha(b"F122O-graph-v1|"+entity_bytes(node))
    bucket=int.from_bytes(h[:8],"big")%20
    return "train" if bucket<=13 else ("dev" if bucket<=16 else "test")

def undirected(a:str,b:str)->tuple[str,str]:
    return (a,b) if entity_bytes(a)<entity_bytes(b) else (b,a)

def pair_bytes(pair:tuple[str,str])->bytes:
    return entity_bytes(pair[0])+b"\x1f"+entity_bytes(pair[1])

def masked(pair:tuple[str,str])->bool:
    h=sha(b"F122O-mask-v1|"+pair_bytes(pair))
    return int.from_bytes(h[:8],"big")%4==0

def frozen_pair_order(pair):
    raw=pair_bytes(pair)
    return sha(b"F122O-positive-v1|"+raw),raw

def candidate_positive_first(pair)->bool:
    return (sha(b"F122O-order-v1|"+pair_bytes(pair))[0]&1)==0

def source_residual_graphs(triples):
    parts=("train","dev","test")
    every_node={name for a,role,b in triples for name in (a,b)}
    split={name:split_node(name) for name in every_node}
    node_counts=Counter(split.values())
    original_pairs={k:set() for k in parts}
    crossed=0
    self_loops=0
    admitted_triples=Counter()
    for a,role,b in triples:
        if a==b:
            self_loops+=1
            continue
        s=split[a]
        if s!=split[b]:
            crossed+=1
            continue
        original_pairs[s].add(undirected(a,b))
        admitted_triples[s]+=1
    residual={}
    positive={}
    census={}
    for part in parts:
        graph=defaultdict(set)
        withheld=[]
        surviving=0
        for pair in original_pairs[part]:
            a,b=pair
            if masked(pair):
                withheld.append(pair)
            else:
                graph[a].add(b)
                graph[b].add(a)
                surviving+=1
        residual[part]=graph
        positive[part]=sorted(withheld,key=frozen_pair_order)
        # Global-mask independence: every physical pair with all source
        # relation variants and both orientations has been removed.
        need(all(b not in graph.get(a,set()) and
                 a not in graph.get(b,set())
                 for a,b in withheld),"MASKED_ORIGINAL_PAIR_LEAKED")
        census[part]={
            "partition_original_nodes":node_counts[part],
            "original_undirected_unique_endpoint_pairs":len(original_pairs[part]),
            "masked_all_role_unordered_endpoint_pairs":len(withheld),
            "residual_undirected_endpoint_pairs":surviving,
            "original_physical_nonself_triples":admitted_triples[part],
            "residual_nodes_with_positive_degree":len(graph),
            "max_residual_node_degree":max(map(len,graph.values()),default=0),
        }
        need(len(withheld)+surviving==len(original_pairs[part]),
             "GLOBAL_MASK_PARTITION_DENOMINATOR")
    need(sum(admitted_triples.values())+crossed+self_loops==source.UNIQUE_TRIPLES,
         "COMPLETE_ORIGINAL_SOURCE_ROWS")
    need(sum(node_counts.values())==43234 and self_loops==11,
         "ORIGINAL_AUTHENTIC_KG_NODE_CENSUS")
    ids={key:set(g) for key,g in residual.items()}
    need(not ids["train"]&ids["dev"] and
         not ids["train"]&ids["test"] and
         not ids["dev"]&ids["test"],"CROSS_SPLIT_SOURCE_NODES_LEAKED")
    return residual,positive,original_pairs,{
        "whole_original_nodes":len(every_node),
        "cross_partition_original_triples_discarded":crossed,
        "original_source_self_loops_excluded":self_loops,
        "graphs":census,
        "split_node_and_physical_edge_sets_disjoint":True,
        "all_predicate_variants_and_reverse_edges_globally_masked":True,
    }

def feature_vector(root,target,graph):
    neighbors_a=graph.get(root,set())
    neighbors_b=graph.get(target,set())
    da,db=len(neighbors_a),len(neighbors_b)
    if root==target or not(0<da<=MAX_DEGREE and 0<db<=MAX_DEGREE):
        return None
    if target in neighbors_a or root in neighbors_b:
        return None
    common=neighbors_a & neighbors_b
    aa=sum(1.0/math.log(2+len(graph.get(mid,set()))) for mid in common)
    three=0
    explored=0
    for m1 in neighbors_a:
        children=graph.get(m1,set())
        explored+=len(children)
        if explored>MAX_SECOND_EXAMINED:return None
        for m2 in children:
            if m2==root or m2==m1 or m2==target or m1==target:
                continue
            if target in graph.get(m2,set()):
                three+=1
    la=math.log1p(da)/6
    lb=math.log1p(db)/6
    neighbors_sum=sum(len(graph.get(mid,set())) for mid in neighbors_b)
    v=(
        la,
        lb,
        abs(la-lb),
        math.log1p(len(common))/6,
        aa/6,
        math.log1p(three)/6,
        math.log1p(three)/(1+math.log1p(da*db)),
        math.log1p(neighbors_sum)/6,
    )
    result=tuple(max(0.,min(2.,x)) for x in v)
    need(len(result)==D and all(math.isfinite(x) for x in result),
         "SOURCE_FEATURES_NUMERIC_AND_BOUNDED")
    return result

def degree_key(degree:int)->int:
    return degree.bit_length()

def choose_frozen_examples(graphs,positive,original_pairs):
    sizes={"train":TRAIN,"dev":DEV,"test":TEST}
    chosen={}
    excluded={}
    for part,graph in graphs.items():
        by_degree=defaultdict(list)
        for node in graph:
            count=len(graph[node])
            if 0<count<=MAX_DEGREE:
                by_degree[degree_key(count)].append(node)
        for bucket in by_degree:
            by_degree[bucket].sort(key=lambda n:(sha(entity_bytes(n)),entity_bytes(n)))
        examples=[]
        refused=Counter()
        for pair in positive[part]:
            a,b=pair
            fa=feature_vector(a,b,graph)
            if fa is None:
                refused["masked_positive_unusable"]=refused["masked_positive_unusable"]+1
                continue
            nodes=by_degree[degree_key(len(graph[b]))]
            if not nodes:
                refused["no_matched_degree_bin"]=refused["no_matched_degree_bin"]+1
                continue
            h=sha(b"F122O-neg-v1|"+pair_bytes(pair))
            start=int.from_bytes(h[:8],"big")%len(nodes)
            found=None
            for step in range(len(nodes)):
                candidate=nodes[(start+step)%len(nodes)]
                if candidate in (a,b) or undirected(a,candidate) in original_pairs[part]:
                    continue
                negative_feature=feature_vector(a,candidate,graph)
                if negative_feature is not None:
                    found=negative_feature
                    break
            if found is None:
                refused["no_valid_matched_hard_negative"]=refused["no_valid_matched_hard_negative"]+1
                continue
            first_positive=candidate_positive_first(pair)
            first,second=(fa,found) if first_positive else (found,fa)
            examples.append((first,second,int(first_positive)))
            if len(examples)==sizes[part]:break
        need(len(examples)==sizes[part],
             "FROZEN_MASKED_SOURCE_COHORT_UNDERPOPULATED_"+part.upper())
        chosen[part]=examples
        excluded[part]=dict(sorted(refused.items()))
    return chosen,excluded

def sigmoid(x):
    return source.sigmoid(x)

def softplus(x):
    return max(0.0,x)+math.log1p(math.exp(-abs(x)))

def initial(layer,i,j):
    value=sha(f"F122O-v1|{layer}|{i}|{j}".encode("ascii"))
    return (int.from_bytes(value[:2],"big")/65535.0-0.5)*0.1

class NeuralTopologyComparator:
    def __init__(self):
        self.W=[[initial("hidden",i,j) for j in range(D)] for i in range(H)]
        self.hidden_bias=[0.0]*H
        self.V=[initial("output",i,0) for i in range(H)]
        self.bias=0.0

    def params(self):
        return [v for row in self.W for v in row]+self.hidden_bias+self.V+[self.bias]

    def forward(self,x):
        hidden=[math.tanh(self.hidden_bias[i]+sum(self.W[i][d]*x[d]
                         for d in range(D))) for i in range(H)]
        score=self.bias+sum(w*z for w,z in zip(self.V,hidden))
        return score,hidden

    def score(self,x):
        return self.forward(x)[0]

    def loss(self,tasks):
        need(bool(tasks),"EMPTY_FROZEN_SOURCE_TRAIN")
        total=0.
        for first,second,label in tasks:
            a,b=self.score(first),self.score(second)
            good=a-b if label else b-a
            total+=softplus(-good)
        return total/len(tasks)

    def train(self,tasks):
        need(bool(tasks),"EMPTY_FROZEN_SOURCE_TRAIN")
        initial_loss=self.loss(tasks)
        initial_params=self.params()
        for _ in range(EPOCHS):
            grad_W=[[0.0]*D for _ in range(H)]
            grad_hidden=[0.0]*H
            grad_V=[0.0]*H
            grad_bias=0.0
            for first,second,label in tasks:
                positives=first if label else second
                negatives=second if label else first
                sp,hp=self.forward(positives)
                sn,hn=self.forward(negatives)
                delta=sigmoid(sp-sn)-1.0
                for x,hidden,dscore in ((positives,hp,delta),
                                         (negatives,hn,-delta)):
                    grad_bias+=dscore
                    for i in range(H):
                        grad_V[i]+=dscore*hidden[i]
                        g=dscore*self.V[i]*(1-hidden[i]*hidden[i])
                        grad_hidden[i]+=g
                        for d in range(D):
                            grad_W[i][d]+=g*x[d]
            count=len(tasks)
            self.bias-=LR*grad_bias/count
            for i in range(H):
                self.V[i]-=LR*(grad_V[i]/count+L2*self.V[i])
                self.hidden_bias[i]-=LR*grad_hidden[i]/count
                for d in range(D):
                    self.W[i][d]-=LR*(grad_W[i][d]/count+L2*self.W[i][d])
        final_loss=self.loss(tasks)
        current=self.params()
        movement=math.sqrt(sum((a-b)**2 for a,b in zip(initial_params,current)))
        need(final_loss<initial_loss and movement>1e-9 and
             math.isfinite(final_loss),"NEURAL_STRUCTURE_TRAINING_NOT_QUALIFIED")
        token=",".join(f"{x:.8f}" for x in current).encode("ascii")
        return {
            "training_epochs":EPOCHS,
            "learned_parameters":len(current),
            "training_logloss_initial":round(initial_loss,8),
            "training_logloss_final":round(final_loss,8),
            "parameter_movement_l2":round(movement,8),
            "learned_parameter_sha256":sha(token).hex(),
        }

class LinearTopologyComparator:
    def __init__(self):
        self.w=[0.0]*D
        self.bias=0.0
    def score(self,x):
        return self.bias+sum(w*v for w,v in zip(self.w,x))
    def loss(self,tasks):
        need(bool(tasks),"EMPTY_TRAIN_LINEAR")
        return sum(softplus(-((self.score(a)-self.score(b))*
                     (1 if y else -1))) for a,b,y in tasks)/len(tasks)
    def train(self,tasks):
        before=self.loss(tasks)
        for _ in range(EPOCHS):
            gw=[0.0]*D
            gb=0.0
            for first,second,y in tasks:
                pos,neg=(first,second) if y else (second,first)
                d=sigmoid(self.score(pos)-self.score(neg))-1.0
                for i in range(D):
                    gw[i]+=d*(pos[i]-neg[i])
            for i in range(D):
                self.w[i]-=LR*(gw[i]/len(tasks)+L2*self.w[i])
        after=self.loss(tasks)
        need(after<before,"STRUCTURAL_LINEAR_CONTROL_FAILED_TO_TRAIN")
        return {
            "training_epochs":EPOCHS,
            "learned_parameters":D+1,
            "training_logloss_initial":round(before,8),
            "training_logloss_final":round(after,8),
            "weight_change_l2":round(math.sqrt(sum(w*w for w in self.w)),8),
        }

def choice(a,b):
    return 0 if a>=b else 1

def evaluate(tasks,method):
    expected=[int(t[2]) for t in tasks]
    predicted=[int(method(t)==0) for t in tasks]
    return source.performance(expected,predicted)

def audit(raw):
    need(source.source_digest(raw),"ORIGINAL_GRAPH_GIT_BLOB_SHA256_MISMATCH")
    triples,roles=source.load_original_triples(raw)
    graphs,positives,pairs,census=source_residual_graphs(triples)
    tasks,refusals=choose_frozen_examples(graphs,positives,pairs)
    learner=NeuralTopologyComparator()
    untrained=NeuralTopologyComparator()
    linear=LinearTopologyComparator()
    trained_record=learner.train(tasks["train"])
    linear_record=linear.train(tasks["train"])
    methods={
        "trained_nonlinear_masked_topology":lambda t:choice(
            learner.score(t[0]),learner.score(t[1])),
        "constant_candidate_zero":lambda t:0,
        "fixed_common_neighbor_score":lambda t:choice(t[0][3],t[1][3]),
        "fixed_adamic_adar_score":lambda t:choice(t[0][4],t[1][4]),
        "fixed_threehop_path_count":lambda t:choice(t[0][5],t[1][5]),
        "train_only_linear_topology":lambda t:choice(
            linear.score(t[0]),linear.score(t[1])),
        "same_nonlinear_architecture_untrained":lambda t:choice(
            untrained.score(t[0]),untrained.score(t[1])),
        "privileged_original_source_edge_oracle":lambda t:0 if t[2] else 1,
    }
    results={part:{key:evaluate(rows,pred) for key,pred in methods.items()}
             for part,rows in tasks.items() if part in ("dev","test")}
    for part in ("dev","test"):
        truth=results[part]["privileged_original_source_edge_oracle"]
        need(truth["both_classes_present"] and truth["tp"]+truth["tn"]==truth["n"],
             "FROZEN_SOURCE_ORACLE_INCONSISTENT")
    actual=results["test"]["trained_nonlinear_masked_topology"]
    controls=[m for key,m in results["test"].items() if key not in (
        "trained_nonlinear_masked_topology",
        "privileged_original_source_edge_oracle")]
    gain=(actual["both_classes_present"] and
          all(c["balanced_accuracy"] is not None for c in controls) and
          actual["balanced_accuracy"]>=max(
              c["balanced_accuracy"] for c in controls)+0.05)
    return {
        "schema":SCHEMA,
        "status":STATUS,
        "source_repository":"tiantiangao7/kalm-qa",
        "source_commit":source.UPSTREAM,
        "source_git_blob":source.BLOB,
        "source_sha256":source.SOURCE_SHA,
        "source_original_rows":source.MAX_SOURCE_ROWS,
        "source_unique_triples":source.UNIQUE_TRIPLES,
        "source_role_types_used_as_model_features":False,
        "complete_original_source_pairs_in_model_features":False,
        "direct_node_ids_hashes_or_exact_equality_features":False,
        "source_graph_census":census,
        "source_frozen_candidate_refusals":refusals,
        "train_pair_choice_tasks":len(tasks["train"]),
        "development_pair_choice_tasks":len(tasks["dev"]),
        "terminal_pair_choice_tasks":len(tasks["test"]),
        "true_original_edge_globally_removed_before_feature_extraction":True,
        "all_original_relation_variants_reciprocals_masked":True,
        "all_negative_pairs_verified_original_nonedge":True,
        "all_candidate_degrees_matched_by_integer_bitlength":True,
        "source_candidate_graphs_node_edge_disjoint":True,
        "training":trained_record,
        "train_only_linear_baseline":linear_record,
        "development_inspection_only":results["dev"],
        "terminal_heldout":results["test"],
        "gain_disposition":(
            "LEARNED_MASKED_GRAPH_STRUCTURE_GAIN_DEMONSTRATED"
            if gain else "LEARNED_MASKED_GRAPH_STRUCTURE_GAIN_NOT_DEMONSTRATED"),
        "original_metaqa_qa_files_read":False,
        "original_metaqa_answers_scored":False,
        "freebaseqa_original_graph_qualified":False,
        "independent_novel_graph_family_qualified":False,
        "independent_scientific_firstuse":False,
        "learned_complete_graph_connectivity_proven":False,
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
    opts=p.parse_args()
    need(not opts.out.exists(),"EVIDENCE_OVERWRITE_DENIED")
    f=opts.source.lstat()
    need(stat.S_ISREG(f.st_mode) and 0<f.st_size<=source.MAX_FILE,
         "ORIGINAL_GRAPH_NOT_REGULAR_OR_OVER_BUDGET")
    content=(json.dumps(audit(opts.source.read_bytes()),sort_keys=True,
                        indent=2,ensure_ascii=True)+"\n").encode("utf-8")
    with opts.out.open("xb") as output:output.write(content)
    print("F122O_ORIGINAL_UNSEEN_SUBGRAPH_MASKED_STRUCTURAL_INFERENCE_AUDITED")
    print("F122O_NO_ROLE_EQUALITY_GOLD_EDGE_PATH_OR_INDEPENDENT_SCIENTIFIC_FIRSTUSE")

if __name__=="__main__":
    try:main()
    except (Denied,source.Denied,OSError,UnicodeError,ValueError) as exc:
        print("F122O_MASKED_SOURCE_INFERENCE_NOT_QUALIFIED",exc,file=sys.stderr)
        sys.exit(1)
