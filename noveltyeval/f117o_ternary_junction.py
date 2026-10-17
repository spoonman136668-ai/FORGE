"""F117-O source-derived three-step witness vs trained latent middle-role junction.

The graph is an OFFLINE label generator, NOT model input at inference.
A ternary signed-role predictor cannot prove actual entity variable binding.
No question/answer dataset, full graph source string, or raw role label is emitted.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import stat
import sys

import f116o_learned_composition as base

SCHEMA="forge.optimizer.f117o.public-metaqa-ternary-latent-junction.v1"
STATUS="PUBLIC_METAQA_LATENT_JUNCTION_TERNARY_LEARNER_ENGINEERING_ONLY"
GAIN="LEARNED_JUNCTION_TRANSFER_GAIN_DEMONSTRATED"
NO_GAIN="LEARNED_JUNCTION_TRANSFER_GAIN_NOT_DEMONSTRATED"
N=base.N_TYPES
D=4
EPOCHS=240
LR=0.20
L2=0.01
CHALLENGE_SIZE=256

class Denied(Exception):pass
def require(ok,reason):
    if not ok:raise Denied("F117O_JUNCTION_LEARNER_DENIED_"+reason)

def triple_bucket(types,i,j,k):
    raw=base.triple_key(types[i],types[j],types[k])
    return int.from_bytes(hashlib.sha256(raw).digest()[:8],"big")%10

def split_triples(types):
    split={0:[],1:[],2:[]}
    for i in range(N):
        for j in range(N):
            for k in range(N):
                bucket=triple_bucket(types,i,j,k)
                split[0 if bucket<=6 else (1 if bucket==7 else 2)].append((i,j,k))
    require(sum(map(len,split.values()))==N**3 and all(split.values()),
            "FROZEN_TRIPLE_HASH_SPLIT")
    return split

def challenge_candidates(types,pair_true,heldout):
    eligible=[]
    for i,j,k in heldout:
        if (i,j) in pair_true and (j,k) in pair_true:
            name=base.triple_key(types[i],types[j],types[k])
            eligible.append((hashlib.sha256(name).digest(),name,i,j,k))
    eligible.sort(key=lambda x:(x[0],x[1]))
    return [(i,j,k) for _,_,i,j,k in eligible[:CHALLENGE_SIZE]],len(eligible)

def initial_embedding(side,i,k):
    digest=hashlib.sha256(f"F117O-v1|{side}|{i}|{k}".encode("ascii")).digest()
    return (int.from_bytes(digest[:2],"big")/65535.0-0.5)*0.1

class TernaryJunctionLearner:
    def __init__(self):
        self.U=[[initial_embedding("U",i,d) for d in range(D)] for i in range(N)]
        self.M=[[initial_embedding("M",j,d) for d in range(D)] for j in range(N)]
        self.V=[[initial_embedding("V",k,d) for d in range(D)] for k in range(N)]
        self.left=[0.0]*N
        self.middle=[0.0]*N
        self.right=[0.0]*N
        self.bias=0.0

    def logit(self,i,j,k):
        u,m,v=self.U[i],self.M[j],self.V[k]
        return self.bias+self.left[i]+self.middle[j]+self.right[k]+sum(
            u[d]*m[d]+m[d]*v[d]+u[d]*m[d]*v[d] for d in range(D))

    def score(self,i,j,k):
        return base.sigmoid(self.logit(i,j,k))

    def parameters(self):
        values=[self.bias]+self.left+self.middle+self.right
        for group in (self.U,self.M,self.V):
            for row in group:values.extend(row)
        return values

    def loss(self,training):
        require(training,"EMPTY_TRAIN_SET")
        result=0.0
        for i,j,k,y in training:
            prob=self.score(i,j,k)
            result-=y*math.log(max(prob,1e-12))+(1-y)*math.log(max(1-prob,1e-12))
        return result/len(training)

    def train(self,training):
        require(training and all(len(z)==4 for z in training),"BAD_TRAINING")
        before=self.loss(training)
        init=self.parameters()
        n=len(training)
        for _ in range(EPOCHS):
            gu=[[0.0]*D for _ in range(N)]
            gm=[[0.0]*D for _ in range(N)]
            gv=[[0.0]*D for _ in range(N)]
            gl=[0.0]*N
            gmid=[0.0]*N
            gr=[0.0]*N
            gb=0.0
            for i,j,k,y in training:
                err=self.score(i,j,k)-y
                gb+=err
                gl[i]+=err
                gmid[j]+=err
                gr[k]+=err
                u,m,v=self.U[i],self.M[j],self.V[k]
                for d in range(D):
                    gu[i][d]+=err*m[d]*(1+v[d])
                    gm[j][d]+=err*(u[d]+v[d]+u[d]*v[d])
                    gv[k][d]+=err*m[d]*(1+u[d])
            self.bias-=LR*gb/n
            for role in range(N):
                self.left[role]-=LR*gl[role]/n
                self.middle[role]-=LR*gmid[role]/n
                self.right[role]-=LR*gr[role]/n
                for d in range(D):
                    self.U[role][d]-=LR*(gu[role][d]/n+L2*self.U[role][d])
                    self.M[role][d]-=LR*(gm[role][d]/n+L2*self.M[role][d])
                    self.V[role][d]-=LR*(gv[role][d]/n+L2*self.V[role][d])
        after=self.loss(training)
        final=self.parameters()
        drift=math.sqrt(sum((x-y)**2 for x,y in zip(init,final)))
        require(drift>1e-9 and after<before,
                "GRADIENT_LEARNING_NOT_VERIFIED")
        digest=hashlib.sha256(",".join(f"{v:.15g}" for v in final).encode("ascii")).hexdigest()
        return {"training_epochs":EPOCHS,"trainable_parameters":len(final),
                "train_logloss_before":round(before,8),
                "train_logloss_after":round(after,8),
                "parameter_movement_l2":round(drift,8),
                "trained_parameter_sha256":digest}

def triple_marginal(train):
    count=[Counter(),Counter(),Counter()]
    positives=[Counter(),Counter(),Counter()]
    for i,j,k,y in train:
        for pos,role in enumerate((i,j,k)):
            count[pos][role]+=1
            positives[pos][role]+=y
    def score(i,j,k):
        return sum((positives[p][r]+1)/(count[p][r]+2)
                   for p,r in enumerate((i,j,k)))/3
    return score

def exact_witness_labels(edges,type_lookup):
    """Source-only diagnostic for synthetic graphs (not model inference)."""
    from collections import defaultdict
    out=defaultdict(set)
    arcs=[]
    for src,role,dst in edges:
        forward=type_lookup[(role,"F")]
        reverse=type_lookup[(role,"R")]
        out[src].add(forward)
        out[dst].add(reverse)
        arcs.append((src,forward,dst))
        arcs.append((dst,reverse,src))
    true_pairs=set()
    for present in out.values():
        for incoming_inverse in present:
            for following in present:
                true_pairs.add((incoming_inverse^1,following))
    true_triples=set()
    for src,middle,dst in arcs:
        for back in out[src]:
            for nxt in out[dst]:
                true_triples.add((back^1,middle,nxt))
    return true_pairs,true_triples

def evaluate(types,pair_true,triple_true):
    require(len(types)==N and
            all(len(s)==2 for s in types),"SIGNED_ROLE_DENOMINATOR")
    split=split_triples(types)
    labeled=lambda points:[(i,j,k,int((i,j,k) in triple_true))
                           for i,j,k in points]
    train=labeled(split[0])
    dev=labeled(split[1])
    terminal=labeled(split[2])
    learner=TernaryJunctionLearner()
    learned_training=learner.train(train)
    train_majority=int(sum(y for _,_,_,y in train)>len(train)/2)
    marginal=triple_marginal(train)
    # F116's pair-only control is trained on ONLY its earlier 2-step
    # TRAIN hash and no 3-step labels, not DEV or terminal data.
    pair_sections=base.split_pairs(types)
    pair_train=base.labels_for(pair_sections[0],pair_true)
    pair_model=base.Learner()
    pair_report=pair_model.train(pair_train)
    require(pair_report["training_epochs"]==200,
            "FROZEN_F116_PAIR_ONLY_CONTROL")
    controls={
        "learned_ternary":lambda i,j,k:learner.score(i,j,k),
        "train_majority":lambda i,j,k:float(train_majority),
        "train_only_positional_marginal":marginal,
        "f116_train_only_pairwise_min":lambda i,j,k:min(
            pair_model.score(i,j),pair_model.score(j,k)),
    }
    challenge,pool=challenge_candidates(types,pair_true,split[2])
    require(challenge,"MISSING_PAIR_COMPATIBLE_UNSEEN_STRUCTURES")
    def measure(points):
        y=[int((i,j,k) in triple_true) for i,j,k in points]
        return {name:base.performance(y,[
            int(sc(i,j,k)>=0.5) for i,j,k in points])
            for name,sc in controls.items()}
    heldout_metrics=measure(split[2])
    challenge_metrics=measure(challenge)
    dev_probe=base.performance(
        [y for _,_,_,y in dev],
        [int(learner.score(i,j,k)>=0.5) for i,j,k,y in dev])
    def ahead(metrics):
        current=metrics["learned_ternary"]
        competitors=[metrics[key] for key in controls if key!="learned_ternary"]
        if not current["both_classes_present"] or not all(
            c["both_classes_present"] for c in competitors):
            return False
        return current["balanced_accuracy"]>=max(
            c["balanced_accuracy"] for c in competitors)+0.05
    gain=ahead(heldout_metrics) and ahead(challenge_metrics)
    # Pairwise true-and-true always predicts 1 on this frozen challenge;
    # count its false positive witness failures without leaking labels.
    absent_witness=sum((i,j,k) not in triple_true for i,j,k in challenge)
    return {
        "source_3hop_role_type_population":N**3,
        "train":len(train),"development_inspection_only":len(dev),
        "terminal_test":len(terminal),
        "train_positive":sum(y for _,_,_,y in train),
        "train_negative":sum(1-y for _,_,_,y in train),
        "training":learned_training,
        "pair_control_training_only":pair_report,
        "dev_learner_report_not_used_for_selection":dev_probe,
        "terminal_holdout":heldout_metrics,
        "binding_challenge_source_pair_pool":pool,
        "binding_challenge_n":len(challenge),
        "binding_challenge_heldout":challenge_metrics,
        "binding_challenge_exact_join_negative":absent_witness,
        "pairwise_positive_does_not_guarantee_shared_node":bool(absent_witness),
        "gain_disposition":GAIN if gain else NO_GAIN,
        "train_only_updates":True,
        "dev_test_labels_in_training":False,
        "learned_latent_junction_not_entity_variable_binding":True,
        "graph_witness_oracle_separate_from_model_features":True,
    }

def audit(raw):
    require(base.source_digest(raw),"SOURCE_SHA256_GIT_BLOB_MISMATCH")
    triples,roles=base.load_original_triples(raw)
    types,pairs,threes=base.make_graph_labels(triples,roles)
    require(len(types)==N and 0<len(pairs)<=324 and
            0<len(threes)<=N**3,"AUTHENTIC_TYPED_GRAPH_SOURCE")
    outcome=evaluate(types,pairs,threes)
    return {
        "schema":SCHEMA,"status":STATUS,
        "source_repository":"tiantiangao7/kalm-qa",
        "source_commit":base.UPSTREAM,
        "original_graph_git_blob":base.BLOB,
        "original_graph_sha256":base.SOURCE_SHA,
        "original_source_rows":base.MAX_SOURCE_ROWS,
        "original_unique_triples":base.UNIQUE_TRIPLES,
        "exact_oracle_true_2step_role_pairs":len(pairs),
        "exact_oracle_true_3step_role_triples":len(threes),
        "learning":outcome,
        "gold_metaqa_question_answers_accessed":False,
        "original_freebaseqa_graph_qualified":False,
        "independent_new_task_family_generalization_proven":False,
        "actual_entity_variable_binding_learned":False,
        "independent_scientific_firstuse":False,
        "accepted_science":False,
        "accepted_ref_mutation":False,
        "dream_pareto_promotion":False,
        "thetaevolve_accepted_training":False,
        "scientific_dispatch":False,
        "model_calls":0,"codex_calls":0,"cloudflare_writes":0,
    }

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--source-raw",type=Path,required=True)
    parser.add_argument("--out",type=Path,required=True)
    opts=parser.parse_args()
    require(not opts.out.exists(),"OVERWRITE_OF_EVIDENCE_DENIED")
    st=opts.source_raw.lstat()
    require(stat.S_ISREG(st.st_mode) and 0<st.st_size<=base.MAX_FILE,
            "SOURCE_NOT_REGULAR_OR_OVER_BUDGET")
    result=audit(opts.source_raw.read_bytes())
    encoded=(json.dumps(result,indent=2,sort_keys=True,ensure_ascii=True)+"\n").encode()
    with opts.out.open("xb") as dest:dest.write(encoded)
    print("F117O_REAL_TRAINING_AND_EXACT_GRAPH_JUNCTION_CHALLENGE_MEASURED")
    print("F117O_NO_QA_SCORE_OR_INDEPENDENT_SCIENCE_OR_OPTIMIZER_PROMOTION")

if __name__=="__main__":
    try:main()
    except (Denied,base.Denied,ValueError,UnicodeError,OSError) as exc:
        print("F117O_TERNARY_LEARNING_NOT_QUALIFIED:",exc,file=sys.stderr)
        sys.exit(1)
