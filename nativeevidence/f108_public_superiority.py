"""F108: preregistered PUBLIC transfer superiority challenge; retain failures.

No source generation/model search on these diagnostic cases. Uses exact F107 AST
selected on prior training, exact F103/F104 fitted weights, same examples and
explicit cost-parity rule. Scientific acceptance and inference authority ZERO.
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
import f107_structural_mechanisms as structural

ROOT=Path(__file__).resolve().parents[1]
FREEZE=ROOT/"reference/research-intake/f108-superiority-transfer-freeze.json"
FREEZE_BLOB="d6e3568b025681193d632c8fd7e92ef2a8457e9f"
PARENT_F107="51e6dcd98692c68b3cd318f8956082209022e20b"
PARENT_F107_BLOB="4785e6171e87455377d7a5ce4e7d2d5699044219"
SCHEMA="forge.autonomy.f108.frozen-blind-parent-superiority-test.v1"
REPORT="forge.autonomy.f108.preregistered-public-transfer-parent-superiority.v1"
SHA40=re.compile(r"^[0-9a-f]{40}$")

class Quarantined(ValueError):pass
def need(value,reason):
    if not value:raise Quarantined("F108_"+reason)
def gitblob(raw):
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
def canonical(path):
    return Path(path).read_bytes().replace(b"\r\n",b"\n")
def get_config():
    raw=canonical(FREEZE)
    need(gitblob(raw)==FREEZE_BLOB,"PREREGISTRATION_DRIFT")
    need(gitblob(canonical(ROOT/"nativeevidence/f107_structural_mechanisms.py"))==
         PARENT_F107_BLOB,"PARENT_IMPLEMENTATION_DRIFT")
    cfg=structural.load_json(raw)
    need(cfg.get("schema")==SCHEMA and
         cfg.get("parent_f107_exact_head_sha")==PARENT_F107 and
         cfg.get("parent_f107_frozen_git_blob")==
             "b46c57b0e9e040069eab9726618df27416b4068b" and
         cfg.get("parent_f107_implementation_git_blob")==PARENT_F107_BLOB,
         "PARENT_LINEAGE_DRIFT")
    expected={
        "Wingless":{"parent":"W100-C2",
            "ast":["query_attention","top_two_contrast","hard_margin"]},
        "Yggdrasil":{"parent":"Y100-C2",
            "ast":["slot_keyed","max","learned_sigmoid"]}}
    need(cfg.get("required_f107_selected")==expected,"CHERRY_PICKED_MECHANISM")
    cohorts=cfg.get("prospectively_different_public_development_challenges",{})
    w=cohorts.get("Wingless",{})
    y=cohorts.get("Yggdrasil",{})
    need(w.get("seed_block")==[65300,65347] and
         w.get("assessment_pairs")==48 and w.get("pairs_per_seed")==1 and
         w.get("signed_query_strengths")==[0.05,0.10,0.20] and
         w.get("signed_distractor_strengths")==[0.5,1.0,2.0] and
         w.get("pair_difference")==
         "exactly_one_queried_value_flips_sign_while_every_other_observation_is_unchanged" and
         y.get("seed_block")==[65400,65447] and
         y.get("assessment_pairs")==48 and y.get("pairs_per_seed")==1 and
         y.get("edge_budget")==12 and y.get("hops")==4 and
         y.get("pair_difference")==
         "exactly_one_queried_main_path_variable_argument_breaks_unification",
         "PREDECLARED_NEW_CHALLENGE_DRIFT")
    test=cfg.get("predeclared_metrics",{})
    gate=test.get("improvement_gate",{})
    need(gate=={
         "minimum_absolute_paired_gain":0.125,
         "minimum_net_pair_advantage":6,
         "minimum_worst_family_candidate_accuracy":0.6,
         "candidate_no_higher_cost_than_parent":True,
         "candidate_must_beat_parent_on_same_examples":True,
         "result_label_only_if_all_requirements_pass":
             "PUBLIC_DEV_RESOURCE_MATCHED_ADVANTAGE_NO_SCIENCE"} and
         test.get("no_superiority_outcome")=="NO_DEMONSTRATED_GAIN_RETAIN_NEGATIVE" and
         test.get("no_test_adaptive_retraining_or_cherry_picking") is True and
         test.get("negative_is_valid_outcome_not_ci_failure") is True and
         test.get("unfrozen_test_not_to_be_used_for_selection") is True,
         "SUPERIORITY_DEFINITION_DRIFT")
    trained=cfg.get("existing_parent_training",{})
    need(trained.get("exact_100_existing_parent_updates") is True and
         trained.get("no_new_training_or_parameter_tuning") is True and
         trained.get("no_adapt_after_new_conditions") is True,
         "POST_ASSESSMENT_TUNING")
    guards=cfg.get("guardrails",{})
    need(all(guards.get(key) is True for key in (
        "no_protected_scientific_first_use","no_independent_science_acceptance",
        "no_optimizer_promotion","no_accepted_ref_mutation","no_codex",
        "no_paid_model_api","no_chatgpt_work_tasks","no_ckb_plane_contact",
        "no_cloudflare_write","no_mind_palace_write","no_new_scheduler",
        "no_other_repositories_mutated","no_automatic_native_science_dispatch",
        "no_unrestricted_GPT_mechanism_claim")),
        "UNAUTHORIZED_SCIENCE")
    return cfg,hashlib.sha256(raw).hexdigest()

def get_current_F107(source_sha,evidence_root,cfg):
    root=Path(evidence_root).resolve()
    report=root/cfg["current_run_F107_report"]
    receipt=root/cfg["current_run_F107_receipt"]
    raw=report.read_bytes()
    rec=receipt.read_bytes().decode("utf-8-sig").strip()
    m=re.fullmatch(r"([a-f0-9]{64})  ([A-Za-z0-9._-]+)",rec)
    need(bool(m) and m.group(2)==report.name and
         hashlib.sha256(raw).hexdigest()==m.group(1),
         "F107_REPORT_CONTENT_OR_HASH_DRIFT")
    data=structural.load_json(raw)
    need(data.get("schema")==structural.REPORT and
         data.get("source_sha")==source_sha and
         data.get("F106_feedback_consumed") is True and
         data.get("diagnostic_not_used_to_choose") is True and
         data.get("choices_from_train_only") is True and
         data.get("candidate_count")==33 and
         data.get("scientific_originals_executed")==0 and
         data.get("independent_science_accepted")==0 and
         data.get("protected_first_use_authorized") is False and
         data.get("accepted_ref_mutations")==0 and
         data.get("codex_invocations")==0 and
         data.get("paid_api_calls")==0,
         "F107_REPORT_UNQUALIFIED_OR_REPLAYED")
    lanes=data.get("lanes")
    need(type(lanes) is list and len(lanes)==2,"INCOMPLETE_PARENT_PROGRAMS")
    expected=cfg["required_f107_selected"]
    for lane,expect in expected.items():
        rows=[r for r in lanes if r.get("lane")==lane]
        need(len(rows)==1,"AMBIGUOUS_PARENT_LANE")
        actual=rows[0]
        ast=expect["ast"]
        need(actual.get("source_parent_C2")==expect["parent"] and
             actual.get("selected_program_ast")==ast and
             actual.get("selected_program_fingerprint")==
                 structural.fingerprint(lane,ast) and
             actual.get("new_diagnostic_pairs")==48 and
             actual.get("coded_oracle_separate_control_accuracy")==1.0 and
             actual.get("no_protected_first_use") is True and
             actual.get("no_automatic_dispatch") is True,
             "F107_SELECTED_PROGRAM_SUBSTITUTED")
    return data,hashlib.sha256(raw).hexdigest()

def wingless_cases():
    cases=[]
    for seed in range(65300,65348):
        rng=random.Random((seed<<5)+108)
        family=(seed-65300)%3
        query=(seed+family)%4
        order=list(range(4));rng.shuffle(order)
        query_strength=(0.05,0.10,0.20)[(seed-65300)%3]
        strengths=(0.5,1.0,2.0)
        signals=[0.]*4
        others=[tag for tag in range(4) if tag!=query]
        for j,tag in enumerate(others):
            strength=strengths[(j+seed)%3]
            # Frozen family sign patterns, chosen without model outcomes.
            if family==0:
                value=-strength
            elif family==1:
                value=strength if j%2==0 else -strength
            else:
                value=strength if j==0 else -strength
            signals[tag]=value
        positive=signals.copy()
        negative=signals.copy()
        positive[query]=query_strength
        negative[query]=-query_strength
        p=wobserve.Case(seed,family,0,query,tuple(order),
             tuple(positive[t] for t in order),
             tuple(negative[t] for t in order))
        need(sum(a!=b for a,b in zip(p.positive_values,p.negative_values))==1 and
             structural.wobserve.coded_depth_observation_oracle(
                 p,p.positive_values) and
             not structural.wobserve.coded_depth_observation_oracle(
                 p,p.negative_values),"WINGLESS_GROUND_TRUTH_INVALID")
        cases.append(p)
    need(len(cases)==48 and len({p.seed for p in cases})==48,
         "WINGLESS_ASSESSMENT_SIZE_OR_REPLAY")
    return tuple(cases)

def ygg_cases():
    cases=[]
    for seed in range(65400,65448):
        family=(seed-65400)%3
        p=structural.ygg_case(seed,2,family)
        # Change ONLY non-answer cross-branch typed-role distractor edges
        # (positions 8-11 in generator before permutation) by matching
        # graph edge endpoint identities of known cross edges after shuffle.
        # The altered role on an edge with variable lhs 15 can never unify
        # from the main path whose variable labels are drawn from 0..14.
        rng=random.Random(seed*97+108)
        extra=tuple(sorted((u,v) for u,v in p.edges if
                    (u,v) not in []))
        newroles=list(p.roles)
        if family in (1,2):
            # All cross-branch edges are identified by original last-four
            # variable assignments with no need to reveal correct binding.
            # Cross-edge roles collide with the query's second/third role.
            for i,(lhs,rhs) in enumerate(p.positive_variables):
                if i<0:raise AssertionError("unreachable")
                if (p.edges[i][0] != 0 and lhs==rhs and lhs==15):
                    newroles[i]=p.query_roles[(i+family)%4]
        # Deterministically remap only nodes; no oracle fed to candidate.
        p=replace(p,block=family,roles=tuple(newroles))
        need(sum(a!=b for one,two in zip(p.positive_variables,p.negative_variables)
                 for a,b in zip(one,two))==1 and
             ybind.coded_exact_binding_oracle(p,p.positive_variables) and
             not ybind.coded_exact_binding_oracle(p,p.negative_variables),
             "YGGDRASIL_NEW_BINDING_GROUND_TRUTH_INVALID")
        cases.append(p)
    need(len(cases)==48 and len({p.seed for p in cases})==48,
         "YGGDRASIL_ASSESSMENT_SIZE_OR_REPLAY")
    return tuple(cases)

def eval_lane(lane,ast,cfg):
    if lane=="Wingless":
        cases=wingless_cases()
        historical=wobserve.public_groups()
        learned=wobserve.LearnedObservationSelector().fit(historical[0]+historical[1])
        blind=wobserve.LearnedObservationSelector(depth_blind=True).fit(historical[0]+historical[1])
        parentast=("query_attention","single_argmax","learned_sigmoid")
        parent=lambda p,v:structural.wing_pred(learned,parentast,p,v)
        candidate=lambda p,v:structural.wing_pred(learned,tuple(ast),p,v)
        blindpred=lambda p,v:structural.wing_pred(blind,parentast,p,v)
        oracle=lambda p,v:wobserve.coded_depth_observation_oracle(p,v)
        getter=lambda p:(p.positive_values,p.negative_values)
        oldcost=1
        newcost=2
    else:
        need(lane=="Yggdrasil","UNSUPPORTED_LANE")
        cases=ygg_cases()
        historical=ybind.public_cohorts()
        learned=ybind.LearnedVariableBinder().fit(historical[0]+historical[1])
        blind=ybind.LearnedVariableBinder(blind=True).fit(historical[0]+historical[1])
        parentast=("slot_keyed","sum","learned_sigmoid")
        parent=lambda p,v:structural.ygg_pred(learned,parentast,p,v)
        candidate=lambda p,v:structural.ygg_pred(learned,tuple(ast),p,v)
        blindpred=lambda p,v:structural.ygg_pred(blind,parentast,p,v)
        oracle=lambda p,v:ybind.coded_exact_binding_oracle(p,v)
        getter=lambda p:(p.positive_variables,p.negative_variables)
        oldcost=18
        newcost=18
    need(learned.training_updates==blind.training_updates==100,
         "PARENT_TRAINING_BUDGET_DRIFT")
    details=[]
    families={}
    for p in cases:
        pos,neg=getter(p)
        oracle_ok=oracle(p,pos) and not oracle(p,neg)
        need(oracle_ok,"INVALID_CONTROL_TRUTH")
        a=candidate(p,pos) and not candidate(p,neg)
        b=parent(p,pos) and not parent(p,neg)
        c=blindpred(p,pos) and not blindpred(p,neg)
        details.append(dict(seed=p.seed,family=p.block,
             candidate_both_correct=bool(a),parent_both_correct=bool(b),
             blind_both_correct=bool(c),
             candidate_negative_false_positive=bool(candidate(p,neg)),
             parent_negative_false_positive=bool(parent(p,neg))))
        families.setdefault(str(p.block),[]).append(bool(a))
    correct_c=sum(x["candidate_both_correct"] for x in details)
    correct_p=sum(x["parent_both_correct"] for x in details)
    correct_b=sum(x["blind_both_correct"] for x in details)
    cand_only=sum(x["candidate_both_correct"] and not x["parent_both_correct"]
                  for x in details)
    parent_only=sum(x["parent_both_correct"] and not x["candidate_both_correct"]
                    for x in details)
    net=cand_only-parent_only
    gate=cfg["predeclared_metrics"]["improvement_gate"]
    family_scores={k:sum(v)/len(v) for k,v in families.items()}
    minfamily=min(family_scores.values())
    parity=newcost<=oldcost
    improved=(correct_c-correct_p>=gate["minimum_absolute_paired_gain"]*48 and
              net>=gate["minimum_net_pair_advantage"] and
              minfamily>=gate["minimum_worst_family_candidate_accuracy"] and
              parity and correct_c>correct_p)
    label=(gate["result_label_only_if_all_requirements_pass"] if improved else
           cfg["predeclared_metrics"]["no_superiority_outcome"])
    return dict(lane=lane,selected_program_ast=ast,
        selected_program_fingerprint=structural.fingerprint(lane,ast),
        candidate_score=correct_c/48,
        unchanged_parent_score=correct_p/48,
        independently_trained_blind_score=correct_b/48,
        coded_control_score=1.0,
        candidate_correct_pairs=correct_c,parent_correct_pairs=correct_p,
        candidate_only_correct=cand_only,parent_only_correct=parent_only,
        net_paired_advantage=net,
        candidate_cost=newcost,parent_cost=oldcost,
        cost_parity_satisfied=parity,
        worst_family_candidate_score=minfamily,
        family_candidate_scores=family_scores,
        candidate_negative_false_positive_rate=
            sum(x["candidate_negative_false_positive"] for x in details)/48,
        parent_negative_false_positive_rate=
            sum(x["parent_negative_false_positive"] for x in details)/48,
        all_paired_record_details=details,
        diagnostic_pair_count=48,parent_training_updates=100,
        frozen_resource_matched_superiority_gate_passed=improved,
        outcome=label,independent_science_claim=False)

def evaluate(source_sha,evidence_root):
    need(type(source_sha) is str and SHA40.fullmatch(source_sha) and
         (not os.environ.get("GITHUB_SHA") or os.environ["GITHUB_SHA"]==source_sha),
         "RUN_SOURCE_REF_DRIFT")
    cfg,cfg_hash=get_config()
    prior,parent_hash=get_current_F107(source_sha,evidence_root,cfg)
    outcomes=[eval_lane("Wingless",cfg["required_f107_selected"]["Wingless"]["ast"],cfg),
              eval_lane("Yggdrasil",cfg["required_f107_selected"]["Yggdrasil"]["ast"],cfg)]
    success=[x["lane"] for x in outcomes if
             x["frozen_resource_matched_superiority_gate_passed"]]
    return dict(schema=REPORT,source_sha=source_sha,
        evidence_class="PROSPECTIVE_FROZEN_PUBLIC_DEVELOPMENT_NO_PROTECTED_FIRST_USE",
        current_run_F107_report_sha256=parent_hash,
        preregistered_protocol_sha256=cfg_hash,
        total_new_public_assessment_pairs=96,
        diagnostic_results=outcomes,
        resource_matched_improvement_lanes=success,
        definitive_mechanism_improvement_claim=False,
        feedback=("PUBLIC_SUPERIORITY_SCREEN_TO_INDEPENDENT_PROSPECTIVE_REVIEW"
                   if success else "NO_PROVEN_RESOURCE_MATCHED_IMPROVEMENT_RETAIN_NEGATIVES"),
        all_predeclared_outcomes_retained=True,
        no_post_test_tuning=True,
        scientific_originals_dispatched=0,
        independently_accepted_science=0,
        first_use_authorized=False,
        optimizer_promotions=0,accepted_ref_mutations=0,
        codex_calls=0,paid_model_api_calls=0,
        work_tasks=0,ckb_plane_contact=False,
        cloudflare_writes=0,new_schedulers=0)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--source-ref",required=True)
    ap.add_argument("--evidence-root",required=True)
    args=ap.parse_args()
    print(json.dumps(evaluate(args.source_ref,args.evidence_root),
                     sort_keys=True,separators=(",",":")))

if __name__=="__main__":
    try:main()
    except (Quarantined,structural.Quarantined,
            ybind.Rejected,wobserve.Rejected,OSError,
            TypeError,ValueError,KeyError) as error:
        print("FORGE_F108_FROZEN_TRANSFER=QUARANTINED "+str(error),file=sys.stderr)
        raise SystemExit(1)
