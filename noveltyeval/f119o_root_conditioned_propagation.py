"""F119-O: learned query-conditioned edge gates over real joined graph state.

Physical graph node identities connect two signed-role edges, but are NEVER
encoded as ML features. Offline query-time source adjacency is given to all
methods, so this cannot prove independently learned graph connectivity.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import stat
import sys

import f116o_learned_composition as source

SCHEMA="forge.optimizer.f119o.authentic-root-conditioned-typed-state.v1"
STATUS="PUBLIC_METAQA_LEARNED_ROLE_GATE_OVER_SYMBOLIC_CONNECTED_GRAPH_ENGINEERING_ONLY"
N=18
D=3
EPOCHS=120
LR=0.35
L2=0.005
MAX_FIRST=128
MAX_PATHS=4096
MAX_TARGETS=512
TRAIN=64
DEV=24
TEST=48

class Denied(Exception):pass
def require(ok,reason):
    if not ok:raise Denied("F119O_TYPED_SOURCE_GRAPH_DENIED_"+reason)

def h(value:str)->bytes:
    return hashlib.sha256(value.encode("utf-8","strict")).digest()

def order_hash(root:str)->bytes:
    return hashlib.sha256(b"F119O-order|"+root.encode("utf-8","strict")).digest()

def split(root:str)->str:
    v=int.from_bytes(h(root)[:8],"big")%10
    return "train" if v<=6 else ("dev" if v==7 else "test")

def adjacency(triples,roles):
    type_ids={(role,d):i for i,(role,d) in
              enumerate(source.role_types(roles))}
    out=defaultdict(list)
    for a,r,b in triples:
        if a==b:continue
        fact=(a,r,b)
        out[a].append((b,type_ids[(r,"F")],fact))
        out[b].append((a,type_ids[(r,"R")],fact))
    for root in out:
        out[root].sort(key=lambda x:(x[1],x[0],x[2]))
    return out,type_ids

def full_two_step_histogram(root,out):
    """Original physical F/R arcs; no original edge repeated by instant inverse."""
    first=out.get(root,())
    if not first or len(first)>MAX_FIRST:return None
    count=0
    histogram=defaultdict(Counter)
    for intermediate,role_one,physical_one in first:
        next_arcs=out.get(intermediate,())
        count+=len(next_arcs)
        if count>MAX_PATHS:return None
        for target,role_two,physical_two in next_arcs:
            if target==root or physical_one==physical_two:continue
            histogram[target][(role_one,role_two)]+=1
            if len(histogram)>MAX_TARGETS:return None
    return histogram

def freeze_query(root,hist):
    if len(hist)<2:return None
    # Choose the earliest exact ordered signed-role pair supported anywhere,
    # then positive/negative source terminals lexicographically.
    observed=sorted({pair for counts in hist.values() for pair in counts})
    for query in observed:
        positives=sorted(t for t,c in hist.items() if c.get(query,0)>0)
        negatives=sorted(t for t,c in hist.items() if c.get(query,0)==0
                         and sum(c.values())>0)
        if positives and negatives:
            pos=positives[0]
            neg=negatives[0]
            require(pos!=neg and sum(hist[pos].values())>0 and
                    sum(hist[neg].values())>0,"BOTH_CANDIDATES_MUST_BE_REACHABLE")
            first_positive=(order_hash(root)[0]&1)==0
            first,second=(pos,neg) if first_positive else (neg,pos)
            return (root,query,dict(hist[first]),dict(hist[second]),
                    int(first_positive))
    return None

def select_from_source(triples,roles):
    out,_=adjacency(triples,roles)
    roots=sorted(out,key=lambda name:(h(name),name.encode("utf-8","strict")))
    sizes={"train":TRAIN,"dev":DEV,"test":TEST}
    groups={k:[] for k in sizes}
    eligible={"train":0,"dev":0,"test":0}
    oversize=0
    for root in roots:
        section=split(root)
        if len(groups[section])==sizes[section]:continue
        hist=full_two_step_histogram(root,out)
        if hist is None:
            oversize+=1
            continue
        task=freeze_query(root,hist)
        if task is None:continue
        eligible[section]+=1
        groups[section].append(task)
        if all(len(groups[k])==v for k,v in sizes.items()):
            break
    require(all(len(groups[k])==v for k,v in sizes.items()),
            "FROZEN_REAL_ROOT_COHORT_UNDERPOPULATED")
    roots_by_group={k:{z[0] for z in g} for k,g in groups.items()}
    require(not (roots_by_group["train"]&roots_by_group["dev"]) and
            not (roots_by_group["train"]&roots_by_group["test"]) and
            not (roots_by_group["dev"]&roots_by_group["test"]),
            "ROOT_SPLIT_INDEPENDENCE")
    return groups,{"eligible_collected":eligible,
                   "overbudget_or_empty_root_skipped":oversize,
                   "whole_source_unique_roots":len(out)}

def initial(side,i,d):
    digest=hashlib.sha256(f"F119O-v1|{side}|{i}|{d}".encode("ascii")).digest()
    return (int.from_bytes(digest[:2],"big")/65535.0-0.5)*0.10

def hist_mass(hist,gates,q1,q2):
    return sum(count*gates[q1][a]*gates[q2][b]
               for (a,b),count in hist.items())

def softplus(x):
    return max(0.0,x)+math.log1p(math.exp(-abs(x)))

class LearnedTypedState:
    def __init__(self):
        self.Q=[[initial("Q",i,d) for d in range(D)] for i in range(N)]
        self.E=[[initial("E",i,d) for d in range(D)] for i in range(N)]
        self.bias=0.0

    def params(self):
        vals=[self.bias]
        for rows in (self.Q,self.E):
            for row in rows:vals.extend(row)
        return vals

    def gate(self):
        return [[source.sigmoid(self.bias+
                 sum(self.Q[q][d]*self.E[r][d] for d in range(D)))
                 for r in range(N)] for q in range(N)]

    def scores(self,task,gates=None):
        _,(q1,q2),first,second,_=task
        if gates is None:gates=self.gate()
        return (math.log1p(hist_mass(first,gates,q1,q2)),
                math.log1p(hist_mass(second,gates,q1,q2)))

    def train_loss(self,tasks):
        require(bool(tasks),"EMPTY_TRAINING")
        gates=self.gate()
        total=0.0
        for task in tasks:
            s0,s1=self.scores(task,gates)
            positive=task[4]
            total+=softplus((s1-s0) if positive==1 else (s0-s1))
        return total/len(tasks)

    def train(self,tasks):
        require(bool(tasks),"EMPTY_FROZEN_TRAIN_GROUP")
        before=self.train_loss(tasks)
        start=self.params()
        n=len(tasks)
        for _ in range(EPOCHS):
            gates=self.gate()
            gate_grads=[[0.0]*N for _ in range(N)]
            for task in tasks:
                _,(q1,q2),first,second,first_positive=task
                pos=first if first_positive else second
                neg=second if first_positive else first
                mass_pos=hist_mass(pos,gates,q1,q2)
                mass_neg=hist_mass(neg,gates,q1,q2)
                delta=source.sigmoid(math.log1p(mass_pos)-math.log1p(mass_neg))-1.0
                for hist,coef in ((pos,delta/(1+mass_pos)),
                                  (neg,-delta/(1+mass_neg))):
                    for (r1,r2),count in hist.items():
                        gate_grads[q1][r1]+=coef*count*gates[q2][r2]
                        gate_grads[q2][r2]+=coef*count*gates[q1][r1]
            gQ=[[0.0]*D for _ in range(N)]
            gE=[[0.0]*D for _ in range(N)]
            gb=0.0
            for q in range(N):
                for r in range(N):
                    slope=gate_grads[q][r]*gates[q][r]*(1-gates[q][r])
                    gb+=slope
                    for d in range(D):
                        gQ[q][d]+=slope*self.E[r][d]
                        gE[r][d]+=slope*self.Q[q][d]
            self.bias-=LR*gb/n
            for i in range(N):
                for d in range(D):
                    self.Q[i][d]-=LR*(gQ[i][d]/n+L2*self.Q[i][d])
                    self.E[i][d]-=LR*(gE[i][d]/n+L2*self.E[i][d])
        final_loss=self.train_loss(tasks)
        values=self.params()
        change=math.sqrt(sum((a-b)**2 for a,b in zip(start,values)))
        require(change>1e-9 and final_loss<before,"NO_ACTUAL_GRADIENT_PROGRESS")
        param_digest=hashlib.sha256(",".join(f"{v:.8f}" for v in values).encode("ascii")).hexdigest()
        return {"training_epochs":EPOCHS,"trainable_parameters":len(values),
                "train_logloss_initial":round(before,8),
                "train_logloss_final":round(final_loss,8),
                "parameter_l2_movement":round(change,8),
                "learned_parameter_sha256":param_digest}

def predict(scores):
    return 0 if scores[0]>=scores[1] else 1

def evaluate(tasks,method):
    labels=[int(t[4]==1) for t in tasks]
    predicted=[int(method(t)==0) for t in tasks]
    return source.performance(labels,predicted)

def audit(raw):
    require(source.source_digest(raw),"FULL_SOURCE_GIT_BLOB_SHA256_DRIFT")
    triples,roles=source.load_original_triples(raw)
    require(len(roles)==9 and len(triples)==133582,
            "COMPLETE_ORIGINAL_KB_DENOMINATOR")
    groups,coverage=select_from_source(triples,roles)
    model=LearnedTypedState()
    init_gates=model.gate()
    def model_predict(task):return predict(model.scores(task))
    def untrained_predict(task):
        return predict(model.scores(task,init_gates))
    def uniform_predict(task):
        return predict((sum(task[2].values()),sum(task[3].values())))
    def exact_predict(task):
        q=task[1]
        return predict((task[2].get(q,0),task[3].get(q,0)))
    def constant_predict(task):return 0
    fitted=model.train(groups["train"])
    controls={
        "learned_query_conditioned_role_gate":model_predict,
        "constant_candidate_zero":constant_predict,
        "uniform_untyped_connected_twohop":uniform_predict,
        "frozen_untrained_role_gate":untrained_predict,
        "symbolic_exact_typed_graph_traversal":exact_predict,
    }
    report={splitname:{name:evaluate(tasks,pred)
                       for name,pred in controls.items()}
            for splitname,tasks in groups.items() if splitname in ("dev","test")}
    for splitname in ("dev","test"):
        symbolic=report[splitname]["symbolic_exact_typed_graph_traversal"]
        require(symbolic["both_classes_present"] and
                symbolic["tp"]+symbolic["tn"]==symbolic["n"],
                "SOURCE_GRAPH_ORACLE_MUST_FIND_EXACT_VALID_PATH")
    hold=report["test"]
    learned=hold["learned_query_conditioned_role_gate"]
    competitors=[v for key,v in hold.items() if
                 key not in ("learned_query_conditioned_role_gate",
                             "symbolic_exact_typed_graph_traversal")]
    gain=learned["both_classes_present"] and all(
        v["balanced_accuracy"] is not None for v in competitors) and
        learned["balanced_accuracy"]>=max(
            v["balanced_accuracy"] for v in competitors)+0.05
    return {
        "schema":SCHEMA,"status":STATUS,
        "source_repository":"tiantiangao7/kalm-qa",
        "source_commit":source.UPSTREAM,
        "source_git_blob":source.BLOB,
        "source_sha256":source.SOURCE_SHA,
        "source_rows":source.MAX_SOURCE_ROWS,
        "source_distinct_triples":source.UNIQUE_TRIPLES,
        "source_signed_roles":N,
        "source_root_selection_census":coverage,
        "train_distinct_roots":len(groups["train"]),
        "dev_distinct_roots":len(groups["dev"]),
        "terminal_distinct_roots":len(groups["test"]),
        "root_split_disjoint":True,
        "two_step_actual_shared_intermediate_required":True,
        "negative_candidate_also_has_real_two_step_paths":True,
        "role_mismatch_is_not_candidate_identity_equality_feature":True,
        "training":fitted,
        "development_inspection_only":report["dev"],
        "terminal_heldout":hold,
        "gain_disposition":("LEARNED_ROLE_GATE_TRANSFER_GAIN_DEMONSTRATED" if gain
                            else "LEARNED_ROLE_GATE_TRANSFER_GAIN_NOT_DEMONSTRATED"),
        "structural_graph_join_symbolic_not_learned":True,
        "root_heldout_same_graph_transductive":True,
        "original_metaqa_qa_files_read":False,
        "original_metaqa_answers_scored":False,
        "original_freebaseqa_graph_qualified":False,
        "learned_entity_variable_binding_proven":False,
        "independent_scientific_firstuse":False,
        "accepted_science":False,
        "accepted_ref_mutation":False,
        "dream_pareto_promotion":False,
        "thetaevolve_accepted_training":False,
        "scientific_dispatch":False,
        "model_calls":0,"codex_calls":0,"cloudflare_writes":0,
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source-raw",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    opt=p.parse_args()
    require(not opt.out.exists(),"NEVER_OVERWRITE_EVIDENCE")
    st=opt.source_raw.lstat()
    require(stat.S_ISREG(st.st_mode) and 0<st.st_size<=source.MAX_FILE,
            "AUTHENTIC_SOURCE_FILE_BUDGET")
    result=audit(opt.source_raw.read_bytes())
    encoded=(json.dumps(result,sort_keys=True,indent=2,ensure_ascii=True)+"\n").encode()
    with opt.out.open("xb") as stream:stream.write(encoded)
    print("F119O_ORIGINAL_METAQA_ROOT_STATE_PROPAGATION_AND_TRAINED_GATE_AUDITED")
    print("F119O_SYMBOLIC_GRAPH_JOINS_GIVEN_NOT_LEARNED_INDEPENDENT_SCIENCE_DENIED")

if __name__=="__main__":
    try:main()
    except (Denied,source.Denied,ValueError,OSError,UnicodeError) as ex:
        print("F119O_ORIGINAL_GRAPH_SOURCE_OR_ROLE_LEARNING_DENIED",ex,file=sys.stderr)
        sys.exit(1)
