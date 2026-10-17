"""F106 automatic current-run F105 advisory -> fresh PUBLIC DEV challenge -> feedback.

Uses only frozen C2 parent models, existing hosted CPU training and new frozen
PUBLIC development cohorts. No protected science, GPT inference, native experiment
dispatch, model API or optimizer promotion. Preserve negative findings.
"""
import argparse
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import random
import re
import sys

import f103_yggdrasil_public_binding as ybind
import f104_wingless_public_observations as wobserve
import f105_research_feedback as feedback

ROOT=Path(__file__).resolve().parents[1]
FROZEN=ROOT/"reference/research-intake/f106-public-challenge-freeze.json"
FROZEN_BLOB="dadea0c72f51d683d94b9c7e12fbafd044dd49c9"
F105_BLOB="e975e20263a633e73bfbbfe18733cf5efcac7cf4"
F104_BLOB="221007d8428b13a64c57017a3c35ecb288da4181"
F103_BLOB="1deab41125d1c00bd90207095c4b31197de408b2"
PARENT="dfd8b2f2f3056598331aee6c41e0d40327120773"
SCHEMA="forge.autonomy.f106.frozen-public-challenge-execution.v1"
REPORT="forge.autonomy.f106.public-new-condition-automatic-research-feedback.v1"
SHA=re.compile(r"^[0-9a-f]{40}$")
HEX64=re.compile(r"^[0-9a-f]{64}$")

class Quarantined(ValueError): pass
def must(condition,reason):
    if not condition:raise Quarantined("F106_"+reason)
def gitblob(data):
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()
def read(path,limit=90000):
    raw=Path(path).read_bytes()
    must(0<len(raw)<=limit,"UNBOUNDED_OR_EMPTY_SOURCE")
    return raw
def gitbytes(path):
    return read(path,300000).replace(b"\r\n",b"\n")
def frozen():
    raw=gitbytes(FROZEN)
    must(gitblob(raw)==FROZEN_BLOB,"FROZEN_PROTOCOL_HASH_DRIFT")
    must(gitblob(gitbytes(ROOT/"nativeevidence/f105_research_feedback.py"))==F105_BLOB and
         gitblob(gitbytes(ROOT/"nativeevidence/f104_wingless_public_observations.py"))==F104_BLOB and
         gitblob(gitbytes(ROOT/"nativeevidence/f103_yggdrasil_public_binding.py"))==F103_BLOB,
         "ANCESTOR_MODEL_SOURCE_DRIFT")
    f=feedback.json_distinct(raw)
    must(f.get("schema")==SCHEMA and
         f.get("parent_f105_exact_branch_head")==PARENT and
         f.get("parent_f105_policy_git_blob_sha")=="9a835dc724efa6bca365d838a293a10e7a8f47c1",
         "ANCESTRY_DRIFT")
    req=f.get("requirements",{})
    must(req.get("only_qualified_prior_C2_successors")=={
        "Wingless":{"candidate":"W100-C2",
                    "hypothesis":"CONFLICTING_OBSERVATION_AND_BUDGET_TRANSFER"},
        "Yggdrasil":{"candidate":"Y100-C2",
                    "hypothesis":"ALIASING_AND_VARIABLE_REUSE_TRANSFER"}
    } and req.get("on_unexpected_selection")=="QUARANTINE_UNSUPPORTED_MECHANISM_NO_EXECUTION" and
         req.get("on_negative_result")=="RETAIN_FULL_SCORES_AND_PROPOSE_REPAIR_WITHOUT_TUNING" and
         req.get("on_positive_result")=="PROPOSE_DIFFERENT_UNSEEN_DEVELOPMENT_TRANSFER_NO_POLICY_PROMOTION" and
         all(req.get(k) is True for k in (
             "require_current_run_source_sha",
             "require_f105_freeze_sha_match",
             "require_f105_verified_four_prior_evidence",
             "require_f105_decision_selected_by_frozen_policy")),
         "SELECTION_OR_FEEDBACK_POLICY_DRIFT")
    training=f.get("training",{})
    must(training.get("use_only_existing_frozen_parent_training_blocks") is True and
         training.get("seed_reuse_in_new_challenge") is False and
         training.get("max_trainable_parameters_per_lane")==128 and
         training.get("optimizer_updates_exactly")==100 and
         training.get("no_retrain_or_tune_after_new_diagnostic") is True,
         "RETRAINING_POLICY_DRIFT")
    cohorts=f.get("new_public_challenge",{})
    w=cohorts.get("Wingless",{})
    y=cohorts.get("Yggdrasil",{})
    must(w.get("fresh_seed_block")==[64200,64223] and w.get("cases_per_seed")==2 and
         w.get("total_paired_counterfactuals")==48 and
         w.get("observation_budget")==1 and
         w.get("pair_diff")=="single_queried_depth_evidence_value_only" and
         y.get("fresh_seed_block")==[64300,64323] and y.get("cases_per_seed")==2 and
         y.get("total_paired_counterfactuals")==48 and
         y.get("edge_budget")==12 and y.get("max_variable_slots")==16 and
         y.get("pair_diff")=="single_main_path_variable_argument_change_only" and
         y.get("exact_coded_binding_oracle_only_for_ground_truth_and_strong_control") is True,
         "NEW_PUBLIC_CHALLENGE_DRIFT")
    scores=f.get("scores",{})
    must(scores.get("frozen_development_screen_only")=={
        "minimum_paired_accuracy":0.75,
        "minimum_gain_over_blind":0.15,
        "minimum_worst_family_accuracy":0.6} and
         scores.get("negative_result_does_not_abort_evidence_receipt") is True and
         scores.get("screen_is_not_scientific_acceptance") is True,
         "SCREEN_TUNING_OR_FALSE_SCIENCE")
    flags=f.get("authority",{})
    must(all(flags.get(k) is True for k in (
        "no_new_protected_scientific_original","no_protected_first_use",
        "no_auto_native_wingless_yggdrasil_dispatch",
        "no_accepted_ref_mutations","no_optimizer_promotion",
        "no_codex","no_paid_api_or_work_task","no_ckb_plane_integration",
        "no_cloudflare_changes","no_new_model_or_external_inference_service",
        "no_wingless_or_yggdrasil_repo_writes",
        "development_only_not_independent_science")),
        "PROTECTED_EXECUTION_AUTHORITY_DRIFT")
    return f,hashlib.sha256(raw).hexdigest()

def f105_current_run(source_sha,root,cfg):
    must(root.is_dir(),"F105_EVIDENCE_ROOT_NOT_FOUND")
    receipt=root/cfg["decision_sha"]
    report=root/cfg["decision_receipt"]
    digest_raw=read(receipt,4096).decode("utf-8-sig").strip()
    match=re.fullmatch(r"([0-9a-f]{64})  ([A-Za-z0-9._-]+)",digest_raw)
    must(bool(match) and match.group(2)==report.name,
         "INVALID_F105_RECEIPT")
    raw=read(report,150000)
    must(hashlib.sha256(raw).hexdigest()==match.group(1),
         "TAMPERED_F105_RECEIPT")
    current=feedback.json_distinct(raw)
    derived=feedback.evaluate(source_sha,root)
    must(current==derived and
         current.get("forge_source_sha")==source_sha and
         current.get("automatic_frozen_policy_selection") is True and
         current.get("input_observation_count")==4 and
         current.get("development_pairs_observed")==576 and
         current.get("original_experiment_dispatches")==0 and
         current.get("protected_first_use_authorized") is False,
         "INCONSISTENT_F105_DECISION_OR_PARENT_EVIDENCE")
    decisions=current.get("selected_successors")
    expected=cfg["requirements"]["only_qualified_prior_C2_successors"]
    must(type(decisions) is list and len(decisions)==2 and
         set(d.get("lane") for d in decisions)==set(expected) and
         all(d["parent_candidate_id"]==expected[d["lane"]]["candidate"] and
             d["selected_successor_hypothesis"]==expected[d["lane"]]["hypothesis"] and
             d["selection_reason"]=="PUBLIC_DEV_PASSED_PRIORITIZE_NOVEL_TRANSFER_FALSIFICATION" and
             d["proposed_status"]=="UNTESTED_DEVELOPMENT_DESIGN_NOT_DISPATCH_ELIGIBLE"
             for d in decisions),
         "UNSUPPORTED_AUTOMATIC_CHOICE_FAIL_CLOSED")
    return current,hashlib.sha256(raw).hexdigest()

def wingless_new_challenge():
    result=[]
    for seed in range(64200,64224):
        for instance in (0,1):
            rng=random.Random((seed<<7)+instance*19+106)
            query=(seed+2*instance)%4
            order=list(range(4))
            rng.shuffle(order)
            if instance==1:order=order[1:]+order[:1]
            val=[-1.0]*4
            if instance==1:
                other=[i for i in range(4) if i!=query]
                # Two sign-opposed distractors and one agreeing distractor.
                val[other[(seed+instance)%3]]=1.0
            pos=val.copy();neg=val.copy()
            pos[query]=1.0;neg[query]=-1.0
            p=wobserve.Case(seed,instance,instance,query,tuple(order),
                tuple(pos[i] for i in order),tuple(neg[i] for i in order))
            must(sum(a!=b for a,b in zip(p.positive_values,p.negative_values))==1 and
                 wobserve.coded_depth_observation_oracle(p,p.positive_values) and
                 not wobserve.coded_depth_observation_oracle(p,p.negative_values),
                 "WINGLESS_NEW_CHALLENGE_LABEL_ERROR")
            result.append(p)
    must(len(result)==48 and len({(p.seed,p.specimen) for p in result})==48,
         "WINGLESS_NEW_CHALLENGE_SIZE_OR_REPLAY")
    return tuple(result)

def yggdrasil_new_challenge():
    result=[]
    for seed in range(64300,64324):
        for instance in (0,1):
            rng=random.Random((seed<<7)+instance*31+106)
            nodes=list(range(1,8))
            rng.shuffle(nodes)
            a,b,c,d,e,f,extra=nodes
            target=8
            path_a=[0,a,b,c,target]
            path_b=[0,d,e,f,target]
            edges=list(zip(path_a[:-1],path_a[1:]))+list(zip(path_b[:-1],path_b[1:]))
            if instance==0:
                connected=[(a,e),(d,b),(b,f),(e,c)]
            else:
                connected=[(a,f),(f,b),(d,c),(c,e)]
            edges+=connected
            must(len(set(edges))==12,"DUPLICATE_CONNECTED_TOPOLOGY")
            query=tuple(rng.randrange(4) for _ in range(4))
            roles=[*query,*query]+[(query[(i+1)%4]+1+i)%4 for i in range(4)]
            x=(seed+instance)%6
            y=(x+1+(seed%5))%12
            z=(y+2)%12
            u=(z+3)%12
            v=(u+2)%12
            w=(v+3)%12
            positive=[(x,x),(x,y),(y,x),(x,z),
                      (x,u),(u,v),(v,w),((w+1)%12,z)]
            positive +=[(15,(seed+i)%12) for i in range(4)]
            negative=[list(pair) for pair in positive]
            conflict=(seed+instance)%3
            idx=conflict+1
            negative[idx][0]=(positive[idx][0]+1+(seed%7))%12
            must(negative[idx][0]!=positive[idx][0],"NONCOUNTERFACTUAL_BINDING_SHIFT")
            ordering=list(range(12))
            rng.shuffle(ordering)
            p=ybind.Pair(seed,instance,instance,
                tuple(edges[j] for j in ordering),
                tuple(roles[j] for j in ordering),
                tuple(positive[j] for j in ordering),
                tuple(tuple(negative[j]) for j in ordering),
                query,0,target,conflict)
            must(sum(a!=b for pair1,pair2 in zip(
                    p.positive_variables,p.negative_variables)
                    for a,b in zip(pair1,pair2))==1 and
                 ybind.coded_exact_binding_oracle(p,p.positive_variables) and
                 not ybind.coded_exact_binding_oracle(p,p.negative_variables),
                 "YGGDRASIL_NEW_CHALLENGE_INVALID_TRUTH")
            result.append(p)
    must(len(result)==48 and len({(p.seed,p.specimen) for p in result})==48,
         "YGGDRASIL_NEW_CHALLENGE_SIZE_OR_REPLAY")
    return tuple(result)

def evaluate_lane(name,cfg):
    limits=cfg["scores"]["frozen_development_screen_only"]
    if name=="Wingless":
        examples=wingless_new_challenge()
        train=wobserve.public_groups()
        learner=wobserve.LearnedObservationSelector().fit(train[0]+train[1])
        blind=wobserve.LearnedObservationSelector(depth_blind=True).fit(train[0]+train[1])
        learned=wobserve.paired_accuracy(examples,learner.predicts)
        comparator=wobserve.paired_accuracy(examples,blind.predicts)
        coded=wobserve.paired_accuracy(examples,wobserve.coded_depth_observation_oracle)
        shortcut=wobserve.paired_accuracy(examples,lambda p,v: v[0]>0)
        by_family={str(i):wobserve.paired_accuracy(
            [p for p in examples if p.specimen==i],learner.predicts) for i in (0,1)}
        false_positive=sum(learner.predicts(p,p.negative_values) for p in examples)/len(examples)
        selected_correct=sum(learner.selected_depth(p)==p.query_depth for p in examples)/len(examples)
        params=learner.parameters
        mechanism="W100-C2"
        direction="CONFLICTING_OBSERVATION_AND_BUDGET_TRANSFER"
    elif name=="Yggdrasil":
        examples=yggdrasil_new_challenge()
        train=ybind.public_cohorts()
        learner=ybind.LearnedVariableBinder().fit(train[0]+train[1])
        blind=ybind.LearnedVariableBinder(blind=True).fit(train[0]+train[1])
        learned=ybind.paired_accuracy(examples,learner.predicts)
        comparator=ybind.paired_accuracy(examples,blind.predicts)
        coded=ybind.paired_accuracy(examples,ybind.coded_exact_binding_oracle)
        shortcut=ybind.paired_accuracy(examples,lambda p,v:True)
        by_family={str(i):ybind.paired_accuracy(
            [p for p in examples if p.specimen==i],learner.predicts) for i in (0,1)}
        false_positive=sum(learner.predicts(p,p.negative_variables) for p in examples)/len(examples)
        selected_correct=None
        params=learner.parameter_count
        mechanism="Y100-C2"
        direction="ALIASING_AND_VARIABLE_REUSE_TRANSFER"
    else:
        raise Quarantined("UNKNOWN_LANE")
    must(params<=128 and learner.training_updates==100 and
         blind.training_updates==100 and coded==1.0 and len(examples)==48,
         "ORACLE_TRAINING_OR_CHALLENGE_DRIFT")
    worst=min(by_family.values())
    screen=(learned>=limits["minimum_paired_accuracy"] and
            learned-comparator>=limits["minimum_gain_over_blind"] and
            worst>=limits["minimum_worst_family_accuracy"])
    if screen:
        next_direction=("HARDER_UNSEEN_PUBLIC_OBSERVATION_TOPOLOGY" if name=="Wingless"
                        else "ADVERSARIAL_NOVEL_BINDING_GRAPH_TOPOLOGY")
    else:
        next_direction=("FALSIFY_QUERY_SELECTION_ON_CONFLICTING_OBSERVATIONS" if name=="Wingless"
                        else "FALSIFY_LEARNED_VARIABLE_BINDER_ON_ALIASING_CROSS_EDGES")
    return dict(lane=name,parent_candidate_id=mechanism,
                selected_parent_direction=direction,
                new_challenge_source="F106_PUBLIC_SEEDED_GENERATOR_INDEPENDENT_OF_F101_TO_F104_COHORT",
                new_assessment_pairs=48,prior_parent_training_only_pairs=96,
                trainable_parameter_count=params,parent_training_steps=100,
                comparator_training_steps=100,
                learned_paired_accuracy=learned,
                blind_paired_accuracy=comparator,
                coded_oracle_control_accuracy=coded,
                shortcut_paired_accuracy=shortcut,
                worst_novel_family_accuracy=worst,
                family_accuracy=by_family,
                negative_false_positive_rate=false_positive,
                correct_query_slot_fraction=selected_correct,
                new_challenge_screen_passed=screen,
                outcome=("PUBLIC_TRANSFER_SCREEN_POSITIVE_NOT_SCIENCE" if screen
                         else "PUBLIC_TRANSFER_SCREEN_NEGATIVE_PRESERVED"),
                next_feedback_direction=next_direction,
                successor_authority="UNTESTED_PROPOSAL_ONLY_NO_DISPATCH_OR_PROMOTION")

def evaluate(source_sha,evidence_root):
    must(type(source_sha) is str and SHA.fullmatch(source_sha) is not None and
         (not os.environ.get("GITHUB_SHA") or os.environ["GITHUB_SHA"]==source_sha),
         "GITHUB_SHA_DRIFT")
    cfg,freeze_hash=frozen()
    prior,decision_sha=f105_current_run(source_sha,Path(evidence_root).resolve(),cfg)
    lanes=[evaluate_lane("Wingless",cfg),evaluate_lane("Yggdrasil",cfg)]
    return dict(schema=REPORT,source_sha=source_sha,
        evidence_class="NEW_BOUNDED_PUBLIC_DEVELOPMENT_CHALLENGE_NOT_SCIENTIFIC_FIRST_USE",
        freeze_sha256=freeze_hash,validated_prior_f105_sha256=decision_sha,
        source_policy_sha256=prior["frozen_policy_sha256"],
        new_public_challenge_pairs=96,
        distinct_parent_model_lanes=2,
        run_scoped_selection_verified=True,
        real_cpu_model_training=True,
        lanes=lanes,feedback_next_directions=[dict(lane=x["lane"],
            advice=x["next_feedback_direction"],based_on_negative=not x["new_challenge_screen_passed"],
            dispatch_allowed=False) for x in lanes],
        new_protected_originals=0,original_science_accepted=0,
        protected_first_use_authorized=False,
        independent_scientific_generalization_claimed=False,
        trained_policy_promoted=False,accepted_ref_mutations=0,
        codex_invocations=0,external_paid_model_calls=0,
        work_tasks=0,ckb_plane_accessed=False,
        new_schedulers=0,native_research_workers_dispatched=0)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source-ref",required=True)
    p.add_argument("--evidence-root",required=True)
    a=p.parse_args()
    print(json.dumps(evaluate(a.source_ref,a.evidence_root),
                     sort_keys=True,separators=(",",":")))

if __name__=="__main__":
    try:main()
    except (Quarantined,feedback.Quarantined,ybind.Rejected,wobserve.Rejected,
            KeyError,ValueError,TypeError,OSError) as error:
        print("FORGE_F106_AUTOMATIC_PUBLIC_CHALLENGE=QUARANTINED "+str(error),file=sys.stderr)
        raise SystemExit(1)
