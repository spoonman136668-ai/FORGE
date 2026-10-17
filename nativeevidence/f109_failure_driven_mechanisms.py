"""F109 frozen, failure-driven one-read source routing and strict-slot graph model.

Both candidate and unchanged parent get the same bounded training opportunities.
Public synthetic task only; no original scientific first-use or authority transfer.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import random
import re
import sys
from dataclasses import dataclass

import f103_yggdrasil_public_binding as ybind
import f104_wingless_public_observations as wobserve
import f108_public_superiority as f108

ROOT=Path(__file__).resolve().parents[1]
FREEZE=ROOT/"reference/research-intake/f109-failure-driven-mechanism-freeze.json"
FREEZE_BLOB="bb90fa23ba454f7a8a337babe3185f8f7d06986a"
F108_BLOB="bd1166310d2e1a2b5a8c993f3c814aa26e2726ea"
PARENT="8cc29268eee3915308b83c219f8c2031845c9646"
SCHEMA="forge.autonomy.f109.failure-driven-mechanism-freeze.v1"
REPORT="forge.autonomy.f109.resource-matched-failure-driven-public-development.v1"
SOURCE=re.compile(r"^[0-9a-f]{40}$")

class Quarantined(ValueError): pass
def require(flag,reason):
    if not flag:raise Quarantined("F109_"+reason)
def gitblob(raw):
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
def canonical(path):
    return Path(path).read_bytes().replace(b"\r\n",b"\n")
def frozen():
    raw=canonical(FREEZE)
    require(gitblob(raw)==FREEZE_BLOB and
            gitblob(canonical(ROOT/"nativeevidence/f108_public_superiority.py"))==F108_BLOB,
            "PREIMPLEMENTATION_FROZEN_SOURCE_DRIFT")
    f=json.loads(raw)
    require(f.get("schema")==SCHEMA and f.get("parent_f108_head_sha")==PARENT and
            f.get("f108_protocol_blob_sha")=="d6e3568b025681193d632c8fd7e92ef2a8457e9f" and
            f.get("f108_implementation_blob_sha")==F108_BLOB,
            "PARENT_EVIDENCE_DRIFT")
    neg=f.get("f108_negative_precondition",{})
    require(neg=={
        "Wingless":{"candidate_score":0.75,"parent_score":1.0,
                    "cost_parity_satisfied":False,"outcome":"NO_DEMONSTRATED_GAIN_RETAIN_NEGATIVE"},
        "Yggdrasil":{"candidate_score":1.0,"parent_score":1.0,
                    "cost_parity_satisfied":True,"outcome":"NO_DEMONSTRATED_GAIN_RETAIN_NEGATIVE"}},
            "NEGATIVE_RELABEL")
    w=f["seeds_and_generator"]["Wingless"]
    y=f["seeds_and_generator"]["Yggdrasil"]
    require(w["training"]==[66000,66031] and w["diagnostic"]==[66048,66095] and
            w["training_pairs"]==96 and w["diagnostic_pairs"]==48 and
            w["train_instances_per_seed"]==3 and w["test_instances_per_seed"]==1 and
            w["observation_reads_per_prediction"]==1 and
            w["public_metadata"]=="source_tag_offset_0_to_3_available_to_both_arms" and
            y["training"]==[66100,66131] and y["diagnostic"]==[66148,66195] and
            y["training_pairs"]==96 and y["diagnostic_pairs"]==48 and
            y["edge_count"]==12 and y["path_hops"]==4 and
            y["negative_mutation"]=="one_main_path_variable_argument_change",
            "FROZEN_COHORT_OR_BUDGET_DRIFT")
    wmod=f["frozen_models"]["Wingless"]
    ymod=f["frozen_models"]["Yggdrasil"]
    require(wmod["candidate_learned_parameters_max"]==64 and
            wmod["parent_learned_parameters"]==18 and
            wmod["candidate_fixed_updates"]==100 and
            wmod["parent_fixed_updates"]==100 and
            wmod["both_train_using_identical_new_96_pairs"] is True and
            wmod["no_labels_at_inference"] is True and
            wmod["randomized_source_offsets_independent_of_labels"] is True and
            ymod["parent_and_candidate_training_updates"]==100 and
            ymod["max_parameters"]==20 and
            ymod["same_12_edge_budget"] is True and
            ymod["strict_slot_gate_no_external_oracle"] is True,
            "TRAINING_FAIRNESS_OR_MODEL_DRIFT")
    gate=f["screen"]
    require(gate["min_absolute_paired_accuracy_gain"]==0.125 and
            gate["min_net_candidate_only_advantage_pairs"]==6 and
            gate["min_worst_family_accuracy"]==0.6 and
            gate["require_no_higher_observation_or_graph_cost"] is True and
            gate["keep_failures_if_no_gain"] is True and
            gate["do_not_retune_after_diagnostic"] is True and
            gate["screen_only_public_synthetic_not_protected_science"] is True,
            "IMPROVEMENT_GATE_RETUNED")
    require(all(f["authority"].get(k) is True for k in (
        "no_codex","no_paid_api","no_chatgpt_work","no_new_scheduler",
        "no_ckb_plane","no_cloudflare","no_mind_palace_mutation",
        "no_wingless_yggdrasil_repo_edits","no_protected_first_use",
        "no_accepted_science","no_optimizer_promotion",
        "no_accepted_ref_mutations","no_native_research_dispatch",
        "no_unattended_GPT_claim")),"UNAUTHORIZED_SCIENCE")
    return f,hashlib.sha256(raw).hexdigest()

def read_parent(source,root,cfg):
    root=Path(root).resolve()
    report=root/cfg["f108_current_run_report"]
    receipt=root/cfg["f108_current_run_receipt"]
    r=report.read_bytes()
    line=receipt.read_bytes().decode("utf-8-sig").strip()
    m=re.fullmatch(r"([a-f0-9]{64})  ([A-Za-z0-9_.-]+)",line)
    require(bool(m) and m.group(2)==report.name and
            hashlib.sha256(r).hexdigest()==m.group(1),
            "F108_REPORT_DIGEST_OR_RECEIPT_TAMPERED")
    d=json.loads(r.decode("utf-8-sig"))
    reference=f108.evaluate(source,root)
    require(d==reference and d.get("source_sha")==source and
            d.get("schema")==f108.REPORT and
            d.get("total_new_public_assessment_pairs")==96 and
            d.get("first_use_authorized") is False and
            d.get("accepted_ref_mutations")==0 and
            d.get("codex_calls")==0 and
            d.get("scientific_originals_dispatched")==0,
            "F108_SOURCE_REPLAY_OR_UNAUTHORIZED_RESULT")
    negative=cfg["f108_negative_precondition"]
    records=d.get("diagnostic_results",[])
    require(len(records)==2,"MISSING_F108_LANE")
    for lane,expected in negative.items():
        hits=[x for x in records if x.get("lane")==lane]
        require(len(hits)==1 and
                hits[0]["candidate_score"]==expected["candidate_score"] and
                hits[0]["unchanged_parent_score"]==expected["parent_score"] and
                hits[0]["cost_parity_satisfied"]==expected["cost_parity_satisfied"] and
                hits[0]["outcome"]==expected["outcome"] and
                not hits[0]["frozen_resource_matched_superiority_gate_passed"],
                "UNEXPECTED_F108_RESULT_NO_UNFROZEN_ADMISSION_"+lane)
    return hashlib.sha256(r).hexdigest()

@dataclass(frozen=True)
class WCase:
    base:wobserve.Case
    offset:int
    family:int

def wing_case(seed,instance=0,diagnostic=False):
    rng=random.Random((seed<<8)+(instance*37)+109)
    offset=seed%4
    query=((seed//4)+instance)%4 if not diagnostic else ((seed//4)+2)%4
    order=list(range(4));rng.shuffle(order)
    target_tag=(query+offset)%4
    distractors=[1.0 if rng.getrandbits(1) else -1.0 for _ in range(4)]
    pos=list(distractors);neg=list(distractors)
    pos[target_tag]=1.0
    neg[target_tag]=-1.0
    base=wobserve.Case(seed,instance,instance,query,tuple(order),
        tuple(pos[t] for t in order),tuple(neg[t] for t in order))
    require(sum(a!=b for a,b in zip(base.positive_values,base.negative_values))==1,
            "INVALID_WING_PAIR")
    return WCase(base,offset,offset)

def wing_cohorts():
    train=tuple(wing_case(seed,inst) for seed in range(66000,66032)
                for inst in range(3))
    diag=tuple(wing_case(seed,diagnostic=True) for seed in range(66048,66096))
    require(len(train)==96 and len(diag)==48 and
            len({(p.base.seed,p.base.specimen) for p in train})==96 and
            {p.base.seed for p in train}.isdisjoint({p.base.seed for p in diag}) and
            {p.offset for p in train}=={0,1,2,3} and
            {p.offset for p in diag}=={0,1,2,3},
            "WING_TRAIN_DIAGNOSTIC_LEAK_OR_MISSING_GROUP")
    return train,diag

class LearnedSourceRouting:
    """Trainable 64 conditional route logits; reads exactly one evidence value.

    At training, paired labels support BCE gradient on soft attention; at
    inference labels and unselected observation *values* are inaccessible.
    """
    parameters=64
    def __init__(self):
        self.routing=[0.025*((i*7)%11-5) for i in range(64)]
        self.steps=0
    def weights(self,p):
        row=(p.offset*4+p.base.query_depth)*4
        x=[self.routing[row+tag] for tag in p.base.observation_depths]
        return wobserve.softmax(x)
    def train(self,pairs):
        pairs=tuple(pairs)
        require(len(pairs)==96 and self.steps==0,"ROUTING_TRAINING_BUDGET")
        for _ in range(100):
            grads=[0.]*64
            for p in pairs:
                weights=self.weights(p)
                row=(p.offset*4+p.base.query_depth)*4
                for vals,label in ((p.base.positive_values,1),
                                   (p.base.negative_values,0)):
                    mean=sum(w*v for w,v in zip(weights,vals))
                    err=wobserve.sigmoid(3*mean)-label
                    for i,tag in enumerate(p.base.observation_depths):
                        grads[row+tag]+=err*3*weights[i]*(vals[i]-mean)
            rate=4./(2*len(pairs))
            self.routing=[max(-12.,min(12.,val-rate*g))
                          for val,g in zip(self.routing,grads)]
            self.steps+=1
        return self
    def selected_slot(self,p):
        weights=self.weights(p)
        return max(range(4),key=lambda j:weights[j])
    def predicts(self,p,values):
        require(len(values)==4,"ROUTE_BUDGET_DRIFT")
        return values[self.selected_slot(p)]>0

def ygg_case(seed,instance=0,diagnostic=False):
    rng=random.Random((seed<<8)+instance*37+109)
    nodes=list(range(1,12))
    rng.shuffle(nodes)
    target=12
    paths=[(0,*nodes[4*j:4*j+3],target) for j in range(3)]
    # Three four-hop paths, same query role, two incompatible distractor
    # paths; all 12 edges are used in both arms.
    edges=[edge for path in paths for edge in zip(path[:-1],path[1:])]
    roles=tuple(rng.randrange(4) for _ in range(4))
    slots=[rng.randrange(16) for _ in range(5)]
    m0,m1,m2,m3,m4=slots
    main=[(m0,m1),(m1,m2),(m2,m3),(m3,m4)]
    wrong=[]
    for k in range(2):
        x,y,z,t,u=[rng.randrange(16) for _ in range(5)]
        seq=[(x,y),(y,z),(z,t),(t,u)]
        position=(seed+instance+k)%3+1
        seq[position]=( (seq[position][0]+1+((seed+k)%15))%16,
                       seq[position][1])
        wrong+=seq
    vars_=main+wrong
    negative=list(vars_)
    idx=1+(seed+instance)%3
    lhs,rhs=negative[idx]
    negative[idx]=((lhs+1+(seed%15))%16,rhs)
    order=list(range(12));rng.shuffle(order)
    p=ybind.Pair(seed,0 if not diagnostic else 1,instance,
                 tuple(edges[j] for j in order),
                 tuple(roles[j%4] for j in order),
                 tuple(vars_[j] for j in order),
                 tuple(negative[j] for j in order),
                 roles,0,target,(seed+instance)%3)
    require(len(set(p.edges))==12 and
            ybind.coded_exact_binding_oracle(p,p.positive_variables) and
            not ybind.coded_exact_binding_oracle(p,p.negative_variables),
            "YGG_TRUE_LABEL_INVALID")
    return p

def ygg_cohorts():
    train=tuple(ygg_case(seed,i) for seed in range(66100,66132) for i in range(3))
    diag=tuple(ygg_case(seed,diagnostic=True) for seed in range(66148,66196))
    require(len(train)==96 and len(diag)==48 and
            len({(p.seed,p.specimen) for p in train})==96 and
            {p.seed for p in train}.isdisjoint({p.seed for p in diag}),
            "YGG_NEW_COHORT_LEAK")
    return train,diag

def strict_slot_predict(model,p,values):
    """Learned role gates + strict source slot matching; no oracle invocation."""
    state={(p.source,-1):1.}
    for hop,query in enumerate(p.query_roles):
        nxt={}
        for (u,v),role,(lhs,rhs) in zip(p.edges,p.roles,values):
            gate=ybind.sigmoid(model.role[4*query+role])
            for (node,previous),mass in state.items():
                if node!=u or (hop>0 and previous!=lhs):continue
                key=(v,rhs)
                nxt[key]=nxt.get(key,0.)+mass*gate
        state=nxt
    mass=sum(s for (node,_),s in state.items() if node==p.target)
    return ybind.sigmoid(model.scale*mass+model.bias)>=.5

def lane_result(lane,cfg):
    if lane=="Wingless":
        train,diag=wing_cohorts()
        parent=wobserve.LearnedObservationSelector().fit(
            tuple(p.base for p in train))
        blind=wobserve.LearnedObservationSelector(depth_blind=True).fit(
            tuple(p.base for p in train))
        proposed=LearnedSourceRouting().train(train)
        candidate=lambda p,v:proposed.predicts(p,v)
        original=lambda p,v:parent.predicts(p.base,v)
        blindpred=lambda p,v:blind.predicts(p.base,v)
        oracle=lambda p,v:v[p.base.observation_depths.index(
            (p.base.query_depth+p.offset)%4)]>0
        vals=lambda p:(p.base.positive_values,p.base.negative_values)
        cost_p=cost_c=1
        family=lambda p:str(p.family)
        fit_steps=[parent.training_updates,proposed.steps]
        parameters=[parent.parameters,proposed.parameters]
    else:
        train,diag=ygg_cohorts()
        old=ybind.public_cohorts()
        parent=ybind.LearnedVariableBinder().fit(old[0]+old[1])
        blind=ybind.LearnedVariableBinder(blind=True).fit(old[0]+old[1])
        proposed=parent
        candidate=lambda p,v:strict_slot_predict(proposed,p,v)
        original=lambda p,v:parent.predicts(p,v)
        blindpred=lambda p,v:blind.predicts(p,v)
        oracle=lambda p,v:ybind.coded_exact_binding_oracle(p,v)
        vals=lambda p:(p.positive_variables,p.negative_variables)
        cost_p=cost_c=12
        family=lambda p:str(p.conflict_site)
        fit_steps=[parent.training_updates,parent.training_updates]
        parameters=[parent.parameter_count,parent.parameter_count]
    require(len(diag)==48 and fit_steps==[100,100] and
            cost_c<=cost_p and parameters[1]<=64,
            "UNFAIR_NEW_MECHANISM_COST_OR_FIT")
    details=[]
    for p in diag:
        pos,neg=vals(p)
        require(oracle(p,pos) and not oracle(p,neg),"INCORRECT_STRONG_CONTROL")
        ca=bool(candidate(p,pos) and not candidate(p,neg))
        pa=bool(original(p,pos) and not original(p,neg))
        ba=bool(blindpred(p,pos) and not blindpred(p,neg))
        details.append(dict(seed=p.base.seed if lane=="Wingless" else p.seed,
                            family=family(p),
                            generated_candidate_both_correct=ca,
                            original_parent_both_correct=pa,
                            independent_blind_both_correct=ba,
                            generated_candidate_negative_false_positive=bool(candidate(p,neg)),
                            original_parent_negative_false_positive=bool(original(p,neg))))
    ca=sum(x["generated_candidate_both_correct"] for x in details)
    pa=sum(x["original_parent_both_correct"] for x in details)
    ba=sum(x["independent_blind_both_correct"] for x in details)
    ca_only=sum(x["generated_candidate_both_correct"] and not
                x["original_parent_both_correct"] for x in details)
    pa_only=sum(x["original_parent_both_correct"] and not
                x["generated_candidate_both_correct"] for x in details)
    fs={}
    for k in sorted({x["family"] for x in details}):
        subset=[x for x in details if x["family"]==k]
        fs[k]=sum(x["generated_candidate_both_correct"] for x in subset)/len(subset)
    gate=cfg["screen"]
    pass_gate=(ca-pa>=48*gate["min_absolute_paired_accuracy_gain"] and
               ca_only-pa_only>=gate["min_net_candidate_only_advantage_pairs"] and
               min(fs.values())>=gate["min_worst_family_accuracy"] and cost_c<=cost_p)
    return dict(lane=lane,training_pairs=96,diagnostic_pairs=48,
                candidate_parameters=parameters[1],parent_parameters=parameters[0],
                candidate_training_steps=fit_steps[1],parent_training_steps=fit_steps[0],
                candidate_resource_cost=cost_c,parent_resource_cost=cost_p,
                parent_score=pa/48,candidate_score=ca/48,blind_score=ba/48,
                exact_control_score=1.,candidate_correct_pairs=ca,parent_correct_pairs=pa,
                candidate_only_correct=ca_only,parent_only_correct=pa_only,
                net_pair_advantage=ca_only-pa_only,
                worst_candidate_family_accuracy=min(fs.values()),
                family_scores=fs,
                all_paired_records=details,
                resource_matched_public_screen_passed=pass_gate,
                disposition=("POSITIVE_PUBLIC_DEV_SCREEN_NOT_INDEPENDENT_SCIENCE"
                             if pass_gate else "NO_DEMONSTRATED_GAIN_RETAIN_NEGATIVE"),
                no_scientific_permission=True)

def evaluate(source,evidence_root):
    require(type(source) is str and SOURCE.fullmatch(source) is not None and
            (not os.environ.get("GITHUB_SHA") or os.environ["GITHUB_SHA"]==source),
            "EXACT_CURRENT_GITHUB_SHA_REQUIRED")
    cfg,freeze_sha=frozen()
    source_digest=read_parent(source,evidence_root,cfg)
    lanes=[lane_result("Wingless",cfg),lane_result("Yggdrasil",cfg)]
    return dict(schema=REPORT,source_sha=source,
                freeze_sha256=freeze_sha,parent_F108_sha256=source_digest,
                evidence_class="PUBLIC_SYNTHETIC_FROZEN_RESOURCE_MATCHED_NO_SCIENCE",
                prior_F108_negative_results_preserved=True,
                all_arm_and_per_pair_outcomes_preserved=True,
                true_resource_matched_improvement_lanes=[
                    x["lane"] for x in lanes if x["resource_matched_public_screen_passed"]],
                lanes=lanes,
                interpretation="DEVELOPMENT_ONLY_NOT_RECURSIVE_SELF_IMPROVEMENT",
                scientific_originals_executed=0,independent_science_accepted=0,
                first_use_authorized=False,accepted_ref_mutations=0,
                optimizer_promotions=0,native_science_dispatches=0,
                codex_calls=0,paid_model_api_calls=0,chatgpt_work_tasks=0,
                new_schedulers=0,ckb_plane_contact=False,cloudflare_writes=0)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source-ref",required=True)
    p.add_argument("--evidence-root",required=True)
    a=p.parse_args()
    print(json.dumps(evaluate(a.source_ref,a.evidence_root),
                     sort_keys=True,separators=(",",":")))

if __name__=="__main__":
    try: main()
    except (Quarantined,f108.Quarantined,ybind.Rejected,wobserve.Rejected,
            TypeError,ValueError,KeyError,OSError) as error:
        print("FORGE_F109_FAILURE_DRIVEN_PUBLIC_DEVELOPMENT=QUARANTINED "+str(error),file=sys.stderr)
        raise SystemExit(1)
