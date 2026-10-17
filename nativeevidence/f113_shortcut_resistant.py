"""F113: preregistered shortcut-resistant public source relationships.

Counterfactual target sources are balanced independently of query depth and
position. Strong edit-distance controls receive identical public strings and
one-value observation budget. Never tune from held-out results. Yggdrasil tests
near-compatible (one variable mismatch) false routes in competing path graphs.
No protected first-use, original science, Codex, model API, or dispatch.
"""
import argparse
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import random
import re
import sys

import f103_yggdrasil_public_binding as ybind
import f109_failure_driven_mechanisms as f109
import f110_capacity_transfer as f110
import f112_learned_relations as f112

ROOT=Path(__file__).resolve().parents[1]
FREEZE=ROOT/"reference/research-intake/f113-shortcut-resistant-freeze.json"
FREEZE_BLOB="b6cbc3ec597115fc544ea91a824a279d09696703"
PARENT_F112_BLOB="838050a30a37961525eba29cab42a32f651c8ca0"
PARENT="9bd5269582e537cf5e7537c1298ec29611ddec16"
SCHEMA="forge.autonomy.f113.frozen-source-route-shortcut-and-hard-binding-test.v1"
REPORT="forge.autonomy.f113.shortcut-resistant-source-routing-and-graph-binding-public.v1"
SHA40=re.compile(r"^[0-9a-f]{40}$")
class Quarantined(ValueError):pass
def need(flag,reason):
    if not flag:raise Quarantined("F113_"+reason)
def gitblob(b):
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def canonical(path):
    return Path(path).read_bytes().replace(b"\r\n",b"\n")
def frozen():
    raw=canonical(FREEZE)
    need(gitblob(raw)==FREEZE_BLOB and
         gitblob(canonical(ROOT/"nativeevidence/f112_learned_relations.py"))==
         PARENT_F112_BLOB,"PREREG_OR_PARENT_SOURCE_DRIFT")
    cfg=json.loads(raw)
    need(cfg.get("schema")==SCHEMA and cfg.get("parent_F112_exact_head_sha")==PARENT and
         cfg.get("parent_F112_implementation_blob")==PARENT_F112_BLOB and
         cfg.get("parent_F112_protocol_blob")=="c42f5baaaa4cd77395229a153b059bcd4fa08181",
         "PARENT_F112_ANCESTRY_CHANGED")
    w,y=cfg["Wingless"],cfg["Yggdrasil"]
    need(w["training"]=={"seeds":[69000,69031],"instances_per_seed":3,
         "pairs":96,"updates":100} and
         [(c["name"],c["seeds"]) for c in w["diagnostic"]]==[
         ("W113-A",[69048,69095]),("W113-B",[69100,69147]),
         ("W113-C",[69200,69247])] and
         w["required_position_contingency_each_block"]==
         "for_every_query_and_correct_tag_count_exactly_3" and
         w["max_queried_position_correct_from_depth_only_each_block"]==0.25 and
         w["no_exact_unmodified_query_source_equality_in_test"] is True and
         w["models"]==[
         "F112_six_parameter_trainable_engineered_similarity_metric_retrained_on_F113_96_pairs",
         "fixed_uniform_six_feature_similarity_no_fit",
         "F110_equal_or_larger_64_parameter_query_only_attention_trained_on_identical_96_pairs",
         "deterministic_public_minimum_Levenshtein_distance_control_one_read",
         "F109_additive_offset_model_fixed_zero_no_privileged_adapter"] and
         w["score"]=={
         "minimum_learned_paired_accuracy_per_block":0.75,
         "minimum_pooled_net_learned_over_fixed_similarity":18,
         "minimum_pooled_net_learned_over_edit_distance_control":18,
         "maximum_query_only_shortcut_accuracy_per_block":0.35,
         "minimum_worst_block_accuracy":0.60},
         "TRAIN_SPLIT_OR_CONTROLS_DRIFT")
    need([(c["name"],c["seeds"]) for c in y["diagnostic"]]==[
         ("Y113-A",[69300,69347]),("Y113-B",[69400,69447]),
         ("Y113-C",[69500,69547])] and
         all(c["mismatch_per_false_branch"]==1 for c in y["diagnostic"]) and
         y["edge_count"]==12 and y["variable_slot_count"]==16 and
         y["minimum_strict_over_soft_net_paired_advantage"]==18 and
         y["training_updates_unchanged"]==100 and
         y["no_retrain_on_diagnostic"] is True,"GRAPH_CHALLENGE_DRIFT")
    need(cfg["mandatory_F112_negative"]=={
         "Wingless":{"learned_correct":[48,48,48],
                     "fixed_feature_correct":[48,48,48],
                     "modular_offset_correct":[48,48,48],
                     "learned_superiority":False,
                     "confound":"F112_chosen_equals_query_depth_in_all_diagnostic_cases"},
         "Yggdrasil":{"strict_correct":[48,48,48],
                     "soft_correct":[48,48,48],"strict_superiority":False}},
         "F112_FAILURE_ERASED")
    need(all(cfg["integrity"].get(k) is True for k in (
         "freeze_before_implementation","source_bound_F112_raw_SHA256_verified",
         "recompute_F112_from_ancestor_receipts",
         "full_288_pairwise_records_and_controls_preserved",
         "failed_research_screen_not_ci_error","no_hindsight_diagnostic_retuning",
         "no_codex","no_paid_llm","no_work_tasks","no_new_scheduler",
         "no_cloudflare_write","no_ckb_plane_contact","no_mind_palace_write",
         "no_other_repo_writes","no_protected_first_use","no_accepted_refs",
         "no_optimizer_promotion","no_independent_science_acceptance",
         "no_native_scientific_dispatch")),"UNAUTHORIZED_SCIENTIFIC_ACTION")
    return cfg,hashlib.sha256(raw).hexdigest()

def receive_F112(source,root,cfg):
    base=Path(root).resolve()
    report=base/cfg["current_run_F112_report"]
    receipt=base/cfg["current_run_F112_receipt"]
    raw=report.read_bytes()
    marker=receipt.read_bytes().decode("utf-8-sig").strip()
    match=re.fullmatch(r"([a-f0-9]{64})  ([A-Za-z0-9_.-]+)",marker)
    need(bool(match) and match.group(2)==report.name and
         hashlib.sha256(raw).hexdigest()==match.group(1),
         "PARENT_F112_SHA256_RECEIPT_TAMPER")
    got=json.loads(raw.decode("utf-8-sig"))
    expect=f112.evaluate(source,base)
    need(got==expect and got.get("source_sha")==source and
         got.get("schema")==f112.REPORT and
         got.get("protected_first_use_authorized") is False and
         got.get("accepted_ref_mutations")==0 and got.get("codex_calls")==0 and
         len(got.get("lanes",[]))==2,"F112_REPORT_REPLAY_OR_AUTHORITY")
    w,y=got["lanes"]
    spec=cfg["mandatory_F112_negative"]
    need(w["lane"]=="Wingless" and
         [v["correct_pairs_by_arm"]["learned_relational_features"]
          for v in w["blocks"]]==spec["Wingless"]["learned_correct"] and
         [v["correct_pairs_by_arm"]["fixed_uniform_feature_weights"]
          for v in w["blocks"]]==spec["Wingless"]["fixed_feature_correct"] and
         [v["correct_pairs_by_arm"]["legacy_modular_offset_64"]
          for v in w["blocks"]]==spec["Wingless"]["modular_offset_correct"] and
         w["learned_generalization_screen_passed"] is False and
         y["lane"]=="Yggdrasil" and
         [v["correct_pairs_by_arm"]["hard_slot_same_learned_role20"]
          for v in y["blocks"]]==spec["Yggdrasil"]["strict_correct"] and
         [v["correct_pairs_by_arm"]["soft_slot_parent20"]
          for v in y["blocks"]]==spec["Yggdrasil"]["soft_correct"] and
         y["improvement_screen_passed"] is False,
         "PARENT_F112_NEGATIVE_RELABEL")
    return hashlib.sha256(raw).hexdigest()

@dataclass(frozen=True)
class Case:
    public:f112.WCase
    true_source_tag:int
    cohort:int

def targets(group):
    # A prospectively balanced but per-group independently scrambled 4x4
    # contingency. For EACH query q, each of four source tags occurs 3 times.
    seen=[]
    for q in range(4):
        choices=[v for v in range(4) for _ in range(3)]
        random.Random(113000+group*97+q*13).shuffle(choices)
        seen.append(choices)
    return seen

def make_case(seed,group,instance,idx):
    rng=random.Random(seed*1229+group*181+instance*47+113)
    q=(idx+instance)%4
    # For diagnostics instance=0; distinct source tag independently assigned
    # within each q, and never derived by a fixed offset.
    per_query_idx=(idx//4)%12 if instance==0 else (idx+instance*5)%12
    chosen=targets(group)[q][per_query_idx]
    alphabet="ABCDEFGHJKLMNPQRSTUVWXYZ" if group in (0,1) else "0123456789ABCDEFGH"
    while True:
        strings=["".join(rng.choice(alphabet) for _ in range(9)) for _ in range(4)]
        if len(set(strings))==4 and all(
            levenshtein(strings[i],strings[j])>=5 for i in range(4)
            for j in range(i+1,4)):break
    original=strings[chosen]
    if group==0:
        at=rng.randrange(1,8)
        repl=rng.choice([c for c in alphabet if c!=original[at]])
        request=original[:at]+repl+original[at+1:]
    elif group==1:
        at=rng.randrange(1,7)
        request=original[:at]+original[at+1]+original[at]+original[at+2:]
        if request==original: # repeated adjacent char
            request=original[:at]+alphabet[(alphabet.index(original[at])+1)%len(alphabet)]+original[at+1:]
    else:
        at=rng.randrange(1,8)
        request=original[:at]+original[at+1:]
    order=list(range(4));rng.shuffle(order)
    baseline=[rng.choice((-1.0,1.0)) for _ in range(4)]
    plus=baseline.copy();minus=baseline.copy()
    plus[chosen]=1.;minus[chosen]=-1.
    p=f112.WCase(seed,group,tuple(strings),request,
                 tuple(plus[t] for t in order),
                 tuple(minus[t] for t in order),q,tuple(order))
    need(chosen!=q or group>=0,"IMPOSSIBLE")
    need(request not in strings and
         min(levenshtein(request,s) for s in strings)==
              levenshtein(request,original) and
         sum(a!=b for a,b in zip(p.positive_values,p.negative_values))==1 and
         oracle(p,p.positive_values) and not oracle(p,p.negative_values),
         "INVALID_RELATION_COUNTERFACTUAL")
    return Case(p,chosen,group)

def oracle(p,values):
    # Offline separate test-label control, never used by model inference.
    return values[p.observation_depths.index(
        min(range(4),key=lambda j:levenshtein(p.requested_code,p.source_codes[j])))]>0

def levenshtein(a,b):
    # Deterministic strong public edit distance control; no label access.
    old=list(range(len(b)+1))
    for i,ca in enumerate(a,1):
        new=[i]
        for j,cb in enumerate(b,1):
            new.append(min(new[-1]+1,old[j]+1,old[j-1]+(ca!=cb)))
        old=new
    return old[-1]

def edit_distance_control(p,values):
    best=min(range(4),key=lambda tag:(
        levenshtein(p.requested_code,p.source_codes[tag]),tag))
    return values[p.observation_depths.index(best)]>0

def wing_groups():
    train=tuple(make_case(s,0,inst,(s-69000)*3+inst) for s in range(69000,69032)
                for inst in range(3))
    blocks=tuple(tuple(make_case(seed,g,0,i) for i,seed in enumerate(range(lo,hi+1)))
        for g,(lo,hi) in enumerate(((69048,69095),(69100,69147),(69200,69247)),1))
    need(len(train)==96 and len({(p.public.seed,i) for i,p in enumerate(train)})==96 and
         all(len(b)==48 for b in blocks),"PUBLIC_COHORT_BUDGET")
    for block in blocks:
        n={(q,t):0 for q in range(4) for t in range(4)}
        for c in block:
            n[c.public.query_depth,c.true_source_tag]+=1
        need(all(value==3 for value in n.values()),
             "QUERY_DEPTH_SOURCE_POSITION_LEAK")
    return train,blocks

def wing_eval(cfg):
    train,blocks=wing_groups()
    learned=f112.LearnedRelationAttention().train(tuple(c.public for c in train))
    fixed=f112.fixed_similarity
    baseline_train=tuple(f109.WCase(f110.wobserve.Case(
        c.public.seed,c.cohort,i%3,c.public.query_depth,
        c.public.observation_depths,c.public.positive_values,c.public.negative_values),
        0,c.cohort) for i,c in enumerate(train))
    queryonly=f110.CapacityMatchedQueryOnly().train(baseline_train)
    historical,_=f109.wing_cohorts()
    legacy=f109.LearnedSourceRouting().train(historical)
    need(learned.updates==queryonly.steps==legacy.steps==100 and
         learned.parameters==6 and queryonly.parameters==64,"TRAINING_OR_CAPACITY_DRIFT")
    arms={
     "learned_six_feature_metric":learned.predicts,
     "fixed_six_feature_metric":fixed,
     "trained_query_only_64":lambda p,v:f112.original_query_only(p,v,queryonly),
     "full_public_edit_distance_one_read":edit_distance_control,
     "legacy_modular_offset":lambda p,v:f112.legacy_offset(p,v,legacy)}
    reports=[]
    for index,cases in enumerate(blocks):
        rows=[]
        for case in cases:
            p=case.public
            need(edit_distance_control(p,p.positive_values) and
                 not edit_distance_control(p,p.negative_values),
                 "FULL_INFORMATION_CONTROL_INVALID")
            decisions={k:bool(fn(p,p.positive_values) and
                              not fn(p,p.negative_values)) for k,fn in arms.items()}
            rows.append(dict(seed=p.seed,query_depth=p.query_depth,
                true_source_tag=case.true_source_tag,paired_correct=decisions))
        counts={k:sum(x["paired_correct"][k] for x in rows) for k in arms}
        contingency={str(q)+":"+str(t):sum(
          r["query_depth"]==q and r["true_source_tag"]==t for r in rows)
          for q in range(4) for t in range(4)}
        need(all(v==3 for v in contingency.values()),"NONINDEPENDENT_QUERY_SOURCE")
        reports.append(dict(block=index,paired_cases=48,
                            correct_pairs_by_arm=counts,
                            query_source_contingency=contingency,
                            all_paired_decisions=rows))
    allrows=[r for g in reports for r in g["all_paired_decisions"]]
    def gain(base):
        return sum(r["paired_correct"]["learned_six_feature_metric"] and
                    not r["paired_correct"][base] for r in allrows)-sum(
                    r["paired_correct"][base] and
                    not r["paired_correct"]["learned_six_feature_metric"]
                    for r in allrows)
    threshold=cfg["Wingless"]["score"]
    learned_scores=[b["correct_pairs_by_arm"]["learned_six_feature_metric"]
                    for b in reports]
    query=[b["correct_pairs_by_arm"]["trained_query_only_64"] for b in reports]
    g_fixed=gain("fixed_six_feature_metric")
    g_edit=gain("full_public_edit_distance_one_read")
    pass_screen=(min(learned_scores)/48>=threshold["minimum_learned_paired_accuracy_per_block"] and
        g_fixed>=threshold["minimum_pooled_net_learned_over_fixed_similarity"] and
        g_edit>=threshold["minimum_pooled_net_learned_over_edit_distance_control"] and
        max(query)/48<=threshold["maximum_query_only_shortcut_accuracy_per_block"])
    return dict(lane="Wingless",training_pairs=96,training_updates_each=100,
        learned_parameters=6,trained_query_control_parameters=64,
        each_arm_reads_one_evidence_value=True,
        query_source_contingency_balanced=True,
        blocks=reports,diagnostic_pairs=144,net_gain_vs_fixed=g_fixed,
        net_gain_vs_edit_distance=g_edit,
        no_superiority_over_perfect_public_algorithm=(
            sum(learned_scores)<=sum(b["correct_pairs_by_arm"][
                "full_public_edit_distance_one_read"] for b in reports)),
        independent_source_relation_screen_passed=pass_screen,
        disposition=("PUBLIC_BOUNDED_LEARNED_RELATION_SCREEN_NO_SCIENCE" if pass_screen
            else "NO_SUPERIORITY_OVER_STRONG_PUBLIC_CONTROLS_NEGATIVE_RETAINED"),
        no_unrestricted_representation_learning_claim=True)

def graph_case(seed,block):
    rng=random.Random(seed*137+block*1907+113)
    roles=tuple(rng.randrange(4) for _ in range(4))
    target=20
    edges=[];typed=[];vars_=[]
    for branch in range(3):
        path=(0,branch*3+1,branch*3+2,branch*3+3,target)
        edges.extend(zip(path[:-1],path[1:]))
        slot=[rng.randrange(16) for _ in range(5)]
        chain=[(slot[k],slot[k+1]) for k in range(4)]
        if branch>0:
            broken=1+(seed+branch+block)%3
            a,b=chain[broken]
            chain[broken]=((chain[broken-1][1]+1+
                 (seed+block+branch)%15)%16,b)
        vars_+=chain;typed+=roles
    negative=list(vars_)
    breakidx=1+seed%3
    oldlhs,oldrhs=negative[breakidx]
    negative[breakidx]=((vars_[breakidx-1][1]+1+seed%15)%16,oldrhs)
    order=list(range(12));rng.shuffle(order)
    p=ybind.Pair(seed,block,0,tuple(edges[i] for i in order),
        tuple(typed[i] for i in order),
        tuple(vars_[i] for i in order),tuple(negative[i] for i in order),
        roles,0,target,breakidx-1)
    need(ybind.coded_exact_binding_oracle(p,p.positive_variables) and
         not ybind.coded_exact_binding_oracle(p,p.negative_variables) and
         sum(a!=b for x,y in zip(p.positive_variables,p.negative_variables)
             for a,b in zip(x,y))==1,"GRAPH_LABEL_OR_ALTERNATIVE_PATH_INVALID")
    return p
def graph_groups():
    groups=tuple(tuple(graph_case(seed,g) for seed in range(lo,hi+1))
       for g,(lo,hi) in enumerate(((69300,69347),(69400,69447),(69500,69547))))
    need(all(len(g)==48 for g in groups) and
         len({p.seed for g in groups for p in g})==144,"GRAPH_COHORT_REUSE")
    return groups

def ygg_eval(cfg):
    old=ybind.public_cohorts()
    soft=ybind.LearnedVariableBinder().fit(old[0]+old[1])
    blind=ybind.LearnedVariableBinder(blind=True).fit(old[0]+old[1])
    need(soft.training_updates==blind.training_updates==100,
         "YGG_PARENT_TRAINING_DRIFT")
    arms={
     "unchanged_soft_slot20":soft.predicts,
     "strict_slot_same_learned_role20":lambda p,v:f109.strict_slot_predict(soft,p,v),
     "trained_variable_blind20":blind.predicts,
     "separate_exact_coded_oracle":ybind.coded_exact_binding_oracle}
    blocks=[]
    for group,cases in enumerate(graph_groups()):
        records=[]
        for p in cases:
            need(ybind.coded_exact_binding_oracle(p,p.positive_variables) and
                 not ybind.coded_exact_binding_oracle(p,p.negative_variables),
                 "GRAPH_ORACLE_TRUTH")
            records.append(dict(seed=p.seed,paired_correct={
               k:bool(fn(p,p.positive_variables) and not fn(p,p.negative_variables))
               for k,fn in arms.items()}))
        score={name:sum(r["paired_correct"][name] for r in records)
               for name in arms}
        need(score["separate_exact_coded_oracle"]==48,"STRONG_CODED_ORACLE_FAILURE")
        blocks.append(dict(block=group,paired_cases=48,
                           correct_pairs_by_arm=score,
                           all_paired_decisions=records))
    rows=[r for b in blocks for r in b["all_paired_decisions"]]
    hard_only=sum(r["paired_correct"]["strict_slot_same_learned_role20"] and
         not r["paired_correct"]["unchanged_soft_slot20"] for r in rows)
    soft_only=sum(r["paired_correct"]["unchanged_soft_slot20"] and
         not r["paired_correct"]["strict_slot_same_learned_role20"] for r in rows)
    net=hard_only-soft_only
    passed=net>=cfg["Yggdrasil"]["minimum_strict_over_soft_net_paired_advantage"]
    return dict(lane="Yggdrasil",unchanged_parent_training_updates=100,
       parameters_each=20,graph_edges_each=12,new_diagnostic_pairs=144,
       blocks=blocks,hard_only_correct=hard_only,soft_only_correct=soft_only,
       net_hard_advantage=net,
       novel_variable_binding_screen_passed=passed,
       disposition=("PUBLIC_NEAR_MISS_BRANCH_STRUCTURAL_GAIN_NOT_SCIENCE" if passed
         else "NO_SUPERIORITY_OVER_PARENT_NEGATIVE_RETAINED"))

def evaluate(source,evidence_root):
    need(type(source) is str and SHA40.fullmatch(source) is not None and
         (not os.environ.get("GITHUB_SHA") or
          os.environ["GITHUB_SHA"]==source),"CURRENT_GITHUB_SHA_REQUIRED")
    cfg,digest=frozen()
    f112digest=receive_F112(source,evidence_root,cfg)
    return dict(schema=REPORT,source_sha=source,freeze_sha256=digest,
        authenticated_F112_sha256=f112digest,
        evidence_class="PUBLIC_SYNTHETIC_NO_INDEPENDENT_SCIENTIFIC_FIRST_USE",
        frozen_counterfactuals_per_lane=144,
        preexisting_negative_evidence_retained=True,
        all_288_paired_decisions_retained=True,
        lanes=[wing_eval(cfg),ygg_eval(cfg)],
        protected_first_use_authorized=False,independent_science_accepted=0,
        scientific_originals_dispatched=0,accepted_ref_mutations=0,
        optimizer_promotions=0,codex_calls=0,paid_model_calls=0,
        work_tasks=0,new_schedulers=0,cloudflare_writes=0,
        ckb_plane_contact=False,mind_palace_writes=0)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--source-ref",required=True)
    parser.add_argument("--evidence-root",required=True)
    args=parser.parse_args()
    print(json.dumps(evaluate(args.source_ref,args.evidence_root),
                     sort_keys=True,separators=(",",":")))

if __name__=="__main__":
    try:main()
    except (Quarantined,f112.Quarantined,f110.Quarantined,f109.Quarantined,
       ybind.Rejected,f110.wobserve.Rejected,ValueError,KeyError,TypeError,OSError) as e:
        print("FORGE_F113_SHORTCUT_RESISTANT=QUARANTINED "+str(e),file=sys.stderr)
        raise SystemExit(1)
