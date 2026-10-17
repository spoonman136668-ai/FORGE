"""F116: learned value-of-public-information with misleading and empty sensors.

PUBLIC SYNTHETIC development: separately seeded latent graphs and noisy public
sensor observations. NOT independently sourced research data or protected
first-use. Freeze at fad7b4de6d3864e4f3b9ee30915daddd99acb532 preceded
all F116 code and guard outcomes. No Codex, CKB, external model, deployment.
"""
from __future__ import annotations
from collections import Counter
from dataclasses import dataclass
import argparse
import hashlib
import json
import math
from pathlib import Path
import random
import re

import f115_bounded_active_clarification as f115

ROOT=Path(__file__).resolve().parents[1]
FREEZE=ROOT/"reference/research-intake/f116-learned-query-value-freeze.json"
FREEZE_BLOB="ff1b7b7cf4ba5a37948c832e1ba4378897f4be5e"
F115_SOURCE_BLOB="1d16a2164abbd6740dfa4ff1b5651e21e9745037"
F115_FREEZE_BLOB="05b0848e03d41a6d341b0009a4262c2d02f19790"
PARENT_SHA="58ecee22271771e0eba5d137c93e29282d42b126"
SHA40=re.compile(r"^[0-9a-f]{40}$")
SCHEMA="forge.autonomy.f116.train-only-noisy-sensor-value-public.v1"
RELIABILITY=(0.55,0.70,0.86,0.97)
COSTS=(0.05,0.20,0.50,0.85)
NO_EDGE_RATE=0.125
FAMILIES=("flat","permuted-source-codes","role-alias-renamed",
          "graph-anchor-refactoring","extra-distractor-public-edges")
TRAIN=(71000,72023)
GUARDS=((73000,73767),(74000,74767),(75000,75767),(76000,76767))
EDGE_KIND="synthetic-public-source-link"
ALPHABET="23456789ABCDEFGHJKLMNPQRSTUVWXYZ"

class Invalid(ValueError):pass
def need(ok,why):
    if not ok:raise Invalid("F116_"+why)
def gitblob(raw):
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
def canonical(path):
    return Path(path).read_bytes().replace(b"\r\n",b"\n")

def frozen():
    raw=canonical(FREEZE)
    need(gitblob(raw)==FREEZE_BLOB and
         gitblob(canonical(ROOT/"nativeevidence/f115_bounded_active_clarification.py"))
         ==F115_SOURCE_BLOB and
         gitblob(canonical(ROOT/"reference/research-intake/f115-bounded-active-clarification-freeze.json"))
         ==F115_FREEZE_BLOB,
         "PREREG_PARENT_SOURCE_DRIFT")
    f115.freeze()
    c=json.loads(raw)
    need(c.get("schema")=="forge.autonomy.f116.frozen-learned-query-value-source-disjoint-public.v1"
         and c["parent"]["exact_F115_head"]==PARENT_SHA
         and c["parent"]["frozen_F115_source_git_blob"]==F115_SOURCE_BLOB
         and c["parent"]["frozen_F115_protocol_git_blob"]==F115_FREEZE_BLOB
         and c["frozen_source_split"]["TRAIN"]["seed_start"]==TRAIN[0]
         and c["frozen_source_split"]["TRAIN"]["seed_end"]==TRAIN[1]
         and [(v["seed_start"],v["seed_end"])
              for v in c["frozen_source_split"]["GUARD"]]==list(GUARDS),
         "SOURCE_SPLIT_IDENTITY_DRIFT")
    a=c["sensor_and_utility"]
    fit=c["fit"]
    need(a["channelIDs_nominal"]==[0,1,2,3] and
         a["channel_correct_given_usable"]==list(RELIABILITY) and
         a["probability_sensor_no_edge"]==NO_EDGE_RATE and
         a["evidence_costs"]==list(COSTS) and
         [a["reward_correct"],a["reward_wrong"],a["reward_abstain"]]==[1,-4,-0.1]
         and fit["params"]==8 and fit["updates"]==100
         and "learning rate 0.9" in fit["learner"]
         and "Beta(1,1)" in str(fit["independent_equal_info_controls"]) and
         all(v is True for v in c["authority"].values()),
         "TRAINING_OR_AUTHORITY_CONTRACT_DRIFT")
    return c,hashlib.sha256(raw).hexdigest()

@dataclass(frozen=True)
class Public:
    anchor:str
    candidate_codes:tuple[str,str]
    channel:int
    cost:float
    # No seed, split, family, graph truth, sensor result or latent answer.

@dataclass(frozen=True)
class Link:
    schema:str
    anchor:str
    source_code:str

@dataclass(frozen=True)
class World:
    public:Public
    sample_id:int
    family:int
    graph_truth:int
    graph_fingerprint:str
    positive:tuple[float,float]
    negative:tuple[float,float]
    sensor:tuple[Link,...]
    # Offline scoring & TRAIN supervision only. Not an inference argument.

class PaidPort:
    def __init__(self,edges):
        self.edges=edges
        self.queries=0
    def read(self):
        need(self.queries==0,"SECOND_QUERY_REFUSED")
        self.queries+=1
        return self.edges

def token(rng,n=16):
    return "".join(rng.choice(ALPHABET) for _ in range(n))

def world(seed:int,family:int):
    need(type(family) is int and 0<=family<=4 and
         type(seed) is int and
         ((family==0 and TRAIN[0]<=seed<=TRAIN[1]) or
          (family>0 and GUARDS[family-1][0]<=seed<=GUARDS[family-1][1])),
         "SEED_OR_FAMILY_OUTSIDE_SOURCE_IDENTITY")
    start=TRAIN[0] if family==0 else GUARDS[family-1][0]
    local=seed-start
    ch=local%4
    ci=(local//4)%4
    # Separate PRNG streams: underlying graph and latent relevant source;
    # distinct source ID spelling; noisy channel. These are internal
    # independent simulation streams, NOT externally sourced evidence.
    graph_rng=random.Random(seed*11147+family*23+11601)
    code_rng=random.Random(seed*11887+family*43+11602)
    sensor_rng=random.Random(seed*11939+family*89+11603)
    truth=graph_rng.randrange(2)
    ids=[token(code_rng),token(code_rng)]
    need(ids[0]!=ids[1],"DUPLICATE_SOURCE_CODES")
    anchor=token(code_rng,12)
    if family==2:
        ids=[("alias/"+s) for s in ids]
    elif family==3:
        anchor="graph/"+anchor
    elif family==4:
        ids=[("ctx/"+s+"/edge") for s in ids]
    elif family==1:
        ids=[s[::-1] for s in ids]
    public=Public(anchor,tuple(ids),ch,COSTS[ci])
    # Other public distractor links in a synthetic graph are not the paid
    # source link. The sensor's one candidate edge is conditionally sampled.
    # Its correctness is stochastic, not guaranteed by source selection.
    sensor_available = sensor_rng.random()>=NO_EDGE_RATE
    correct_sensor = (sensor_rng.random()<RELIABILITY[ch]) if sensor_available else None
    selected=truth if correct_sensor else 1-truth
    sensor=(Link(EDGE_KIND,anchor,public.candidate_codes[selected]),) if sensor_available else ()
    graph_edges=(("anchor",anchor,"latent-source",public.candidate_codes[truth]),
                 ("noise",token(graph_rng,8),"independent",token(graph_rng,8)))
    graph_hash=hashlib.sha256(json.dumps(graph_edges,sort_keys=True).encode()).hexdigest()
    # Counterfactual signs are evaluator-only; selection happens BEFORE read.
    sign_rng=random.Random(seed*12149+family*71+11604)
    other=sign_rng.choice((-1.0,1.0))
    pos=[other,other]
    neg=[other,other]
    pos[truth]=1.0
    neg[truth]=-1.0
    need(sum(a!=b for a,b in zip(pos,neg))==1,
         "PAIR_ONLY_ONE_SIGN_CHANGES")
    return World(public,seed,family,truth,graph_hash,
                 tuple(pos),tuple(neg),sensor)

def cohorts():
    train=tuple(world(s,0) for s in range(TRAIN[0],TRAIN[1]+1))
    guards=tuple(tuple(world(s,i+1) for s in range(lo,hi+1))
                 for i,(lo,hi) in enumerate(GUARDS))
    need(len(train)==1024 and all(len(g)==768 for g in guards),
         "SOURCE_COUNT_DRIFT")
    all_worlds=train+tuple(w for g in guards for w in g)
    need(len({w.sample_id for w in all_worlds})==len(all_worlds) and
         len({w.graph_fingerprint for w in all_worlds})==len(all_worlds) and
         len({c for w in all_worlds for c in w.public.candidate_codes})==
         len(all_worlds)*2 and
         len({w.public.anchor for w in all_worlds})==len(all_worlds),
         "SOURCE_OR_GRAPH_NOT_DISJOINT")
    for block,each in ((train,64), *((g,48) for g in guards)):
        tally=Counter((w.public.channel,w.public.cost) for w in block)
        need(len(tally)==16 and
             all(tally[(ch,c)]==each for ch in range(4) for c in COSTS),
             "BALANCED_COST_CHANNEL_FROZEN_DRIFT")
        channels=Counter(w.public.channel for w in block if w.sensor)
        empties=sum(not w.sensor for w in block)
        bad=sum(bool(w.sensor) and
                w.sensor[0].source_code!=w.public.candidate_codes[w.graph_truth]
                for w in block)
        need(empties>0 and bad>0 and
             all(channels[x]>0 for x in range(4)),
             "MISSING_MISLEADING_OR_UNINFORMATIVE_EVIDENCE")
    return train,guards

def sigmoid(x):
    return 1/(1+math.exp(-max(-16.0,min(16.0,x))))

class LearnedChannelValue:
    def __init__(self):
        self.availability=[0.0]*4
        self.correctness=[0.0]*4
        self.updates=0
    def fit(self,train):
        need(self.updates==0 and len(train)==1024 and
             all(w.family==0 for w in train),
             "TRAIN_ONLY_PROVENANCE")
        # First fit 4 independent Bernoulli usable-signal parameters;
        # then 4 conditional correctness parameters using only TRAIN labels.
        for _ in range(100):
            for channel in range(4):
                rows=[w for w in train if w.public.channel==channel]
                usable=[w for w in rows if w.sensor]
                need(len(rows)==256 and len(usable)>0,
                     "TRAIN_CHANNEL_OR_AVAILABLE_EMPTY")
                observed_available=sum(bool(w.sensor) for w in rows)/len(rows)
                observed_correct=sum(
                    w.sensor[0].source_code==
                    w.public.candidate_codes[w.graph_truth]
                    for w in usable)/len(usable)
                self.availability[channel]=max(-8.,min(8.,
                    self.availability[channel]-.9*(
                    sigmoid(self.availability[channel])-observed_available)))
                self.correctness[channel]=max(-8.,min(8.,
                    self.correctness[channel]-.9*(
                    sigmoid(self.correctness[channel])-observed_correct)))
            self.updates+=1
        return self
    def rates(self,channel):
        return sigmoid(self.availability[channel]),sigmoid(self.correctness[channel])

class BetaChannelValue:
    """Strong same-data empirical estimate; NO GUARD labels or prior outcomes."""
    def __init__(self,train):
        need(len(train)==1024 and all(w.family==0 for w in train),
             "BETA_TRAIN_ONLY")
        self.availability=[]
        self.correctness=[]
        for ch in range(4):
            rows=[w for w in train if w.public.channel==ch]
            usable=[w for w in rows if w.sensor]
            correct=sum(w.sensor[0].source_code==
                        w.public.candidate_codes[w.graph_truth] for w in usable)
            self.availability.append((len(usable)+1)/(len(rows)+2))
            self.correctness.append((correct+1)/(len(usable)+2))
    def rates(self,ch):
        return self.availability[ch],self.correctness[ch]

def buy_if_positive(rates,cost):
    response,correct=rates
    # Relative to abstaining (-.1), with correct +1, wrong -4,
    # empty -0.1 and paid cost. Frozen before evaluation.
    return response*(5*correct-3.9)-cost>0

def valid_edge(p,edges):
    if type(edges) is not tuple or len(edges)!=1: return None
    x=edges[0]
    if type(x) is not Link or x.schema!=EDGE_KIND or x.anchor!=p.anchor:
        return None
    if x.source_code not in p.candidate_codes: return None
    return p.candidate_codes.index(x.source_code)

def choose_if_query(p,read,should_query):
    if not should_query:
        return None
    return valid_edge(p,read())

def learned_policy(model):
    return lambda p,read:choose_if_query(p,read,
             buy_if_positive(model.rates(p.channel),p.cost))

def beta_policy(model):
    return lambda p,read:choose_if_query(p,read,
             buy_if_positive(model.rates(p.channel),p.cost))

def no_query(p,read):return None
def always_query(p,read):return choose_if_query(p,read,True)
def cheap_fixed(p,read):return choose_if_query(p,read,p.cost<=0.20)
def nominal_high_fixed(p,read):return choose_if_query(p,read,p.channel>=2)
def simulator_oracle(p,read):
    # UNDEPLOYABLE: sees frozen sensor generator rate, not an observed fact.
    # Never feeds a learned model or changes policy / scientific acceptance.
    return choose_if_query(p,read,
             buy_if_positive((1-NO_EDGE_RATE,RELIABILITY[p.channel]),p.cost))

def assess(worlds,policy):
    rows=[]
    for w in worlds:
        port=PaidPort(w.sensor)
        # The actor sees ONLY Public and callable paid port; never World.
        selected=policy(w.public,port.read)
        need((selected is None or
             (type(selected) is int and selected in (0,1)))
             and port.queries<=1,"UNAUTHORIZED_ACTION_OR_SECOND_QUERY")
        if selected is None:
            outcome="abstain"
        else:
            outcome="correct" if selected==w.graph_truth else "wrong"
            # Offline truth assertion: only one counterfactual sign may differ.
            need((w.positive[selected]>0 and w.negative[selected]<0)==
                 (selected==w.graph_truth),
                 "EVALUATOR_GOLD_RESULT_MISMATCH")
        rows.append(dict(sample_id=w.sample_id,
                  source_identity_sha256=hashlib.sha256(json.dumps(
                      [w.public.anchor,w.public.candidate_codes],
                      sort_keys=True).encode()).hexdigest(),
                  graph_sha256=w.graph_fingerprint,
                  channel=w.public.channel,cost=w.public.cost,
                  queried=port.queries,usable_response=bool(w.sensor),
                  misleading_response=(bool(w.sensor) and
                      w.sensor[0].source_code!=
                      w.public.candidate_codes[w.graph_truth]),
                  selected=selected,
                  true_tag_OFFLINE_ONLY=w.graph_truth,outcome=outcome))
    c=Counter(x["outcome"] for x in rows)
    correct,wrong,abstained=(c["correct"],c["wrong"],c["abstain"])
    queries=sum(x["queried"] for x in rows)
    noedge=sum(x["queried"] and not x["usable_response"] for x in rows)
    deceptive=sum(x["queried"] and x["misleading_response"] for x in rows)
    spend=sum(x["cost"]*x["queried"] for x in rows)
    utility=round(correct-4*wrong-.1*abstained-spend,8)
    need(len(rows)==correct+wrong+abstained,"MISSING_NEGATIVE_OUTCOMES")
    return dict(count=len(rows),correct=correct,wrong=wrong,abstained=abstained,
                queries=queries,empty_paid_queries=noedge,
                misleading_paid_queries=deceptive,
                total_paid_cost=round(spend,8),utility=utility,rows=rows)

def evaluate(head):
    need(type(head) is str and SHA40.fullmatch(head),
         "CURRENT_SOURCE_SHA_INVALID")
    cfg,prereg_sha=frozen()
    train,guards=cohorts()
    learned=LearnedChannelValue().fit(train)
    beta=BetaChannelValue(train)
    need(learned.updates==100 and
         len(learned.availability)+len(learned.correctness)==8,
         "FROZEN_TRAIN_BUDGET_CHANGED")
    arms={
      "learned_train_only_eight_logits":learned_policy(learned),
      "empirical_beta_train_only":beta_policy(beta),
      "no_query_abstain":no_query,
      "always_query":always_query,
      "cheap_query_fixed":cheap_fixed,
      "high_channel_fixed":nominal_high_fixed,
      "unavailable_true_simulator_rate_oracle":simulator_oracle,
    }
    blocks=[]
    for index,worlds in enumerate(guards):
        blocks.append(dict(cohort=cfg["frozen_source_split"]["GUARD"][index]["name"],
             family=FAMILIES[index+1],count=768,
             policies={name:assess(worlds,fn) for name,fn in arms.items()}))
    totals={name:dict(
       correct=sum(b["policies"][name]["correct"] for b in blocks),
       wrong=sum(b["policies"][name]["wrong"] for b in blocks),
       abstained=sum(b["policies"][name]["abstained"] for b in blocks),
       queries=sum(b["policies"][name]["queries"] for b in blocks),
       empty_paid_queries=sum(b["policies"][name]["empty_paid_queries"] for b in blocks),
       misleading_paid_queries=sum(b["policies"][name]["misleading_paid_queries"] for b in blocks),
       utility=round(sum(b["policies"][name]["utility"] for b in blocks),8))
       for name in arms}
    learned_total=totals["learned_train_only_eight_logits"]["utility"]
    bounded=learned_total>totals["no_query_abstain"]["utility"] and \
            learned_total>totals["always_query"]["utility"]
    positive=all(
       b["policies"]["learned_train_only_eight_logits"]["utility"]>
       b["policies"]["empirical_beta_train_only"]["utility"] for b in blocks
    ) and learned_total>=totals["empirical_beta_train_only"]["utility"]+12
    return dict(schema=SCHEMA,source_sha=head,prereg_sha256=prereg_sha,
         parent_F115_head=PARENT_SHA,
         source_kind="PUBLIC_SIMULATED_LATENT_GRAPHS_NOT_EXTERNAL_ORIGINAL_EVIDENCE",
         train_count=len(train),guard_count=sum(map(len,guards)),
         train_guard_source_IDs_disjoint=True,
         no_guard_retraining=True,trained_steps=learned.updates,
         learned_trainable_params=8,
         learned_rates_by_nominal_channel=[
           {"channel":i,"usable_probability":round(learned.rates(i)[0],8),
            "correct_given_usable":round(learned.rates(i)[1],8),
            "beta_usable":round(beta.rates(i)[0],8),
            "beta_correct_given_usable":round(beta.rates(i)[1],8)}
           for i in range(4)],
         guard_blocks=blocks, totals_by_arm=totals,
         bounded_learned_feasibility_passed=bounded,
         incremental_learning_over_equal_information_Beta_control_passed=positive,
         disposition=(
           "TRAIN_ONLY_LEARNED_QUERY_FEASIBLE_PUBLIC_NOT_SCIENCE"
           if bounded else
           "TRAIN_ONLY_LEARNED_QUERY_FEASIBILITY_NEGATIVE_PUBLIC"),
         incremental_disposition=(
           "LEARNED_INCREMENTAL_GAIN_VS_TRAIN_BETA_PUBLIC_ONLY"
           if positive else
           "NO_INCREMENTAL_GAIN_OVER_EQUAL_TRAIN_BETA_CONTROL"),
         scientific_first_use_authorized=False,independently_accepted_science=False,
         optimizer_promotion_authorized=False,accepted_ref_mutations=0,
         real_scientific_originals=0,model_API_calls=0,codex_calls=0,
         external_controller_accessed=False,MindPalace_written=False)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--source-ref",required=True)
    args=parser.parse_args()
    print(json.dumps(evaluate(args.source_ref),sort_keys=True,separators=(",",":")))
if __name__=="__main__":main()
