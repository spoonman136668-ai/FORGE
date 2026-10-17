"""F110: equal-parameter controls, three frozen public transfer blocks per lane.

No adaptive source or threshold tuning. The F109 program is evaluated unchanged.
The 64-weight query-only comparator is trained independently on exactly the same
96 public cases and 100 updates; unlike F109 it cannot condition on source offset.
This is an architectural ablation, NOT proof over arbitrary equal-size models.
"""
import argparse
from dataclasses import replace
import hashlib
import json
import math
import os
from pathlib import Path
import random
import re
import sys

import f103_yggdrasil_public_binding as ybind
import f104_wingless_public_observations as wobserve
import f109_failure_driven_mechanisms as f109

ROOT=Path(__file__).resolve().parents[1]
FREEZE=ROOT/"reference/research-intake/f110-capacity-matched-transfer-freeze.json"
FREEZE_BLOB="e191c4b3959d580b15390bd2eb8dca3b21eb2fc7"
F109_BLOB="5987de95ed7bf34da9c6e56003bda125cabae488"
PARENT="1d3e0820002ed931f2a1a119ce5e52cd1467e9c8"
SCHEMA="forge.autonomy.f110.capacity-matched-multiblock-transfer-freeze.v1"
REPORT="forge.autonomy.f110.capacity-matched-frozen-three-block-public-transfer.v1"
HEX40=re.compile(r"^[0-9a-f]{40}$")

class Quarantined(ValueError):pass
def need(ok,why):
    if not ok:raise Quarantined("F110_"+why)
def gitblob(raw):
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
def canonical(path):
    return Path(path).read_bytes().replace(b"\r\n",b"\n")

def frozen():
    raw=canonical(FREEZE)
    need(gitblob(raw)==FREEZE_BLOB and
         gitblob(canonical(ROOT/"nativeevidence/f109_failure_driven_mechanisms.py"))==
         F109_BLOB,"SOURCE_PREREGISTRATION_DRIFT")
    f=json.loads(raw)
    need(f.get("schema")==SCHEMA and
         f.get("parent_f109_exact_head_sha")==PARENT and
         f.get("parent_f109_implementation_blob")==F109_BLOB and
         f.get("parent_f109_protocol_blob")=="bb90fa23ba454f7a8a337babe3185f8f7d06986a",
         "F109_ANCESTRY_DRIFT")
    req=f.get("source_precondition",{})
    need(req=={
        "Wingless":{"candidate_correct_pairs":48,"parent_correct_pairs":12,
                    "resource_matched_public_screen_passed":True},
        "Yggdrasil":{"candidate_correct_pairs":48,"parent_correct_pairs":48,
                     "resource_matched_public_screen_passed":False}},
         "F109_POSITIVE_OR_NEGATIVE_REWRITTEN")
    t=f.get("frozen_parent_training",{})
    need(t.get("steps_exactly")==100 and
         t.get("no_test_condition_training") is True and
         t.get("candidate_parameter_count")==64 and
         t.get("capacity_control_parameter_count")==64 and
         t.get("capacity_control_offset_feature_accessible_but_not_conditioning_attentional_weights") is True and
         t.get("candidate_inference")=="one_actual_observation_value" and
         t.get("capacity_control_inference")==
             "aggregate_head_attentions_choose_one_observation_value" and
         t.get("capacity_control_training")==
             "same_F109_96_training_pairs_and_100_SGD_updates",
         "CAPACITY_OR_TRAINING_RULE_DRIFT")
    blocks=f.get("independent_public_development_blocks",{})
    w=blocks.get("Wingless")
    y=blocks.get("Yggdrasil")
    need(type(w) is list and type(y) is list and
         [v.get("block") for v in w]==["W-A","W-B","W-C"] and
         [v.get("seeds") for v in w]==[[66200,66247],[66300,66347],[66400,66447]] and
         [v.get("queried_signal_abs") for v in w]==[1.0,1.0,0.25] and
         [v.get("distractor_abs") for v in w]==[[1.0],[2.0,3.0],[1.0,2.0]] and
         [v.get("block") for v in y]==["Y-A","Y-B","Y-C"] and
         [v.get("seeds") for v in y]==[[66500,66547],[66600,66647],[66700,66747]] and
         all(v.get("pairs")==48 for v in w+y) and
         blocks.get("all_seeds_disjoint_prior_F101_to_F109") is True and
         blocks.get("no_new_samples_or_seeds_after_results") is True and
         blocks.get("counterfactual_differ_in_exactly_one_requested_value_or_variable_argument") is True,
         "FROZEN_COHORT_DRIFT")
    outcome=f["frozen_outcomes"]
    ws=outcome["Wingless"]
    need(ws["minimum_candidate_paired_accuracy_each_block"]==0.75 and
         ws["minimum_gain_over_64_parameter_capacity_control_each_block"]==0.125 and
         ws["minimum_pooled_net_candidate_only_correct_vs_capacity_control"]==18 and
         ws["minimum_worst_offset_family_accuracy"]==0.60 and
         ws["candidate_reads"]==ws["control_reads"]==1 and
         ws["minimum_metadata_offset_tamper_accuracy_drop"]==0.20 and
         ws["no_parameter_efficiency_claim_if_64_vs_18"] is True and
         outcome["Yggdrasil"]["report_all_144_new_pairs"] is True and
         outcome["Yggdrasil"]["strict_superiority_needs_pooled_net_gain_at_least_18"]==18 and
         outcome["no_test_failure_for_negative_scientific_outcome"] is True and
         outcome["no_hindsight_model_reselection"] is True and
         outcome["no_retraining_after_diagnostic"] is True,
         "POST_HOC_TRANSFER_SCREEN_DRIFT")
    for field in ("no_codex","no_paid_api","no_chatgpt_work","no_cloudflare_write",
                  "no_ckb_plane_contact","no_mind_palace_write","no_new_scheduler",
                  "no_accepted_refs","no_sci_first_use","no_scientific_originals",
                  "no_independent_acceptance","no_optimizer_promotion",
                  "no_native_research_dispatch","no_wingless_yggdrasil_repo_mutation",
                  "no_unattended_GPT_research_claim"):
        need(f["safety"].get(field) is True,"UNAUTHORIZED_"+field.upper())
    return f,hashlib.sha256(raw).hexdigest()

def authentic_f109(source,root,cfg):
    root=Path(root).resolve()
    report=root/cfg["source_report"]
    receipt=root/cfg["source_receipt"]
    raw=report.read_bytes()
    line=receipt.read_bytes().decode("utf-8-sig").strip()
    match=re.fullmatch(r"([0-9a-f]{64})  ([A-Za-z0-9_.-]+)",line)
    need(bool(match) and match.group(2)==report.name and
         hashlib.sha256(raw).hexdigest()==match.group(1),
         "PARENT_F109_RECEIPT_DRIFT")
    data=json.loads(raw.decode("utf-8-sig"))
    expected=f109.evaluate(source,root)
    need(data==expected and data.get("schema")==f109.REPORT and
         data.get("source_sha")==source and
         data.get("prior_F108_negative_results_preserved") is True and
         data.get("first_use_authorized") is False and
         data.get("independent_science_accepted")==0 and
         data.get("accepted_ref_mutations")==0 and data.get("codex_calls")==0,
         "F109_EVIDENCE_REPLAY_OR_AUTHORITY_DRIFT")
    expected_lanes=cfg["source_precondition"]
    for lane,pre in expected_lanes.items():
        rows=[x for x in data.get("lanes",[]) if x.get("lane")==lane]
        need(len(rows)==1 and
             rows[0].get("candidate_correct_pairs")==pre["candidate_correct_pairs"] and
             rows[0].get("parent_correct_pairs")==pre["parent_correct_pairs"] and
             rows[0].get("resource_matched_public_screen_passed")==
                    pre["resource_matched_public_screen_passed"],
             "F109_PRECONDITION_CHANGED_"+lane)
    return hashlib.sha256(raw).hexdigest()

class CapacityMatchedQueryOnly:
    """64 independently trainable scalars: four query-conditioned attention heads.

    Public offset metadata may be supplied but cannot interact with the logits.
    The four heads' soft distributions are averaged. At inference, ONE actual
    evidence value is accessed, just as in the F109 64-parameter candidate.
    """
    parameters=64
    def __init__(self):
        self.logits=[.025*((i*11+3)%13-6) for i in range(64)]
        self.steps=0
    def row(self,p,head):
        # query only -- offset is deliberately not used for query-head ablation
        need(0<=p.offset<4,"BAD_VISIBLE_OFFSET")
        return (head*4+p.base.query_depth)*4
    def weights(self,p):
        means=[0.]*4
        for head in range(4):
            row=self.row(p,head)
            one=wobserve.softmax([self.logits[row+t] for t in p.base.observation_depths])
            for j,value in enumerate(one):means[j]+=value/4
        return means
    def train(self,pairs):
        pairs=tuple(pairs)
        need(len(pairs)==96 and self.steps==0,"CAPACITY_CONTROL_TRAINING_BUDGET_DRIFT")
        for _ in range(100):
            grads=[0.]*64
            for p in pairs:
                heads=[]
                for head in range(4):
                    row=self.row(p,head)
                    heads.append(wobserve.softmax(
                        [self.logits[row+t] for t in p.base.observation_depths]))
                for values,label in ((p.base.positive_values,1),
                                     (p.base.negative_values,0)):
                    mean=sum(sum(weights[j]*values[j] for j in range(4))/4
                             for weights in heads)
                    err=wobserve.sigmoid(3*mean)-label
                    for head,weights in enumerate(heads):
                        specific=sum(weights[j]*values[j] for j in range(4))
                        row=self.row(p,head)
                        for j,tag in enumerate(p.base.observation_depths):
                            grads[row+tag]+=(err*3/4)*weights[j]*(values[j]-specific)
            step=4/(len(pairs)*2)
            self.logits=[max(-12.,min(12.,v-step*g)) for v,g in zip(self.logits,grads)]
            self.steps+=1
        return self
    def slot(self,p):
        w=self.weights(p)
        return max(range(4),key=lambda k:w[k])
    def predicts(self,p,values):
        need(len(values)==4,"CONTROL_MUST_READ_ONE")
        return values[self.slot(p)]>0

def wing_case(seed,block):
    rng=random.Random((seed<<8)+block*1009+110)
    offset=seed%4
    query=(seed//4 + block*2)%4
    order=list(range(4));rng.shuffle(order)
    tagged=(query+offset)%4
    signs=[1 if rng.getrandbits(1) else -1 for _ in range(4)]
    # Generator is frozen before inspecting outcomes; target sign flip is
    # the only paired difference, and magnitudes differ across 3 families.
    magnitude=[(1.,),(2.,3.),(1.,2.)][block]
    values=[float(signs[k]*magnitude[(k+seed)%len(magnitude)]) for k in range(4)]
    plus=values.copy();minus=values.copy()
    amplitude=(1.,1.,.25)[block]
    plus[tagged]=amplitude;minus[tagged]=-amplitude
    case=wobserve.Case(seed,block,0,query,tuple(order),
                        tuple(plus[tag] for tag in order),
                        tuple(minus[tag] for tag in order))
    need(sum(a!=b for a,b in zip(case.positive_values,case.negative_values))==1 and
         case.positive_values[case.observation_depths.index(tagged)]>0 and
         case.negative_values[case.observation_depths.index(tagged)]<0,
         "NONCOUNTERFACTUAL_W_TRANSFER")
    return f109.WCase(case,offset,offset)

def wing_blocks():
    groups=[]
    for i,(lo,hi) in enumerate(((66200,66247),(66300,66347),(66400,66447))):
        rows=tuple(wing_case(seed,i) for seed in range(lo,hi+1))
        need(len(rows)==48 and {x.offset for x in rows}=={0,1,2,3} and
             len({p.base.seed for p in rows})==48,"INVALID_W_TRANSFER_BLOCK")
        groups.append(rows)
    need(len({p.base.seed for group in groups for p in group})==144,
         "W_TRANSFER_SEEDS_NOT_DISJOINT")
    return tuple(groups)

def ygg_blocks():
    groups=[]
    for i,(lo,hi) in enumerate(((66500,66547),(66600,66647),(66700,66747))):
        rows=tuple(f109.ygg_case(seed,instance=i,diagnostic=True)
                   for seed in range(lo,hi+1))
        need(len(rows)==48 and
             all(ybind.coded_exact_binding_oracle(p,p.positive_variables) and
                 not ybind.coded_exact_binding_oracle(p,p.negative_variables)
                 for p in rows),"NEW_YGG_GENERATOR_GROUND_TRUTH")
        groups.append(rows)
    return tuple(groups)

def stats(case_groups,lane,arms,offset_tamper=False):
    # Every arm is evaluated on the SAME positive/negative pair.
    reports=[]
    for i,cases in enumerate(case_groups):
        per=[]
        for case in cases:
            if lane=="Wingless":
                pos,neg=case.base.positive_values,case.base.negative_values
                seed=case.base.seed
                family=str(case.offset)
                oracle=lambda v:v[case.base.observation_depths.index(
                    (case.base.query_depth+case.offset)%4)]>0
            else:
                pos,neg=case.positive_variables,case.negative_variables
                seed=case.seed
                family=str(case.conflict_site)
                oracle=lambda v:ybind.coded_exact_binding_oracle(case,v)
            need(oracle(pos) and not oracle(neg),"BAD_STRONG_CONTROL_OR_TEST_LABEL")
            decisions={key:bool(pred(case,pos) and not pred(case,neg))
                       for key,pred in arms.items()}
            per.append(dict(seed=seed,block=i,family=family,arms=decisions))
        paired={key:sum(x["arms"][key] for x in per) for key in arms}
        subgroup={}
        for family in sorted({x["family"] for x in per}):
            subset=[x for x in per if x["family"]==family]
            subgroup[family]={key:sum(x["arms"][key] for x in subset)/len(subset)
                              for key in arms}
        reports.append(dict(block=i,pairs=len(per),paired_correct=paired,
                            family_accuracy=subgroup,all_paired_decisions=per))
    return reports

def wing_eval(cfg):
    training,old_diag=f109.wing_cohorts()
    original=f109.LearnedSourceRouting().train(training)
    control=CapacityMatchedQueryOnly().train(training)
    old=wobserve.LearnedObservationSelector().fit(tuple(p.base for p in training))
    blind=wobserve.LearnedObservationSelector(depth_blind=True).fit(
        tuple(p.base for p in training))
    need((original.steps,control.steps,old.training_updates,blind.training_updates)==
         (100,100,100,100) and
         original.parameters==control.parameters==64,"UNFAIR_CAPACITY_CONTROL")
    groups=wing_blocks()
    arms={
      "learned_offset_routing_64":lambda p,v:original.predicts(p,v),
      "capacity_matched_query_only_64":lambda p,v:control.predicts(p,v),
      "original_query_depth_18":lambda p,v:old.predicts(p.base,v),
      "query_blind_18":lambda p,v:blind.predicts(p.base,v),
      "metadata_offset_tamper":lambda p,v:original.predicts(
          replace(p,offset=(p.offset+1)%4),v)
    }
    blocks=stats(groups,"Wingless",arms)
    rows=[x for block in blocks for x in block["all_paired_decisions"]]
    wins=sum(x["arms"]["learned_offset_routing_64"] and not
             x["arms"]["capacity_matched_query_only_64"] for x in rows)
    losses=sum(x["arms"]["capacity_matched_query_only_64"] and not
               x["arms"]["learned_offset_routing_64"] for x in rows)
    by_offset={}
    for offset in "0123":
        subset=[x for x in rows if x["family"]==offset]
        by_offset[offset]=sum(x["arms"]["learned_offset_routing_64"] for x in subset)/len(subset)
    candidate=sum(x["arms"]["learned_offset_routing_64"] for x in rows)/144
    tamper=sum(x["arms"]["metadata_offset_tamper"] for x in rows)/144
    gate=cfg["frozen_outcomes"]["Wingless"]
    passed=(all(b["paired_correct"]["learned_offset_routing_64"]/48>=
                gate["minimum_candidate_paired_accuracy_each_block"] and
                (b["paired_correct"]["learned_offset_routing_64"]-
                 b["paired_correct"]["capacity_matched_query_only_64"])/48>=
                gate["minimum_gain_over_64_parameter_capacity_control_each_block"]
                for b in blocks) and
            wins-losses>=gate["minimum_pooled_net_candidate_only_correct_vs_capacity_control"] and
            min(by_offset.values())>=gate["minimum_worst_offset_family_accuracy"] and
            candidate-tamper>=gate["minimum_metadata_offset_tamper_accuracy_drop"])
    return dict(lane="Wingless",training_pairs=96,training_steps_each=100,
                candidate_parameters=64,matched_control_parameters=64,
                candidate_observation_reads=1,matched_control_observation_reads=1,
                original_18_parameter_baseline_included=True,
                blocks=blocks,total_assessment_pairs=144,
                candidate_only_correct=wins,capacity_control_only_correct=losses,
                net_capacity_control_paired_advantage=wins-losses,
                candidate_pooled_accuracy=candidate,
                offset_tampered_pooled_accuracy=tamper,
                worst_offset_group_accuracy=min(by_offset.values()),
                capacity_matched_public_transfer_passed=passed,
                disposition=("BOUNDED_PUBLIC_TRANSFER_ADVANTAGE_NOT_SCIENCE" if passed
                             else "CAPACITY_MATCHED_TRANSFER_NOT_DEMONSTRATED_RETAIN_ALL_NEGATIVES"))

def ygg_eval(cfg):
    prior=ybind.public_cohorts()
    parent=ybind.LearnedVariableBinder().fit(prior[0]+prior[1])
    blind=ybind.LearnedVariableBinder(blind=True).fit(prior[0]+prior[1])
    groups=ygg_blocks()
    arms={
      "soft_slot_parent_20":lambda p,v:parent.predicts(p,v),
      "strict_slot_candidate_20":lambda p,v:f109.strict_slot_predict(parent,p,v),
      "trained_variable_blind_20":lambda p,v:blind.predicts(p,v)
    }
    blocks=stats(groups,"Yggdrasil",arms)
    rows=[x for b in blocks for x in b["all_paired_decisions"]]
    wins=sum(x["arms"]["strict_slot_candidate_20"] and
             not x["arms"]["soft_slot_parent_20"] for x in rows)
    losses=sum(x["arms"]["soft_slot_parent_20"] and
               not x["arms"]["strict_slot_candidate_20"] for x in rows)
    passed=(wins-losses>=cfg["frozen_outcomes"]["Yggdrasil"][
              "strict_superiority_needs_pooled_net_gain_at_least_18"] and
            min(b["paired_correct"]["strict_slot_candidate_20"]/48
                for b in blocks)>=0.6)
    return dict(lane="Yggdrasil",training_steps_each=100,
                candidate_parameters=20,parent_parameters=20,
                candidate_graph_edges=12,parent_graph_edges=12,
                blocks=blocks,total_assessment_pairs=144,
                candidate_only_correct=wins,parent_only_correct=losses,
                pooled_net_paired_advantage=wins-losses,
                strict_slot_transfer_superiority_passed=passed,
                disposition=("BOUNDED_PUBLIC_TRANSFER_ADVANTAGE_NOT_SCIENCE" if passed
                             else "CAPACITY_MATCHED_TRANSFER_NOT_DEMONSTRATED_RETAIN_ALL_NEGATIVES"))

def evaluate(source,evidence_root):
    need(type(source) is str and HEX40.fullmatch(source) is not None and
         (not os.environ.get("GITHUB_SHA") or os.environ["GITHUB_SHA"]==source),
         "EXACT_CURRENT_GITHUB_SHA_REQUIRED")
    cfg,freeze_digest=frozen()
    parent_digest=authentic_f109(source,evidence_root,cfg)
    wings=wing_eval(cfg)
    ygg=ygg_eval(cfg)
    return dict(schema=REPORT,source_sha=source,freeze_sha256=freeze_digest,
                authenticated_F109_report_sha256=parent_digest,
                evidence_class="THREE_PUBLIC_FROZEN_TRANSFER_BLOCKS_NOT_INDEPENDENT_SCIENCE",
                frozen_conditions_per_lane=3,public_pairs_per_lane=144,
                all_f109_positive_and_negative_findings_preserved=True,
                all_diagnostic_arm_decisions_preserved=True,
                lanes=[wings,ygg],
                independently_accepted_science=0,protected_first_use_authorized=False,
                original_science_executed=0,accepted_ref_mutations=0,
                optimizer_promotions=0,native_scientific_dispatches=0,
                codex_calls=0,paid_model_api_calls=0,chatgpt_work_tasks=0,
                new_scheduler_created=False,ckb_plane_contact=False,cloudflare_writes=0,
                no_gpt_autonomous_science_claim=True)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source-ref",required=True)
    p.add_argument("--evidence-root",required=True)
    args=p.parse_args()
    print(json.dumps(evaluate(args.source_ref,args.evidence_root),sort_keys=True,separators=(",",":")))

if __name__=="__main__":
    try:main()
    except (Quarantined,f109.Quarantined,ybind.Rejected,wobserve.Rejected,
            ValueError,KeyError,TypeError,OSError) as error:
        print("FORGE_F110_CAPACITY_MATCHED_TRANSFER=QUARANTINED "+str(error),file=sys.stderr)
        raise SystemExit(1)
