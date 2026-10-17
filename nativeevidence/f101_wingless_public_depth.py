"""F101: bounded PUBLIC-DEVELOPMENT-only depth-conditioned relation propagation.

Four learned scalar parameters; label oracle is used ONLY in generator/controls.
This tiny purpose-built public generator does not establish native cognition,
scientific novelty, independent first-use, or autonomous model inference.
"""
import argparse
import hashlib
import json
import math
import os
import pathlib
import random
import re
import sys
from dataclasses import dataclass

ROOT=pathlib.Path(__file__).resolve().parents[1]
F101=ROOT/"reference/research-intake/f101-wingless-development-freeze.json"
F100=ROOT/"reference/research-intake/f100-frozen-successor-contract.json"
SCHEMA="forge.autonomy.f101.wingless-public-dev-depth-propagation.v1"
REPORT="forge.autonomy.f101.public-development-mechanism-feasibility.v1"
PARENT_F100="356955de3548a56eb916471c505ab36f4f232957"
PARENT_F100_BLOB="79718d11be36ac4742774cf3ab3d502ef2feab59"
BLOCKS=((63100,63115),(63132,63147),(63164,63179))
MAX_PAIRS=144
MAX_STEPS=100

class Rejected(ValueError):pass
def need(ok,reason):
    if not ok: raise Rejected("F101_"+reason)
def blob(data):
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()
def frozen():
    raw=F101.read_bytes()
    d=json.loads(raw)
    f100_raw=F100.read_bytes().replace(b"\r\n",b"\n")
    need(d.get("schema")==SCHEMA and d.get("parent_f100_head_sha")==PARENT_F100 and
         d.get("parent_f100_contract_git_blob_sha")==PARENT_F100_BLOB and
         blob(f100_raw)==PARENT_F100_BLOB,"FROZEN_SOURCE_IDENTITY_DRIFT")
    cfg=d.get("candidate_design",{})
    public=d.get("public_development",{})
    need(d.get("candidate_id")=="W100-C1" and d.get("lane")=="Wingless" and
         cfg.get("trainable_parameter_count")==4 and
         cfg.get("directed_edge_budget")==12 and
         cfg.get("depth_values")==[4,5,6,7] and
         cfg.get("training_updates")==100 and cfg.get("learning_rate")==0.4 and
         cfg.get("learned_model_can_call_ground_truth_oracle") is False and
         public.get("seed_blocks")==[list(x) for x in BLOCKS] and
         public.get("total_pairs")==144 and public.get("train_pairs")==96 and
         public.get("public_assessment_pairs")==48 and
         public.get("protected_originals_consumed")==0 and
         public.get("old_w_f10_seeds_reused") is False,
         "UNFROZEN_DESIGN_OR_SEEDS")
    controls=d.get("controls")
    need(controls==["frozen_depth_blind_W_F10_historical_reference_only",
                    "independently_trained_size_matched_depth_input_removed",
                    "inference_depth_permutation","always_yes_shortcut",
                    "coded_exact_depth_oracle_control_only"],
         "MISSING_STRONG_CONTROLS")
    auth=d.get("separations",{})
    for x in ("independent_original_first_use_authorized",
              "scientific_acceptance_authorized","uses_codex",
              "uses_paid_model_api","uses_chatgpt_work_task",
              "uses_ckb_plane","genenv_policy_training_activated",
              "optimizer_promotion_authorized"):
        need(auth.get(x) is False,"UNAUTHORIZED_"+x)
    need(auth.get("model_free_github_actions_only") is True and
         auth.get("accepted_ref_mutations")==0,"MODEL_EXECUTOR_OR_REF_DRIFT")
    return d,hashlib.sha256(raw).hexdigest()

@dataclass(frozen=True)
class Pair:
    seed:int
    block:int
    depth:int
    edges:tuple
    source:int
    target:int
    truth:tuple

def generate(seed,block,specimen):
    need(block in (0,1,2) and specimen in (0,1,2) and
         BLOCKS[block][0]<=seed<=BLOCKS[block][1],"UNREGISTERED_DEV_SOURCE")
    rng=random.Random((seed<<8)+(specimen<<2)+block)
    depth=4+(seed+specimen)%4
    nodes=list(range(1,21))
    rng.shuffle(nodes)
    chain=[0]+nodes[:depth]
    edges=[(a,b) for a,b in zip(chain[:-1],chain[1:])]
    outsiders=nodes[depth:]
    # Independent public distractors are disjoint from the query-target path.
    # The third public source family branches but never rejoins that path.
    for j in range(12-depth):
        if block==2 and j==0:
            edge=(0,outsiders[0])
        else:
            a=outsiders[(2*j)%len(outsiders)]
            b=outsiders[(2*j+1)%len(outsiders)]
            edge=(b,a) if block==1 else (a,b)
        edges.append(edge)
    rng.shuffle(edges)
    need(len(edges)==12 and len(set(edges))==12,"GRAPH_EDGE_DRIFT")
    return Pair(seed,block,depth,tuple(edges),0,chain[-1],(False,True))

def coded_exact_depth_oracle(edges,start,target,depth):
    # Frozen coded control/label generator. NEVER called inside model inference.
    reached={start}
    for _ in range(depth):
        nxt=set()
        for src,dst in edges:
            if src in reached:nxt.add(dst)
        reached=nxt
    return target in reached

def dataset():
    groups=[]
    seen=set()
    for block,(lo,hi) in enumerate(BLOCKS):
        group=[]
        for seed in range(lo,hi+1):
            need(seed not in range(51100,51124),"HISTORICAL_FIRST_USE_SEED_REUSE")
            for specimen in range(3):
                item=generate(seed,block,specimen)
                key=(item.seed,item.block,specimen)
                need(key not in seen,"REPLAYED_PUBLIC_CASE")
                seen.add(key)
                need((coded_exact_depth_oracle(item.edges,item.source,item.target,item.depth-1),
                      coded_exact_depth_oracle(item.edges,item.source,item.target,item.depth))==item.truth,
                     "LABEL_GENERATOR_NOT_COUNTERFACTUAL")
                group.append(item)
        need(len(group)==48,"PUBLIC_DEVELOPMENT_BLOCK_SIZE")
        groups.append(tuple(group))
    need(sum(map(len,groups))==MAX_PAIRS,"PUBLIC_DEVELOPMENT_COHORT_SIZE")
    return tuple(groups)

def sigmoid(x):
    if x>35:return 1.0-1e-15
    if x<-35:return 1e-15
    return 1/(1+math.exp(-x))

class LearnedDepthState:
    """Four trainable scalars; fixed edge-to-node message routing, learned
    depth-sensitive recurrence gain and learned Bernoulli readout.
    Not a general novel-GNN or verified autonomous native-cognition claim.
    """
    def __init__(self,depth_available=True):
        self.gain=0.95
        self.weight=0.15
        self.bias=-0.08
        self.depth_weight=0.01
        self.depth_available=depth_available
        self.updates=0
    def probability(self,case,requested_depth):
        if not self.depth_available:
            requested_depth=7
        depth_feature=(requested_depth-5)/5 if self.depth_available else 0.0
        gain=self.gain+self.depth_weight*depth_feature
        h={case.source:1.0}
        derivative={case.source:0.0}
        for _ in range(requested_depth):
            summed={}
            summed_grad={}
            for src,dst in case.edges:
                if src in h:
                    summed[dst]=summed.get(dst,0.0)+h[src]
                    summed_grad[dst]=summed_grad.get(dst,0.0)+derivative[src]
            h={k:gain*v for k,v in summed.items()}
            derivative={k:v+gain*summed_grad[k] for k,v in summed.items()}
        signal=h.get(case.target,0.0)
        grad=derivative.get(case.target,0.0)
        return sigmoid(self.weight*signal+self.bias),signal,grad,depth_feature
    def fit(self,training,steps=MAX_STEPS):
        pairs=tuple(training)
        need(0<steps<=MAX_STEPS and len(pairs)==96 and self.updates==0,
             "TRAINING_BUDGET_OR_REPLAY")
        for _ in range(steps):
            dw=db=dg=dd=0.0
            for case in pairs:
                for depth,label in ((case.depth-1,0),(case.depth,1)):
                    pred,signal,derivative,depth_feature=self.probability(case,depth)
                    residual=pred-label
                    dw+=residual*signal
                    db+=residual
                    dg+=residual*self.weight*derivative
                    dd+=residual*self.weight*derivative*depth_feature
            scale=1/(2*len(pairs))
            self.weight-=0.4*dw*scale
            self.bias-=0.4*db*scale
            self.gain=max(0.50,min(1.50,self.gain-0.4*dg*scale))
            self.depth_weight=max(-0.2,min(0.2,self.depth_weight-0.4*dd*scale))
            self.updates+=1
        return self
    def predict(self,case,depth):
        return self.probability(case,depth)[0]>=0.5

def paired_accuracy(pairs,predict):
    cases=tuple(pairs)
    need(bool(cases),"MISSING_PUBLIC_DEVELOPMENT")
    return sum((predict(p,p.depth-1),predict(p,p.depth))==p.truth for p in cases)/len(cases)

def evaluate(source_sha):
    need(type(source_sha) is str and re.fullmatch("[0-9a-f]{40}",source_sha) is not None and
         (not os.environ.get("GITHUB_SHA") or os.environ["GITHUB_SHA"]==source_sha),
         "FORGE_SOURCE_SHA_NOT_CURRENT")
    frozen_source,digest=frozen()
    groups=dataset()
    training=groups[0]+groups[1]
    held_public=groups[2]
    model=LearnedDepthState().fit(training)
    size_matched=LearnedDepthState(depth_available=False).fit(training)
    predictions={
        "learned_depth_conditioned":paired_accuracy(held_public,model.predict),
        "size_matched_depth_blind":paired_accuracy(held_public,size_matched.predict),
        "depth_permuted_ablation":paired_accuracy(held_public,
             lambda p,d:model.predict(p,p.depth+(p.depth-1-d))),
        "always_yes_shortcut":paired_accuracy(held_public,lambda p,d:True),
        "coded_exact_depth_oracle":paired_accuracy(held_public,
             lambda p,d:coded_exact_depth_oracle(p.edges,p.source,p.target,d)),
    }
    worst_depth=min(paired_accuracy([p for p in held_public if p.depth==depth],model.predict)
                    for depth in (4,5,6,7))
    worst_source=min(paired_accuracy(g,model.predict) for g in groups)
    # The third block is public DEV, not sealed/independent prospective testing.
    thresholds=frozen_source["metrics"]["screen_only_thresholds"]
    screen=(predictions["learned_depth_conditioned"]>=thresholds["minimum_paired_accuracy"] and
            predictions["learned_depth_conditioned"]-
            predictions["size_matched_depth_blind"]>=thresholds["minimum_improvement_vs_size_matched_blind"] and
            worst_depth>=thresholds["minimum_worst_group_paired_accuracy"] and
            worst_source>=thresholds["minimum_worst_group_paired_accuracy"])
    return {
        "schema":REPORT,"source_sha":source_sha,
        "frozen_prereg_sha256":digest,
        "f100_parent_sha":PARENT_F100,
        "lane":"Wingless","candidate_id":"W100-C1",
        "source_type":"PUBLIC_SYNTHETIC_DEVELOPMENT_NOT_HISTORICAL_ORIGINAL",
        "development_pair_count":sum(map(len,groups)),
        "training_pair_count":len(training),
        "public_dev_assessment_pairs":len(held_public),
        "trainable_parameter_count":4,
        "training_updates":model.updates,
        "control_training_updates":size_matched.updates,
        "public_dev_accuracy_by_arm":predictions,
        "worst_depth_paired_accuracy":worst_depth,
        "worst_public_source_group_paired_accuracy":worst_source,
        "public_development_screen_passed":screen,
        "independently_accepted_scientific_gain":False,
        "protected_first_use_authorized":False,
        "fresh_scientific_original_executed":False,
        "optimizer_promotion_authorized":False,
        "accepted_ref_mutations":0,
        "codex_calls":0,"external_model_api_calls":0,"chatgpt_work_tasks":0,
        "previous_W_F10_negative_preserved":True,
    }
def main():
    a=argparse.ArgumentParser()
    a.add_argument("--source-ref",required=True)
    ns=a.parse_args()
    print(json.dumps(evaluate(ns.source_ref),sort_keys=True,separators=(",",":")))
if __name__=="__main__":
    try:main()
    except (Rejected,ValueError,KeyError,TypeError,OSError) as exc:
        print("FORGE_F101_DEVELOPMENT_MECHANISM=QUARANTINED "+str(exc),file=sys.stderr)
        raise SystemExit(1)
