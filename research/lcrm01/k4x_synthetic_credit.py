#!/usr/bin/env python3
"""K4X preregistered synthetic delayed-action credit falsifier.

Synthetic trajectories only; NOT a MiniGrid simulation, original episode,
original source first use, or evidence for navigation generalization.
The pinned original Yggdrasil GridColony code is not modified.
"""
import argparse
import base64
import hashlib
import importlib
import json
import math
import os
import pathlib
import random
import resource
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request

HERE=pathlib.Path(__file__).resolve().parent
FREEZE=HERE/"k4x_frozen_synthetic_credit.json"

def check(ok,msg):
    if not ok: raise ValueError("K4X_FAIL_CLOSED_"+msg)

def sha(data):return hashlib.sha256(data).hexdigest()
def canon(x):return json.dumps(x,sort_keys=True,separators=(",",":"),allow_nan=False).encode()

def fetch_pin(spec):
    path=spec["path"]
    url="https://api.github.com/repos/"+spec["yggdrasil_repository"]+"/contents/"+urllib.parse.quote(path,safe="/")+"?ref="+spec["yggdrasil_native_commit"]
    headers={"Accept":"application/vnd.github+json","User-Agent":"mass-k4x-freeze-only","X-GitHub-Api-Version":"2022-11-28"}
    if os.environ.get("GH_TOKEN"):headers["Authorization"]="Bearer "+os.environ["GH_TOKEN"]
    with urllib.request.urlopen(urllib.request.Request(url,headers=headers),timeout=20) as response:
        reply=json.load(response)
    check(reply.get("encoding")=="base64" and reply.get("type")=="file","SOURCE_TYPE")
    raw=base64.b64decode(reply["content"],validate=False)
    digest=hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
    check(digest==spec["blob"]==reply["sha"],"SOURCE_BLOB_DRIFT")
    check(spec["yggdrasil_native_commit"]=="1b042d6bf4832d885d80ef73f3ab29d8a600bfe2","SOURCE_REF_DRIFT")
    return raw

def grid(native,x,direction=0):
    return native.PublicGrid(x,3,4,3,direction,False)

def schedule(protocol,role):
    world=protocol["world"]
    if role=="FIT":
        samples=[(x,a) for x in world["FIT_initial_x"] for a in (0,1,2) for _ in range(96)]
        check(len(samples)==world["synthetic_fit_episodes"],"FIT_SIZE")
        rng=random.Random(20261024)
        rng.shuffle(samples)
    elif role=="TEST":
        samples=[(x,0) for x in world["TEST_unseen_initial_x"] for _ in range(64)]
        check(len(samples)==world["synthetic_eval_episodes"],"TEST_SIZE")
        rng=random.Random(20261025)
        rng.shuffle(samples)
    else:raise ValueError("K4X_UNQUALIFIED_ROLE")
    return samples

def target(x):
    check(x in (2,3,6,7),"UNDECLARED_CONTEXT")
    return 0 if x<4 else 1

def synthetic(native,x,arm):
    check(arm in (0,1,2),"ILLEGAL_ACTION")
    before=grid(native,x)
    turned=grid(native,x,3 if arm==0 else (1 if arm==1 else 0))
    # Three actually selected synthetic actions, including the two followup
    # forward actions. Terminal reward is generated only after the last step.
    outcome=int(arm==target(x))
    return [(before,arm,turned,0.,False),
            (turned,2,turned,0.,False),
            (turned,2,turned,float(outcome),True)]

def native_immediate(native,fit):
    model=native.GridColony()
    for x,arm in fit:
        for before,a,after,reward,terminal in synthetic(native,x,arm):
            model.observe(before,a,after,reward,terminal)
    check(model.feedback_updates==3*len(fit),"IMMEDIATE_UPDATE_COUNT")
    return model

class RetrospectiveCellular:
    """Derived source-only mechanism probe; NEVER an upstream Yggdrasil patch.

    Final observed terminal reward is attributed to actually executed initial
    turn/forward choice at a frozen two-step delay, NOT to imaginary actions.
    The original local cell plasticity and source-only public features are used.
    This redirects which original observed action receives reward credit.
    """
    def __init__(self,native,discount):
        self.native=native
        self.model=native.GridColony()
        self.discount=discount
        self.original_executed_actions=0
        self.credited_initial_actions=0
    def train(self,x,arm,label):
        check(label in (0,1),"INVALID_ORIGINAL_REWARD")
        events=synthetic(self.native,x,arm)
        check(int(events[-1][3]) in (0,1),"PHYSICAL_SOURCE_ERROR")
        # Original actual first two synthetic actions have no reward.
        for before,actual,after,r,done in events[:2]:
            check(r==0 and not done,"NONZERO_PRE_TERMINAL_REWARD")
            self.model.observe(before,actual,after,r,done)
        before=events[0][0]
        phi=self.native.features(before)
        # No external expert trajectory / reward on unexecuted action;
        # label is actual terminal observation or explicit shuffled ablation.
        expected=(self.discount**2)*label
        error=self.native.limited(expected-self.model.score(before,arm),1.)
        for cell,value in zip(self.model.cells[str(arm)],phi):
            cell.learn(value,error)
        self.model.feedback_updates+=1
        self.original_executed_actions+=3
        self.credited_initial_actions+=1
    def choose(self,x):
        return self.model.choose(grid(self.native,x))

class TabularTrace:
    """Strong conventional two-step eligibility table, matched FIT labels."""
    def __init__(self,discount):
        self.discount=discount
        self.n={}
        self.rewards={}
    def train(self,x,arm,label):
        sign= -1 if x<4 else 1
        k=(sign,arm)
        self.n[k]=self.n.get(k,0)+1
        self.rewards[k]=self.rewards.get(k,0.)+self.discount**2*label
    def choose(self,x):
        sign= -1 if x<4 else 1
        return max((0,1,2),key=lambda a:(self.rewards.get((sign,a),0.)/max(1,self.n.get((sign,a),0)),-a))

def score(model,evals):
    chosen=[model.choose(x) for x,_ in evals]
    check(all(type(a) is int and a in (0,1,2) for a in chosen),"INVALID_POLICY_CHOICE")
    good=sum(a==target(x) for a,(x,_) in zip(chosen,evals))
    return {"successes":good,"n":len(evals),"accuracy":good/len(evals),
            "action_counts":[chosen.count(a) for a in (0,1,2)],
            "per_context":{str(x):sum(a==target(x) for a,(q,_) in zip(chosen,evals) if q==x)
                          for x in sorted(set(x for x,_ in evals))}}

def experiment(native,protocol):
    fit=schedule(protocol,"FIT");test=schedule(protocol,"TEST")
    # Original FIT training labels from explicitly public synthetic outcome.
    labels=[int(a==target(x)) for x,a in fit]
    rng=random.Random(20261026)
    shuffled=labels[:]
    rng.shuffle(shuffled)
    check(sorted(shuffled)==sorted(labels),"ABLATED_REWARD_MULTISET_CHANGED")
    discount=protocol["param"]["gamma"]
    initial=time.process_time()
    original=native_immediate(native,fit)
    original_cpu=time.process_time()-initial
    start=time.process_time()
    temporal=RetrospectiveCellular(native,discount)
    negative=RetrospectiveCellular(native,discount)
    table=TabularTrace(discount)
    for (x,a),real,misassigned in zip(fit,labels,shuffled):
        temporal.train(x,a,real)
        negative.train(x,a,misassigned)
        table.train(x,a,real)
    trace_cpu=time.process_time()-start
    check(temporal.original_executed_actions==1728 and temporal.credited_initial_actions==576,"DELAYED_EVENT_ACCOUNTING")
    check(negative.credited_initial_actions==576,"ABLATION_EVENT_ACCOUNTING")
    models={"original_native_immediate":original,"retrospective_local_cellular":temporal,
            "tabular_eligibility":table,"shuffled_terminal_reward":negative}
    stats={name:score(model,test) if name!="original_native_immediate" else
           score(type("Adapter",(),{"choose":lambda self,x:original.choose(grid(native,x))})(),test)
           for name,model in models.items()}
    passed=(stats["original_native_immediate"]["accuracy"]<=protocol["acceptance"]["baseline_max_eval_success"]
            and stats["retrospective_local_cellular"]["accuracy"]>=protocol["acceptance"]["credit_min_eval_success"]
            and stats["retrospective_local_cellular"]["accuracy"]-stats["original_native_immediate"]["accuracy"]>=protocol["acceptance"]["credit_advantage_min"]
            and stats["tabular_eligibility"]["accuracy"]>=protocol["acceptance"]["tabular_min_eval_success"]
            and stats["retrospective_local_cellular"]["accuracy"]-stats["shuffled_terminal_reward"]["accuracy"]>=protocol["acceptance"]["shuffled_credit_degradation_min"])
    check(len(fit)==576 and len(test)==128 and all(x not in (2,6) for x,_ in test),"FIT_TEST_LEAKAGE")
    return {"protocol":"mass.lcrm01.k4x.frozen-synthetic-delayed-credit-mechanism-v1",
      "classification":"K4X_SYNTHETIC_MECHANISM_PROBE_PASS" if passed else "K4X_SYNTHETIC_MECHANISM_PROBE_NO_GO",
      "source_only":True,"physical_minigrid_episodes":0,"K4U_original_native_transfer_NO_GO_preserved":True,
      "FIT_synthetic_episodes":len(fit),"TEST_unseen_synthetic_episodes":len(test),
      "FIT_positive_terminal_rewards":sum(labels),"FIT_schedule_sha256":sha(canon(fit)),
      "TEST_schedule_sha256":sha(canon(test)), "methods":stats,
      "original_native_fit_updates":original.feedback_updates,
      "retrospective_cellular_fit_updates":temporal.model.feedback_updates,
      "source_only_native_model_blob_sha256":sha(native.GridColony().save()),
      "original_cpu_seconds":original_cpu,"other_training_cpu_seconds":trace_cpu,
      "note":"Original native and differentiated credit intervention differ by reward-routing and update count; synthetic score is not navigation, causal-world transfer, FSA acceptance or resource superiority."}

def main():
    arg=argparse.ArgumentParser()
    arg.add_argument("--output",required=True,type=pathlib.Path)
    ns=arg.parse_args()
    check(not ns.output.exists() and ns.output.parent.is_dir(),"OVERWRITE")
    freeze=json.loads(FREEZE.read_text())
    check(freeze["schema"]=="mass.lcrm01.k4x.frozen-synthetic-delayed-credit-mechanism-v1","PROTOCOL_IDENTITY")
    check(freeze["world"]["synthetic_fit_episodes"]==576 and freeze["world"]["synthetic_eval_episodes"]==128,"BUDGET_CHANGE")
    raw=fetch_pin(freeze["sources"])
    with tempfile.TemporaryDirectory(prefix="k4x-source-only-") as tmp:
        pathlib.Path(tmp,"native_policy.py").write_bytes(raw)
        sys.path.insert(0,tmp)
        try:
            native=importlib.import_module("native_policy")
            before=time.monotonic()
            evidence=experiment(native,freeze)
            evidence["observed_host_wall_seconds"]=time.monotonic()-before
            evidence["host_peak_rss_bytes"]=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
            evidence["actual_native_source_blob"]=freeze["sources"]["blob"]
            evidence["frozen_original_negative"]="K4U_NO_QUALIFIED_NATIVE_UNFAMILIAR_WORLD_TRANSFER"
        finally:
            sys.path.pop(0)
            sys.modules.pop("native_policy",None)
    ns.output.write_text(json.dumps(evidence,sort_keys=True,indent=2)+"\n")
    print("K4X_FROZEN_SYNTHETIC_SOURCE_ONLY="+evidence["classification"])
    for name,v in evidence["methods"].items():
        print("K4X_METHOD="+name+" accuracy="+str(v["accuracy"])+" choices="+str(v["action_counts"]))
    print("K4X_NO_MINIGRID_OR_SCIENTIFIC_FIRST_USE=TRUE")
if __name__=="__main__":main()
