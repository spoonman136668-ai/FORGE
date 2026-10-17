"""F116-O trained low-rank signed-relation composition, graph-only public development.

Actual optimized numeric parameters, frozen training-only gradient updates,
held-out *role-pair* splits; no original MetaQA question-answer bytes and no
independent scientific claim. Source-derived path-existence oracle constructs
labels offline; never offered as a feature to the learner.
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

UPSTREAM="826ee617e4da5b087584b0e03c70fe76642c6188"
BLOB="a43fa7ca5e6894236556f2984764070c4ca5562b"
SOURCE_SHA="9b4d3b3066266075ad1577b4beed68e6e112e76e1a29ed2cb00a2896d2b792af"
SCHEMA="forge.optimizer.f116o.public-metaqa-trained-role-composition.v1"
STATUS="PUBLIC_METAQA_SELF_SUPERVISED_ROLE_COMPATIBILITY_LEARNER_ENGINEERING_ONLY"
N_ROLES=9
N_TYPES=18
EMBED=4
EPOCHS=200
LR=0.12
L2=0.01
MAX_FILE=7_000_000
MAX_SOURCE_ROWS=134741
UNIQUE_TRIPLES=133582
MAX_3HOP=256
DELIM=b"\x1f"
PAIR_SEP=b"\x1e"
ROLE_SEP=b"\x1d"

class Denied(Exception):pass
def require(ok:bool,reason:str)->None:
    if not ok:raise Denied("F116O_SOURCE_OR_LEARNER_DENIED_"+reason)

def source_digest(raw:bytes)->bool:
    h=hashlib.sha1(b"blob "+str(len(raw)).encode("ascii")+b"\x00"+raw).hexdigest()
    return h==BLOB and hashlib.sha256(raw).hexdigest()==SOURCE_SHA

def load_original_triples(raw:bytes):
    require(0<len(raw)<=MAX_FILE and raw.endswith(b"\n"),
            "COMPLETE_BOUNDED_ORIGINAL_SOURCE")
    lines=raw[:-1].split(b"\n")
    require(len(lines)==MAX_SOURCE_ROWS,"ORIGINAL_SOURCE_DENOMINATOR")
    seen=set()
    roles=set()
    entities=set()
    for line in lines:
        fields=line.split(b"|")
        require(len(fields)==3 and all(0<len(f)<=512 for f in fields) and
                all(b"\x00" not in f and b"\r" not in f for f in fields),
                "ORIGINAL_KB_THREE_FIELDS")
        a,r,b=[v.decode("utf-8","strict") for v in fields]
        seen.add((a,r,b))
        roles.add(r)
        entities.add(a)
        entities.add(b)
    require(len(seen)==UNIQUE_TRIPLES and len(roles)==N_ROLES and
            len(entities)==43234,"COMPLETE_ORIGINAL_KB_UNIQUE_COUNTS")
    return sorted(seen),sorted(roles)

def role_types(roles:list[str]):
    # Signed source role types: (role text, direction symbol).
    return [(r,d) for r in roles for d in ("F","R")]

def role_key(role:tuple[str,str])->bytes:
    return role[0].encode("utf-8")+DELIM+role[1].encode("ascii")

def pair_key(left,right)->bytes:
    return role_key(left)+PAIR_SEP+role_key(right)

def pair_split(left,right)->int:
    digest=hashlib.sha256(pair_key(left,right)).digest()
    return int.from_bytes(digest[:8],"big")%10

def triple_key(a,b,c)->bytes:
    return role_key(a)+ROLE_SEP+role_key(b)+ROLE_SEP+role_key(c)

def make_graph_labels(triples,roles):
    type_list=role_types(roles)
    lookup={t:i for i,t in enumerate(type_list)}
    # Every unique source triple supplies one F and one R *typed* arc.
    outgoing=defaultdict(set)
    directed=[]
    for a,r,b in triples:
        f=lookup[(r,"F")]
        rev=lookup[(r,"R")]
        outgoing[a].add(f)
        outgoing[b].add(rev)
        directed.append((a,f,b))
        directed.append((b,rev,a))
    require(len(directed)==2*UNIQUE_TRIPLES,"DIRECTED_ARC_DENOMINATOR")
    # Existence of 2-hop: a type arriving at junction -> leaving type.
    pair_true=set()
    for present in outgoing.values():
        for outward in present:
            incoming=outward^1
            for following in present:
                pair_true.add((incoming,following))
    # Existence of actual 3-hop: a typed edge connects two junctions.
    triple_true=set()
    for src,middle,dst in directed:
        for prev in outgoing[src]:
            incoming=prev^1
            for next_type in outgoing[dst]:
                triple_true.add((incoming,middle,next_type))
    return type_list,pair_true,triple_true

def split_pairs(types):
    split={0:[],1:[],2:[]}
    for i,left in enumerate(types):
        for j,right in enumerate(types):
            b=pair_split(left,right)
            section=0 if b<=6 else (1 if b==7 else 2)
            split[section].append((i,j))
    require(sum(map(len,split.values()))==324 and all(split.values()),
            "DETERMINISTIC_FROZEN_ROLE_SPLIT")
    return split

def sigmoid(x:float)->float:
    x=max(-40.0,min(40.0,x))
    return 1.0/(1.0+math.exp(-x))

def initial_embedding(side:str,i:int,k:int)->float:
    d=hashlib.sha256(f"F116O-v1|{side}|{i}|{k}".encode()).digest()
    return (int.from_bytes(d[:2],"big")/65535.0-0.5)*0.1

class Learner:
    def __init__(self):
        self.left=[[initial_embedding("L",i,k) for k in range(EMBED)]
                   for i in range(N_TYPES)]
        self.right=[[initial_embedding("R",i,k) for k in range(EMBED)]
                    for i in range(N_TYPES)]
        self.a=[0.0]*N_TYPES
        self.b=[0.0]*N_TYPES
        self.bias=0.0

    def score(self,i:int,j:int)->float:
        return sigmoid(self.bias+self.a[i]+self.b[j]+
                       sum(self.left[i][k]*self.right[j][k] for k in range(EMBED)))

    def snapshot(self):
        vals=[self.bias]+self.a+self.b
        for row in self.left:vals.extend(row)
        for row in self.right:vals.extend(row)
        return vals

    def loss(self,examples):
        require(len(examples)>0,"EMPTY_TRAINING")
        return sum(-(y*math.log(max(self.score(i,j),1e-12))+
                     (1-y)*math.log(max(1-self.score(i,j),1e-12)))
                   for i,j,y in examples)/len(examples)

    def train(self,examples):
        begin=self.loss(examples)
        initial=self.snapshot()
        n=len(examples)
        for _ in range(EPOCHS):
            left_grad=[[0.0]*EMBED for _ in range(N_TYPES)]
            right_grad=[[0.0]*EMBED for _ in range(N_TYPES)]
            a_grad=[0.0]*N_TYPES
            b_grad=[0.0]*N_TYPES
            global_grad=0.0
            for i,j,y in examples:
                delta=self.score(i,j)-y
                a_grad[i]+=delta
                b_grad[j]+=delta
                global_grad+=delta
                for k in range(EMBED):
                    left_grad[i][k]+=delta*self.right[j][k]
                    right_grad[j][k]+=delta*self.left[i][k]
            self.bias-=LR*global_grad/n
            for i in range(N_TYPES):
                self.a[i]-=LR*a_grad[i]/n
                self.b[i]-=LR*b_grad[i]/n
                for k in range(EMBED):
                    self.left[i][k]-=LR*(left_grad[i][k]/n+L2*self.left[i][k])
                    self.right[i][k]-=LR*(right_grad[i][k]/n+L2*self.right[i][k])
        finish=self.loss(examples)
        dist=math.sqrt(sum((x-y)**2 for x,y in zip(initial,self.snapshot())))
        require(dist>1e-9 and finish<begin,"NO_ACTUAL_LOSS_IMPROVEMENT")
        data=",".join(f"{v:.15g}" for v in self.snapshot()).encode("ascii")
        return {"train_logloss_before":round(begin,8),
                "train_logloss_after":round(finish,8),
                "parameter_change_l2":round(dist,8),
                "parameter_vector_sha256":hashlib.sha256(data).hexdigest(),
                "trainable_parameters":len(self.snapshot()),
                "training_epochs":EPOCHS}

def labels_for(points,true):
    return [(i,j,int((i,j) in true)) for i,j in points]

def performance(y_true,y_pred):
    require(len(y_true)==len(y_pred)>0,"EVALUATION_DENOMINATOR")
    tp=sum(y==1 and p==1 for y,p in zip(y_true,y_pred))
    tn=sum(y==0 and p==0 for y,p in zip(y_true,y_pred))
    fp=sum(y==0 and p==1 for y,p in zip(y_true,y_pred))
    fn=sum(y==1 and p==0 for y,p in zip(y_true,y_pred))
    positive=tp+fn
    negative=tn+fp
    ba=(0.5*(tp/positive+tn/negative)) if positive and negative else None
    return {"n":len(y_true),"positive":positive,"negative":negative,
            "tp":tp,"tn":tn,"fp":fp,"fn":fn,
            "accuracy":round((tp+tn)/len(y_true),6),
            "balanced_accuracy":None if ba is None else round(ba,6),
            "both_classes_present":bool(positive and negative)}

def baseline_marginals(train):
    # Count training-only role-conditioned positive rates with Laplace +1/+2.
    lc=Counter()
    rc=Counter()
    lp=Counter()
    rp=Counter()
    for i,j,y in train:
        lc[i]+=1;rc[j]+=1;lp[i]+=y;rp[j]+=y
    def score(i,j):
        left=(lp[i]+1)/(lc[i]+2)
        right=(rp[j]+1)/(rc[j]+2)
        return (left+right)/2
    return score

def choose_triples(types,truth):
    # Terminal 3-hop diagnostic: neither adjacent role-pair seen in training.
    pool=[]
    for i,a in enumerate(types):
        for j,b in enumerate(types):
            if pair_split(a,b)<8:continue
            for k,c in enumerate(types):
                if pair_split(b,c)<8:continue
                raw=triple_key(a,b,c)
                pool.append((hashlib.sha256(raw).digest(),raw,i,j,k))
    pool.sort(key=lambda z:(z[0],z[1]))
    chosen=[(i,j,k) for _,_,i,j,k in pool[:MAX_3HOP]]
    require(len(chosen)>0,"NO_UNSEEN_PAIR_COMPOSITION_POOL")
    return chosen

def fit_and_score(types,pair_true,triple_true):
    sections=split_pairs(types)
    train=labels_for(sections[0],pair_true)
    # Development is measured but never used for hyperparameters/model updates.
    dev=labels_for(sections[1],pair_true)
    test=labels_for(sections[2],pair_true)
    require(0<len(train)<324 and all(y in (0,1) for _,_,y in train),
            "INVALID_FROZEN_TRAINING_PAIRS")
    model=Learner()
    trained=model.train(train)
    maj=int(sum(y for _,_,y in train)>len(train)/2)
    marginal=baseline_marginals(train)
    ty=[y for _,_,y in test]
    learned=performance(ty,[int(model.score(i,j)>=0.5) for i,j,y in test])
    majority=performance(ty,[maj]*len(test))
    marg=performance(ty,[int(marginal(i,j)>=0.5) for i,j,y in test])
    d_y=[y for _,_,y in dev]
    dev_report=performance(d_y,[int(model.score(i,j)>=0.5) for i,j,y in dev])
    triples=choose_triples(types,triple_true)
    triple_y=[int((i,j,k) in triple_true) for i,j,k in triples]
    triple_scores=[min(model.score(i,j),model.score(j,k)) for i,j,k in triples]
    transfer=performance(triple_y,[int(x>=0.5) for x in triple_scores])
    best_baseline=max(v["balanced_accuracy"] for v in (majority,marg)
                      if v["balanced_accuracy"] is not None) if learned["both_classes_present"] else None
    gain=(learned["balanced_accuracy"] is not None and
          transfer["both_classes_present"] and
          best_baseline is not None and
          learned["balanced_accuracy"]>=best_baseline+0.05)
    return {
        "pair_population":324,
        "split_train":len(train),"split_dev":len(dev),"split_test":len(test),
        "train_positive":sum(y for _,_,y in train),
        "train_negative":sum(1-y for _,_,y in train),
        "development_inspection_only":dev_report,
        "terminal_heldout_learned":learned,
        "terminal_heldout_majority_control":majority,
        "terminal_heldout_marginal_control":marg,
        "three_step_both_pairs_unseen":transfer,
        "three_step_source_population":N_TYPES**3,
        "model":trained,
        "gain_disposition":("LEARNED_TRANSFER_GAIN_DEMONSTRATED" if gain else
                            "LEARNED_TRANSFER_GAIN_NOT_DEMONSTRATED"),
        "source_derived_labels_not_original_qa":True,
        "training_only_gradient_updates":True,
        "dev_or_test_in_model_selection":False,
    }

def audit(raw:bytes):
    require(source_digest(raw),"ORIGINAL_GIT_SOURCE_SHA1_OR_SHA256")
    triples,roles=load_original_triples(raw)
    types,pair_true,triple_true=make_graph_labels(triples,roles)
    require(len(types)==N_TYPES and 0<len(pair_true)<=324
            and 0<len(triple_true)<=N_TYPES**3,
            "COMPLETE_GRAPH_TYPED_PATH_POPULATIONS")
    scored=fit_and_score(types,pair_true,triple_true)
    return {
        "schema":SCHEMA,
        "status":STATUS,
        "source_repository":"tiantiangao7/kalm-qa",
        "source_commit":UPSTREAM,
        "original_graph_git_blob":BLOB,
        "original_graph_sha256":SOURCE_SHA,
        "full_original_source_rows":MAX_SOURCE_ROWS,
        "unique_source_triples":UNIQUE_TRIPLES,
        "source_roles":N_ROLES,
        "signed_roles":N_TYPES,
        "whole_graph_true_2step_types":len(pair_true),
        "whole_graph_true_3step_types":len(triple_true),
        "learning":scored,
        "original_metaqa_qa_data_read":False,
        "gold_question_answer_accuracy_computed":False,
        "original_freebase_graph_qualified":False,
        "neural_task_family_generalization_qualified":False,
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
    args=p.parse_args()
    require(not args.out.exists(),"NEW_OUTPUT_ONLY")
    st=args.source_raw.lstat()
    require(stat.S_ISREG(st.st_mode) and 0<st.st_size<=MAX_FILE,
            "REGULAR_SOURCE_AND_BUDGET")
    raw=args.source_raw.read_bytes()
    data=audit(raw)
    out=(json.dumps(data,sort_keys=True,indent=2,ensure_ascii=True)+"\n").encode()
    with args.out.open("xb") as stream:stream.write(out)
    print("F116O_AUTHENTIC_GRAPH_LEARNED_SIGNED_ROLE_PARAMETERS_AND_HOLDOUT_AUDITED")
    print("F116O_TRAINING_NOT_INDEPENDENT_SCIENCE_NO_QA_LABELS_OR_OPTIMIZER_PROMOTION")

if __name__=="__main__":
    try:main()
    except (Denied,OSError,UnicodeError,ValueError,KeyError) as exc:
        print("F116O_LEARNED_COMPOSITION_QUALIFICATION_DENIED:",exc,file=sys.stderr)
        sys.exit(1)
