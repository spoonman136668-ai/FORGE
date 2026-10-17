"""F117: frozen PUBLIC relational-context sensor calibration and acquisition.

Trains ten logistic parameters ONLY on preregistered TRAIN sources. Out-of-source
GUARD transformations test transfer of an ENGINEERED role-equality feature:
this is not unrestricted representation learning or accepted original science.
"""
from __future__ import annotations
from collections import Counter
from dataclasses import dataclass
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import random
import re

import f116_learned_query_value as parent

ROOT=Path(__file__).resolve().parents[1]
FREEZE=ROOT/"reference/research-intake/f117-relational-context-freeze.json"
FREEZE_BLOB="15f41c6c3b487416fad9e391aa070fbe4f372fa0"
PARENT_SOURCE_BLOB="b324a7478f3d0cae53fc192e31473b8159b6f3aa"
PARENT_HEAD="f0c22051203880155e1340dbbcdde4ec7803605a"
SCHEMA="forge.autonomy.f117.relational-context-reliability-public-development.v1"
SHA40=re.compile(r"^[0-9a-f]{40}$")
SEEDS=((78000,79023),(80000,80511),(81000,81511),
       (82000,82511),(83000,83511))
CHANCE_MATCH=(.84,.88,.94,.97)
CHANCE_MISMATCH=(.52,.59,.67,.74)
COSTS=(.05,.20,.50,.85)
FAMILIES=("train-graph","reordered-node-identifiers","aliased-role-labels",
          "reversed-storage-order","unrelated-distractor-edges")
ARMS=("learned_relational_logistic10","same_train_context_beta",
      "same_train_channel_beta","never_query","always_query",
      "cheap_only","simulator_oracle_inaccessible")

class Quarantined(ValueError):pass
def need(ok,why):
    if not ok:raise Quarantined("F117_"+why)
def raw(path):
    return Path(path).read_bytes().replace(b"\r\n",b"\n")
def blob(b):
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def frozen():
    b=raw(FREEZE)
    need(blob(b)==FREEZE_BLOB and
         blob(raw(ROOT/"nativeevidence/f116_learned_query_value.py"))==
              PARENT_SOURCE_BLOB,"FROZEN_OR_PARENT_SOURCE_CHANGED")
    cfg=json.loads(b)
    need(cfg["schema"]=="forge.autonomy.f117.frozen-relational-context-calibration-public.v1"
         and cfg["parent"]["exact_F116_head"]==PARENT_HEAD
         and cfg["parent"]["source_blob"]==PARENT_SOURCE_BLOB
         and cfg["parent"]["freeze_blob"]==
              "ff1b7b7cf4ba5a37948c832e1ba4378897f4be5e"
         and cfg["data"]["train"]==[78000,79023]
         and [b["seeds"] for b in cfg["data"]["guard"]]==[
             [80000,80511],[81000,81511],[82000,82511],[83000,83511]]
         and cfg["data"]["generator_internal_sensor_correctness_by_channel_if_roles_equal"]==
             list(CHANCE_MATCH)
         and cfg["data"]["generator_internal_sensor_correctness_by_channel_if_roles_different"]==
             list(CHANCE_MISMATCH)
         and cfg["data"]["sensor_empty_probability"]==.125
         and cfg["data"]["training_cases"]==1024
         and cfg["data"]["guard_cases_each"]==512,"FROZEN_SOURCE_OR_GENERATOR_DRIFT")
    model=cfg["model"]
    need(model["params"]==10 and model["training_updates"]==100
         and model["learning_rate"]==.9 and model["parameter_clip"]==[-8,8]
         and model["utility"]=={"correct":1,"wrong":-4,"abstain":-.1,
              "query_costs":list(COSTS)}
         and model["zero_GUARD_gradient"] is True
         and model["paid_queries_max"]==1
         and model["source_reads_max"]==1
         and len(model["comparison_arms"])==6
         and cfg["preregistered_screens"]["forbid_post_guard_tuning"] is True
         and all(cfg["authority"].values()),"MODEL_SCREEN_OR_AUTHORITY_DRIFT")
    parent.frozen()
    return cfg,hashlib.sha256(b).hexdigest()

@dataclass(frozen=True)
class Public:
    root:str
    target:str
    edges:tuple[tuple[str,str,str],...]
    source_codes:tuple[str,str]
    channel:int
    cost:float
    schema:str

@dataclass(frozen=True)
class World:
    seed:int
    family:int
    public:Public
    true_tag:int
    sensor_tag:int|None

class PaidSensor:
    def __init__(self,returned):
        self.returned=returned
        self.reads=0
    def read(self):
        need(self.reads==0,"SECOND_PAID_QUERY_DENIED")
        self.reads+=1
        return self.returned

def source_rng(seed,family,purpose):
    # Independent deterministic internal streams, NOT independent scientific custody.
    return random.Random(seed*117019+family*33013+purpose*7919)

def make_world(seed,family):
    need(type(family) is int and family in range(5) and
         type(seed) is int and SEEDS[family][0]<=seed<=SEEDS[family][1],
         "UNREGISTERED_PUBLIC_SEED")
    n=4 if family==0 else 2
    cell=(seed-SEEDS[family][0])//n
    ch=cell//64
    cost_index=(cell//16)%4
    a,b=divmod(cell%16,4)
    need(ch in range(4) and cost_index in range(4),"BALANCE_CELL_INVALID")
    latent=source_rng(seed,family,1)
    spelling=source_rng(seed,family,2)
    signal=source_rng(seed,family,3)
    truth=latent.randrange(2)
    alphabet="abcdefghijkmnpqrstuvwxyz0123456789"
    def tok(length=16):
        return "".join(spelling.choice(alphabet) for _ in range(length))
    root="root/"+tok()
    middle="middle/"+tok()
    target="target/"+tok()
    codes=(FAMILIES[family]+"/src/"+tok(),FAMILIES[family]+"/src/"+tok())
    role_names=[f"role-{i}" for i in range(4)]
    if family==2:
        # Per-world bijective role renaming preserves ONLY relational equality.
        alias=[f"alias-{tok(8)}" for _ in range(4)]
        role_names=alias
    edges=[(root,role_names[a],middle),(middle,role_names[b],target)]
    if family==3:
        edges.reverse()
    if family==4:
        edges.extend([(tok(9),"distractor/"+tok(7),tok(9)) for _ in range(3)])
        spelling.shuffle(edges)
    p=Public(root,target,tuple(edges),codes,ch,COSTS[cost_index],
             "synthetic-public-source-link")
    context=(a==b)
    chance=(CHANCE_MATCH if context else CHANCE_MISMATCH)[ch]
    usable=signal.random()>=.125
    correct=(signal.random()<chance) if usable else False
    sensed=(truth if correct else 1-truth) if usable else None
    need(len(set(codes))==2 and
         p.root!=p.target and (sensed is None or sensed in (0,1)),
         "PUBLIC_GRAPH_OR_SENSOR_GENERATOR_INVALID")
    return World(seed,family,p,truth,sensed)

def role_match(p):
    # Honest limitation: engineered two-hop relation extraction, NOT learned
    # representations of unknown graph structure.
    paths=[]
    for left,left_role,mid in p.edges:
        if left!=p.root:continue
        for src,right_role,dst in p.edges:
            if mid==src and dst==p.target:
                paths.append((left_role,right_role))
    need(len(paths)==1,"AMBIGUOUS_OR_MISSING_PUBLIC_TWO_HOP_PATH")
    return paths[0][0]==paths[0][1]

def cohorts():
    groups=[tuple(make_world(s,i) for s in range(lo,hi+1))
            for i,(lo,hi) in enumerate(SEEDS)]
    all_rows=[w for g in groups for w in g]
    need(len(all_rows)==3072 and
         len({w.seed for w in all_rows})==3072 and
         len({w.public.root for w in all_rows})==3072 and
         len({c for w in all_rows for c in w.public.source_codes})==6144,
         "SOURCE_IDENTITIES_NOT_DISJOINT")
    for i,g in enumerate(groups):
        n=Counter((w.public.channel,w.public.cost,
                   int(role_match(w.public))) for w in g)
        # Equality occurs for 4/16 pairs: TRAIN has 4 x each pair,
        # GUARD has 2 x each pair. Hence equal=4n, unequal=12n.
        rep=4 if i==0 else 2
        for ch in range(4):
            for cost in COSTS:
                need(n[ch,cost,1]==4*rep and n[ch,cost,0]==12*rep,
                     "FROZEN_CHANNEL_COST_RELATION_DISTRIBUTION_DRIFT")
        if i:
            need(any(w.sensor_tag is None for w in g) and
                 any(w.sensor_tag is not None and w.sensor_tag!=w.true_tag
                     for w in g),"GUARD_SENSOR_MISLEADING_OR_EMPTY_MISSING")
    return groups[0],tuple(groups[1:])

def sigmoid(x):
    x=max(-16,min(16,x))
    return 1/(1+math.exp(-x))

class LearnedRelationValue:
    """10 parameters: four availability logits, four channel correctness
    biases, shared role-equality interaction, global correctness intercept."""
    parameters=10
    def __init__(self):
        self.theta=[0.]*10
        self.updates=0
    def rates(self,p):
        eq=1. if role_match(p) else -1.
        ch=p.channel
        return sigmoid(self.theta[ch]),sigmoid(
            self.theta[4+ch]+self.theta[8]*eq+self.theta[9])
    def fit(self,train):
        need(self.updates==0 and len(train)==1024 and
             all(w.family==0 for w in train),"TRAIN_ONLY_1024_REQUIRED")
        for _ in range(100):
            gradient=[0.]*10
            for w in train:
                p=w.public;ch=p.channel
                observed=w.sensor_tag is not None
                eq=1. if role_match(p) else -1.
                response,correct=self.rates(p)
                gradient[ch]+=(response-int(observed))/1024
                if observed:
                    truth=int(w.sensor_tag==w.true_tag)
                    d=(correct-truth)/1024
                    gradient[4+ch]+=d
                    gradient[8]+=d*eq
                    gradient[9]+=d
            self.theta=[max(-8.,min(8.,v-.9*g))
                        for v,g in zip(self.theta,gradient)]
            self.updates+=1
        return self
    def query(self,p):
        response,correct=self.rates(p)
        return response*(5*correct-3.9)-p.cost>0

class ContextBeta:
    """Strong same-TRAIN-data Bayesian estimator observing identical equality."""
    def __init__(self,train,contextual=True):
        self.contextual=contextual
        self.count=Counter();self.usable=Counter();self.correct=Counter()
        for w in train:
            need(w.family==0,"BETA_GUARD_TRAIN_FORBIDDEN")
            key=(w.public.channel,int(role_match(w.public))) if contextual else (
                w.public.channel,)
            self.count[key]+=1
            seen=(w.sensor_tag is not None)
            self.usable[key]+=int(seen)
            self.correct[key]+=int(seen and w.sensor_tag==w.true_tag)
        need(sum(self.count.values())==1024,"BETA_TRAIN_ONLY_COHORT")
    def rates(self,p):
        key=(p.channel,int(role_match(p))) if self.contextual else (p.channel,)
        return ((self.usable[key]+1)/(self.count[key]+2),
                (self.correct[key]+1)/(self.usable[key]+2))
    def query(self,p):
        response,correct=self.rates(p)
        return response*(5*correct-3.9)-p.cost>0

def choose_query(name,p,learned,beta,channel_beta):
    if name=="learned_relational_logistic10":return learned.query(p)
    if name=="same_train_context_beta":return beta.query(p)
    if name=="same_train_channel_beta":return channel_beta.query(p)
    if name=="never_query":return False
    if name=="always_query":return True
    if name=="cheap_only":return p.cost<=.2
    if name=="simulator_oracle_inaccessible":
        eq=role_match(p)
        return .875*(5*(CHANCE_MATCH if eq else CHANCE_MISMATCH)[p.channel]-
                      3.9)-p.cost>0
    raise Quarantined("UNRECOGNIZED_POLICY")

def evaluate_one(w,name,learned,beta,channel_beta):
    p=w.public
    query=choose_query(name,p,learned,beta,channel_beta)
    port=PaidSensor(
        {"anchor":p.root,"schema":p.schema,
         "source_code":p.source_codes[w.sensor_tag]}
        if w.sensor_tag is not None else None)
    # Offline truth / actual sensor generation never enters the actor's
    # decision until the query is irrevocably charged.
    report=port.read() if query else None
    selected=None
    if (type(report) is dict and
        set(report)=={"anchor","schema","source_code"} and
        report["anchor"]==p.root and report["schema"]==p.schema and
        report["source_code"] in p.source_codes):
        selected=p.source_codes.index(report["source_code"])
    need(port.reads<=1 and not (selected is not None and not query),
         "SENSOR_SPENDING_OR_BEFORE_QUERY_LEAK")
    correct=int(selected is not None and selected==w.true_tag)
    wrong=int(selected is not None and selected!=w.true_tag)
    abstain=int(selected is None)
    utility=correct-4*wrong-.1*abstain-(p.cost if query else 0)
    return dict(seed=w.seed,source_hash=hashlib.sha256(json.dumps(
        [p.root,p.source_codes],sort_keys=True).encode()).hexdigest(),
        channel=p.channel,cost=p.cost,role_equal=role_match(p),
        requested=int(query),empty_paid=int(query and report is None),
        misleading_paid=int(query and report is not None and wrong),
        chosen=selected,correct=correct,wrong=wrong,abstain=abstain,
        spent=round(p.cost if query else 0.,5),utility=round(utility,5))

def score(rows):
    x={k:sum(r[k] for r in rows) for k in
       ("requested","empty_paid","misleading_paid","correct","wrong",
        "abstain","spent","utility")}
    x["spent"]=round(x["spent"],5)
    x["utility"]=round(x["utility"],5)
    x["records"]=rows
    return x

def evaluate(source):
    need(type(source) is str and SHA40.fullmatch(source) is not None and
         (not os.environ.get("GITHUB_SHA") or os.environ["GITHUB_SHA"]==source),
         "CURRENT_GITHUB_SHA_REQUIRED")
    cfg,digest=frozen()
    train,guards=cohorts()
    learned=LearnedRelationValue().fit(train)
    beta=ContextBeta(train,True)
    channel_beta=ContextBeta(train,False)
    need(learned.updates==100 and len(learned.theta)==10,
         "TRAINING_BUDGET_VIOLATED")
    blocks=[]
    for idx,g in enumerate(guards):
        arm={name:score([evaluate_one(w,name,learned,beta,channel_beta)
                         for w in g]) for name in ARMS}
        blocks.append(dict(cohort=cfg["data"]["guard"][idx]["name"],
                           family=FAMILIES[idx+1],cases=512,arms=arm))
    pooled={name:round(sum(b["arms"][name]["utility"] for b in blocks),5)
            for name in ARMS}
    feasible=(pooled["learned_relational_logistic10"]>
              pooled["never_query"] and
              pooled["learned_relational_logistic10"]>pooled["always_query"])
    incremental=(all(b["arms"]["learned_relational_logistic10"]["utility"]>
                     b["arms"]["same_train_context_beta"]["utility"]
                     for b in blocks) and
                 pooled["learned_relational_logistic10"]-
                 pooled["same_train_context_beta"]>=12)
    return dict(schema=SCHEMA,source_sha=source,freeze_sha256=digest,
        parent_F116_source_blob=PARENT_SOURCE_BLOB,
        evidence_class="PUBLIC_ENGINEERED_RELATION_CONTEXT_NOT_INDEPENDENT_SCIENCE",
        train_cases=1024,guard_cases=2048,guard_blocks=blocks,
        learned_trainable_parameters=10,training_updates=100,
        learned_fit=[round(x,9) for x in learned.theta],
        pooled_utilities=pooled,
        candidate_bounded_feasibility_passed=feasible,
        learned_incremental_context_Beta_superiority_passed=incremental,
        disposition=("PUBLIC_RELATION_CONTEXT_INCREMENTAL_SCREEN_NOT_SCIENCE"
                     if incremental else
                     "NO_INCREMENTAL_ADVANTAGE_OVER_CONTEXT_MATCHED_BETA"),
        all_source_disjoint_guard_records_preserved=True,
        engineeered_role_equality_feature_not_unrestricted_learning=True,
        independent_originals=0,scientific_first_use_authorized=False,
        scientific_acceptance=0,accepted_ref_mutations=0,
        optimizer_promotions=0,codex_calls=0,paid_model_calls=0,
        extra_schedulers=0,ckb_plane_contact=False,cloudflare_writes=0,
        mind_palace_writes=0)
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source-ref",required=True)
    args=p.parse_args()
    print(json.dumps(evaluate(args.source_ref),sort_keys=True,separators=(",",":")))
if __name__=="__main__":
    main()
