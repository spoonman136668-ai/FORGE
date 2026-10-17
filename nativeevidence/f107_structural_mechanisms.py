"""F107 model-free structural research mechanism generator, public development only.

Compose typed executable operator programs from a frozen grammar, select using a
separate public TRAIN-only cohort, and evaluate one finalist on never-selected
frozen public diagnostic cohort. Every losing candidate and negative is retained.
No arbitrary code generation, eval, protected science, paid model or dispatch.
"""
import argparse
import hashlib
import itertools
import json
import math
import os
from pathlib import Path
import random
import re
import sys

import f103_yggdrasil_public_binding as ybind
import f104_wingless_public_observations as wobserve
import f106_automatic_challenge as f106

ROOT=Path(__file__).resolve().parents[1]
FREEZE=ROOT/"reference/research-intake/f107-structural-mechanism-search-freeze.json"
FREEZE_BLOB="b46c57b0e9e040069eab9726618df27416b4068b"
PARENT_F106_BLOB="38616e87ab57851999c8d2e2d5abd1843fec6c5d"
PARENT="4b8b0558b83541d9e8ddff68b97f497f196aa77c"
SCHEMA="forge.autonomy.f107.frozen-structural-mechanism-search.v1"
REPORT="forge.autonomy.f107.model-free-structural-mechanism-search-public-dev.v1"
SHA40=re.compile(r"^[a-f0-9]{40}$")
HEX64=re.compile(r"^[a-f0-9]{64}$")

class Quarantined(ValueError):pass
def need(value,message):
    if not value:raise Quarantined("F107_"+message)
def gitblob(raw):
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
def raw(path,limit=150000):
    b=Path(path).read_bytes()
    need(0<len(b)<=limit,"EMPTY_OR_OVERSIZED_FILE")
    return b
def canonical(path):
    return raw(path,300000).replace(b"\r\n",b"\n")
def sha256(raw_bytes):
    return hashlib.sha256(raw_bytes).hexdigest()
def load_json(b):
    def unique(pairs):
        obj={}
        for key,val in pairs:
            need(key not in obj,"DUPLICATE_JSON_KEY")
            obj[key]=val
        return obj
    return json.loads(b.decode("utf-8-sig"),object_pairs_hook=unique)
def frozen():
    b=canonical(FREEZE)
    need(gitblob(b)==FREEZE_BLOB,"FREEZE_CONTENT_DRIFT")
    need(gitblob(canonical(ROOT/"nativeevidence/f106_automatic_challenge.py"))==
         PARENT_F106_BLOB,"F106_IMPLEMENTATION_CHANGED")
    f=load_json(b)
    need(f.get("schema")==SCHEMA and f.get("parent_f106_exact_head_sha")==PARENT and
         f.get("parent_f106_protocol_blob_sha")==
            "dadea0c72f51d683d94b9c7e12fbafd044dd49c9" and
         f.get("purpose")==
            "CURRENT_RUN_REAL_F106_FEEDBACK_TO_BOUNDED_NOVEL_MECHANISM_PROGRAM_GENERATION_AND_TRAIN_ONLY_SCREEN",
         "FROZEN_OR_PARENT_POLICY_DRIFT")
    g=f.get("mechanism_grammar",{})
    need(g.get("search_family")==
         "BOUNDED_MODEL_FREE_TYPED_OPERATOR_PROGRAM_GRAMMAR_NOT_GENERATIVE_GPT" and
         g.get("symbolic_op_modules_not_source_code_execution") is True and
         g.get("unique_program_limit_per_lane")==18 and
         g.get("require_fingerprint_different_from_parent") is True and
         g.get("require_at_least_3_structural_families_per_lane") is True and
         g.get("candidate_mutations_are_structural_operator_substitutions") is True and
         g.get("require_candidate_fitness_computed_from_train_only_public_pairs") is True and
         g.get("allow_dynamic_imports_eval_exec_or_remote_source") is False and
         g["Wingless"]["operator_axes"]=={
             "selector":["query_attention","shifted_attention","query_blind_attention"],
             "aggregation":["single_argmax","top_two_contrast","weighted_four"],
             "readout":["learned_sigmoid","hard_margin","signed_soft_margin"]} and
         g["Yggdrasil"]["operator_axes"]=={
             "state":["slot_keyed","node_pooled"],
             "merge":["sum","max","mean"],
             "readout":["learned_sigmoid","target_relative_mass","signed_margin"]},
         "MECHANISM_GRAMMAR_CHANGED")
    cohorts=f.get("public_new_generator",{})
    for lane,train,test in (("Wingless",[64800,64815],[64832,64847]),
                             ("Yggdrasil",[64900,64915],[64932,64947])):
        row=cohorts.get(lane,{})
        need(row.get("train_seeds")==train and row.get("diagnostic_seeds")==test and
             row.get("cases_per_seed")==3 and row.get("train_pairs")==48 and
             row.get("diagnostic_pairs")==48 and
             row.get("no_reuse_F104_F106_seeds",row.get("no_reuse_F103_F106_seeds")) is True,
             "SEED_ALLOCATION_DRIFT_"+lane)
    need(cohorts.get("freeze_diagnostic_before_new_code") is True and
         cohorts.get("no_candidate_selection_on_diagnostic") is True and
         cohorts.get("oracle_separate_ground_truth_only") is True,
         "TEST_SET_LEAKAGE")
    sel=f.get("selection_policy",{})
    need(sel.get("parent_models_fit_on_original_F103_F104_training_only") is True and
         sel.get("parent_training_updates_exactly")==100 and
         sel.get("all_candidates_scored_on_new_train_cohort_before_one_finalist_chosen") is True and
         sel.get("diagnostic_evaluated_once_on_chosen_finalist_and_parent_and_blind") is True and
         sel.get("no_hindsight_selection_or_parameter_tuning") is True and
         sel.get("pareto_metrics")==[
             "paired_train_accuracy_max","observation_or_edge_cost_min","structural_family_diversity"] and
         sel.get("fail_screen_keeps_negative_outcomes") is True and
         sel.get("no_screen_success_required_for_CI") is True,
         "CHERRY_PICKED_SELECTION_RULE")
    flags=f.get("authority",{})
    need(all(flags.get(k) is True for k in (
         "report_advice_only","no_accepted_refs","no_protected_first_use",
         "no_auto_native_scientific_dispatch","no_independent_science_acceptance",
         "no_promoted_optimizer","no_codex","no_paid_model_api",
         "no_chatgpt_work_task","no_ckb_plane_contact",
         "no_cloudflare_write","no_mind_palace_write",
         "no_wingless_yggdrasil_repo_mutation","no_new_scheduler",
         "no_free_form_GPT_hypothesis_generation_claim")),
         "AUTHORITY_ESCALATION")
    return f,sha256(b)

def receipt_current(report_path,receipt_path,source):
    report=Path(report_path)
    rec=raw(receipt_path,4096).decode("utf-8-sig").strip()
    match=re.fullmatch(r"([a-f0-9]{64})  ([A-Za-z0-9_.-]+)",rec)
    need(bool(match) and match.group(2)==report.name,"INVALID_F106_RECEIPT")
    data=raw(report,150000)
    need(sha256(data)==match.group(1),"TAMPERED_F106_EVIDENCE")
    obj=load_json(data)
    need(obj.get("schema")==f106.REPORT and obj.get("source_sha")==source and
         obj.get("run_scoped_selection_verified") is True and
         obj.get("new_public_challenge_pairs")==96 and
         obj.get("distinct_parent_model_lanes")==2 and
         obj.get("real_cpu_model_training") is True and
         obj.get("protected_first_use_authorized") is False and
         obj.get("accepted_ref_mutations")==0 and
         obj.get("new_protected_originals")==0 and
         obj.get("native_research_workers_dispatched")==0 and
         obj.get("external_paid_model_calls")==0 and
         obj.get("codex_invocations")==0 and
         obj.get("trained_policy_promoted") is False,
         "UNQUALIFIED_F106_EVIDENCE")
    outcomes=obj.get("lanes")
    adv=obj.get("feedback_next_directions")
    need(type(outcomes) is list and len(outcomes)==2 and
         type(adv) is list and len(adv)==2,"MISSING_F106_FEEDBACK")
    for lane,expect in (("Wingless","HARDER_UNSEEN_PUBLIC_OBSERVATION_TOPOLOGY"),
                        ("Yggdrasil","ADVERSARIAL_NOVEL_BINDING_GRAPH_TOPOLOGY")):
        subset=[z for z in outcomes if z.get("lane")==lane]
        matching=[z for z in adv if z.get("lane")==lane]
        need(len(subset)==len(matching)==1 and
             matching[0].get("advice")==expect and
             matching[0].get("dispatch_allowed") is False and
             matching[0].get("based_on_negative") is False and
             subset[0].get("new_challenge_screen_passed") is True and
             subset[0].get("new_assessment_pairs")==48 and
             subset[0].get("coded_oracle_control_accuracy")==1.0,
             "UNSUPPORTED_NEXT_MECHANISM_DIRECTIVE_"+lane)
    return obj,sha256(data)

def wingless_case(seed,block,specimen):
    rng=random.Random((seed<<8)+block*307+specimen*29+107)
    query=(seed+specimen+block)%4
    order=list(range(4));rng.shuffle(order)
    # Deliberately contradictory signs, varying query position and feedback.
    signals=[(-1.0 if (rng.getrandbits(1) or specimen==0) else 1.0) for _ in range(4)]
    pos=signals.copy();neg=signals.copy()
    pos[query]=1.;neg[query]=-1.
    case=wobserve.Case(seed,block,specimen,query,tuple(order),
          tuple(pos[t] for t in order),tuple(neg[t] for t in order))
    need(sum(a!=b for a,b in zip(case.positive_values,case.negative_values))==1 and
         wobserve.coded_depth_observation_oracle(case,case.positive_values) and
         not wobserve.coded_depth_observation_oracle(case,case.negative_values),
         "INVALID_NEW_WINGLESS_TRUTH")
    return case

def ygg_case(seed,block,specimen):
    rng=random.Random((seed<<8)+block*307+specimen*31+107)
    nodes=list(range(1,10));rng.shuffle(nodes)
    a,b,c,d,e,f,g,h,i=nodes
    target=10
    path_a=(0,a,b,c,target)
    path_b=(0,d,e,f,target)
    edges=list(zip(path_a[:-1],path_a[1:]))+list(zip(path_b[:-1],path_b[1:]))
    # Connected cross-branch distractors and a spurious path fragment.
    edges.extend(((a,e),(d,b),(b,f),(e,c)))
    query=tuple(rng.randrange(4) for _ in range(4))
    roles=list(query)+list(query)+[
        (query[1]+1)%4,(query[1]+1)%4,
        (query[2]+1)%4,(query[2]+1)%4]
    x,y,z=[rng.randrange(15) for _ in range(3)]
    h1,h2=[rng.randrange(15) for _ in range(2)]
    # Reused, nonadjacent variable slots on main path.
    main=[(x,x),(x,y),(y,x),(x,z)]
    alt=[(h1,h1),(h1,h2),(h2,h1),((h1+1)%16,z)]
    vars_=main+alt+[(rng.randrange(16),rng.randrange(16)) for _ in range(4)]
    neg=[list(pair) for pair in vars_]
    conflict=(seed+specimen)%3
    step=conflict+1
    neg[step][0]=(vars_[step][0]+1+rng.randrange(15))%16
    order=list(range(12));rng.shuffle(order)
    case=ybind.Pair(seed,block,specimen,
                    tuple(edges[k] for k in order),
                    tuple(roles[k] for k in order),
                    tuple(vars_[k] for k in order),
                    tuple(tuple(neg[k]) for k in order),
                    tuple(query),0,target,conflict)
    need(len(case.edges)==len(set(case.edges))==12 and
         sum(a!=b for v1,v2 in zip(case.positive_variables,case.negative_variables)
             for a,b in zip(v1,v2))==1 and
         ybind.coded_exact_binding_oracle(case,case.positive_variables) and
         not ybind.coded_exact_binding_oracle(case,case.negative_variables),
         "INVALID_NEW_YGGDRASIL_TRUTH")
    return case

def groups(lane):
    if lane=="Wingless":
        generator=wingless_case
        seeds=((64800,64815),(64832,64847))
    else:
        need(lane=="Yggdrasil","UNSUPPORTED_LANE")
        generator=ygg_case
        seeds=((64900,64915),(64932,64947))
    result=[]
    for block,(lo,hi) in enumerate(seeds):
        rows=[generator(seed,block,instance)
              for seed in range(lo,hi+1) for instance in range(3)]
        need(len(rows)==48 and len({(x.seed,x.specimen) for x in rows})==48,
             "NEW_GENERATOR_COHORT_WRONG")
        result.append(tuple(rows))
    need(not {(p.seed,p.specimen) for p in result[0]} &
             {(p.seed,p.specimen) for p in result[1]},
         "TRAIN_DIAGNOSTIC_REUSE")
    return tuple(result)

def fingerprint(lane,ast):
    serial=json.dumps({"lane":lane,"typed_operator_ast":list(ast)},
                       sort_keys=True,separators=(",",":"))
    return sha256(serial.encode())

def generated_programs(lane,cfg):
    grammar=cfg["mechanism_grammar"][lane]
    axes=grammar["operator_axes"]
    keys=tuple(axes)
    parent=tuple(grammar["parent_program"])
    all_ops=list(itertools.product(*(axes[k] for k in keys)))
    programs=[]
    for ast in all_ops:
        if ast==parent:continue
        # No "novelty" for changing only the output threshold formula.
        if ast[:-1]==parent[:-1]:continue
        cost=(1 if ast[1]=="single_argmax" else
              (2 if ast[1]=="top_two_contrast" else 4)) if lane=="Wingless" else 12
        if lane=="Yggdrasil":
            cost=12+(6 if ast[0]=="slot_keyed" else 0)
        programs.append(dict(lane=lane,ast=ast,sha256=fingerprint(lane,ast),
                             family=ast[0]+"/"+ast[1],cost=cost))
    rng=random.Random(107 if lane=="Wingless" else 108)
    rng.shuffle(programs)
    limit=cfg["mechanism_grammar"]["unique_program_limit_per_lane"]
    # Force coverage without inspecting fitness or diagnostics.
    chosen=[];families=set()
    for p in programs:
        if p["family"] not in families and len(families)<6:
            chosen.append(p);families.add(p["family"])
    for p in programs:
        if len(chosen)>=limit:break
        if p not in chosen:chosen.append(p)
    need(len(chosen)==limit and len({p["sha256"] for p in chosen})==limit and
         len({p["family"] for p in chosen})>=3 and
         all(p["ast"]!=parent for p in chosen),
         "INSUFFICIENT_NOVEL_PROGRAM_GENERATION")
    return tuple(chosen)

def wing_pred(model,ast,p,values):
    selector,aggregate,readout=ast
    need(len(values)==4,"INVALID_OBSERVATION_BUDGET")
    if selector=="query_attention":
        weights=model.attention_weights(p)
    else:
        row=(p.query_depth+1)%4 if selector=="shifted_attention" else 0
        weights=wobserve.softmax([
            model.attention[4*row+tag] for tag in p.observation_depths])
    ranked=sorted(range(4),key=lambda k:(-weights[k],k))
    if aggregate=="single_argmax":
        signal=values[ranked[0]]
    elif aggregate=="top_two_contrast":
        a,b=ranked[:2]
        signal=values[a]-(weights[b]/max(weights[a],1e-9))*values[b]
    elif aggregate=="weighted_four":
        signal=sum(a*b for a,b in zip(weights,values))
    else:raise Quarantined("ILLEGAL_WING_AGGREGATOR")
    if readout=="learned_sigmoid":
        return wobserve.sigmoid(model.scale*signal+model.bias)>=0.5
    if readout=="hard_margin":
        return signal>0
    if readout=="signed_soft_margin":
        return math.tanh(1.5*signal+model.bias/10.)>0
    raise Quarantined("ILLEGAL_WING_READOUT")

def ygg_pred(model,ast,p,variables):
    state_mode,merge,readout=ast
    # These are actual distinct executable message graph structures.
    state={(p.source,-1):1.}
    for hop,query in enumerate(p.query_roles):
        nxt={}
        counts={}
        for (u,v),role,(lhs,rhs) in zip(p.edges,p.roles,variables):
            role_gate=ybind.sigmoid(model.role[4*query+role])
            for (node,prev),mass in state.items():
                if node!=u:continue
                slot_gate=1. if hop==0 else ybind.sigmoid(
                    model.slot[1 if prev==lhs else 0])
                delta=mass*role_gate*slot_gate
                key=(v,rhs) if state_mode=="slot_keyed" else (v,-1)
                if merge=="max":nxt[key]=max(nxt.get(key,0.),delta)
                else:nxt[key]=nxt.get(key,0.)+delta
                counts[key]=counts.get(key,0)+1
        if merge=="mean":
            nxt={key:mass/counts[key] for key,mass in nxt.items()}
        state=nxt
    mass=sum(v for (node,_),v in state.items() if node==p.target)
    if readout=="learned_sigmoid":
        return ybind.sigmoid(model.scale*mass+model.bias)>=0.5
    if readout=="target_relative_mass":
        total=sum(state.values())
        # Ratio uses target relative to all terminal reached states.
        return (mass/max(1e-9,total))>=0.45 and mass>0.005
    if readout=="signed_margin":
        return mass>=0.05
    raise Quarantined("ILLEGAL_YGG_READOUT")

def paired_score(lane,cases,pred):
    need(len(cases)==48,"INVALID_EVAL_SET")
    if lane=="Wingless":
        return wobserve.paired_accuracy(cases,pred)
    return ybind.paired_accuracy(cases,pred)

def evaluate_lane(lane,cfg):
    train,diagnostic=groups(lane)
    if lane=="Wingless":
        old=wobserve.public_groups()
        model=wobserve.LearnedObservationSelector().fit(old[0]+old[1])
        blind=wobserve.LearnedObservationSelector(depth_blind=True).fit(old[0]+old[1])
        base=lambda p,v:model.predicts(p,v)
        negative=lambda p:p.negative_values
        oracle=lambda p,v:wobserve.coded_depth_observation_oracle(p,v)
        candidate=lambda ast:(lambda p,v:wing_pred(model,ast,p,v))
        compare=lambda p,v:blind.predicts(p,v)
        params=model.parameters
        cost_baseline=1
    else:
        old=ybind.public_cohorts()
        model=ybind.LearnedVariableBinder().fit(old[0]+old[1])
        blind=ybind.LearnedVariableBinder(blind=True).fit(old[0]+old[1])
        base=lambda p,v:model.predicts(p,v)
        negative=lambda p:p.negative_variables
        oracle=lambda p,v:ybind.coded_exact_binding_oracle(p,v)
        candidate=lambda ast:(lambda p,v:ygg_pred(model,ast,p,v))
        compare=lambda p,v:blind.predicts(p,v)
        params=model.parameter_count
        cost_baseline=18
    need(model.training_updates==blind.training_updates==100,"CHANGED_PARENT_FIT")
    programs=list(generated_programs(lane,cfg))
    # All mechanism fitness computations use train-only input.
    for p in programs:
        p["train_paired_accuracy"]=paired_score(lane,train,candidate(p["ast"]))
    # Cost/accuracy Pareto frontier, retain ALL losers in the archive.
    for p in programs:
        p["pareto_nondominated"]=not any(
            (x["train_paired_accuracy"]>=p["train_paired_accuracy"] and
             x["cost"]<=p["cost"] and
             (x["train_paired_accuracy"]>p["train_paired_accuracy"] or
              x["cost"]<p["cost"]))
            for x in programs)
    frontier=[p for p in programs if p["pareto_nondominated"]]
    need(bool(frontier),"EMPTY_PARETO_FRONTIER")
    chosen=sorted(frontier,key=lambda p:(
        -p["train_paired_accuracy"],p["cost"],p["sha256"]))[0]
    # Diagnostic cohort is touched only AFTER a finalist is frozen in memory.
    final_pred=candidate(chosen["ast"])
    score=paired_score(lane,diagnostic,final_pred)
    prior=paired_score(lane,diagnostic,base)
    comparator=paired_score(lane,diagnostic,compare)
    coded=paired_score(lane,diagnostic,oracle)
    need(coded==1.,"NEW_PUBLIC_DATASET_GROUND_TRUTH_INVALID")
    family={}
    for instance in (0,1,2):
        subset=[p for p in diagnostic if p.specimen==instance]
        family[str(instance)]=(
          sum(final_pred(p,p.positive_values) and
              not final_pred(p,p.negative_values) for p in subset)/len(subset)
          if lane=="Wingless" else
          sum(final_pred(p,p.positive_variables) and
              not final_pred(p,p.negative_variables) for p in subset)/len(subset))
    false_positives=sum(final_pred(p,negative(p)) for p in diagnostic)/48
    limits=cfg["selection_policy"]["final_screen_thresholds"]
    ok=(score>=limits["minimum_diagnostic_paired_accuracy"] and
        score-comparator>=limits["minimum_gain_vs_blind"] and
        min(family.values())>=limits["minimum_worst_family_accuracy"])
    outcome=("POSITIVE_DEV_NEW_STRUCTURE_ONLY" if ok else
             "NEGATIVE_DEV_NEW_STRUCTURE_PRESERVED")
    next_step=("FALSIFY_SELECTED_PROGRAM_ON_DIFFERENT_GRAPH_AND_SIGNAL_FAMILY" if ok else
               "REJECT_OR_REDESIGN_SELECTED_PROGRAM_WITHOUT_TEST_RETUNING")
    return dict(lane=lane,source_parent_C2="W100-C2" if lane=="Wingless" else "Y100-C2",
        new_train_pairs=48,new_diagnostic_pairs=48,
        parent_training_updates=100,trained_parent_parameters=params,
        candidates_generated=len(programs),
        distinct_structural_families=len({p["family"] for p in programs}),
        all_candidate_train_results=[dict(
            ast=list(p["ast"]),sha256=p["sha256"],family=p["family"],
            cost=p["cost"],train_paired_accuracy=p["train_paired_accuracy"],
            pareto_nondominated=p["pareto_nondominated"]) for p in programs],
        pareto_frontier_size=len(frontier),
        selected_program_ast=list(chosen["ast"]),
        selected_program_fingerprint=chosen["sha256"],
        selected_train_paired_accuracy=chosen["train_paired_accuracy"],
        selected_cost=chosen["cost"],
        finalist_diagnostic_accuracy=score,
        frozen_parent_diagnostic_accuracy=prior,
        independently_trained_blind_diagnostic_accuracy=comparator,
        coded_oracle_separate_control_accuracy=coded,
        worst_new_family_accuracy=min(family.values()),
        each_new_family_accuracy=family,
        negative_false_positive_rate=false_positives,
        screen_passed=ok,outcome=outcome,
        new_feedback_advisory=next_step,
        novel_mechanism_class="TYPED_EXECUTABLE_STRUCTURAL_RECOMBINATION_NOT_GPT_GENERATION",
        no_protected_first_use=True,no_automatic_dispatch=True)

def evaluate(source_sha,evidence_root):
    need(type(source_sha) is str and SHA40.fullmatch(source_sha) is not None and
         (not os.environ.get("GITHUB_SHA") or os.environ["GITHUB_SHA"]==source_sha),
         "RUN_SOURCE_SHA_DRIFT")
    cfg,freeze_hash=frozen()
    root=Path(evidence_root).resolve()
    f106_json,digest=receipt_current(
        root/cfg["f106_report"],root/cfg["f106_receipt"],source_sha)
    outcomes=[evaluate_lane("Wingless",cfg),evaluate_lane("Yggdrasil",cfg)]
    return dict(schema=REPORT,source_sha=source_sha,
        evidence_class="BOUNDED_NEW_PUBLIC_DEVELOPMENT_MECHANISM_PROGRAM_SEARCH_ONLY",
        freeze_sha256=freeze_hash,parent_F106_report_sha256=digest,
        F106_feedback_consumed=True,
        real_machine_generated_typed_programs=True,
        candidate_count=sum(x["candidates_generated"] for x in outcomes),
        independent_new_cohorts_per_lane=2,
        choices_from_train_only=True,
        diagnostic_not_used_to_choose=True,
        lanes=outcomes,
        next_proposals=[dict(lane=x["lane"],hypothesis=x["new_feedback_advisory"],
                             executable_without_next_preregistration=False)
                        for x in outcomes],
        scientific_originals_executed=0,independent_science_accepted=0,
        protected_first_use_authorized=False,
        auto_native_experiment_dispatches=0,
        accepted_ref_mutations=0,optimizer_promotions=0,
        codex_invocations=0,paid_api_calls=0,
        work_tasks=0,ckb_plane_contact=False,
        cloudflare_writes=0,new_schedulers=0,free_form_GPT_inference=False)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source-ref",required=True)
    p.add_argument("--evidence-root",required=True)
    a=p.parse_args()
    print(json.dumps(evaluate(a.source_ref,a.evidence_root),
                     sort_keys=True,separators=(",",":")))

if __name__=="__main__":
    try: main()
    except (Quarantined,f106.Quarantined,ybind.Rejected,wobserve.Rejected,
            ValueError,KeyError,TypeError,OSError) as e:
        print("FORGE_F107_MECHANISM_GENERATION=QUARANTINED "+str(e),file=sys.stderr)
        raise SystemExit(1)
