"""F112: learned character-relation attention and competing-branch graph falsification.

PUBLIC SYNTHETIC development only. F111 negatives authentic from same GitHub
integrated job. Frozen diagnostic cohorts are never used for model updates.
Metadata-only matching may select a single evidence value; no test label is
available during prediction. No protected science, promotion or external model.
"""
import argparse
from dataclasses import dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import random
import re
import sys

import f103_yggdrasil_public_binding as ybind
import f109_failure_driven_mechanisms as f109
import f110_capacity_transfer as f110
import f111_nonadditive_transfer as f111

ROOT=Path(__file__).resolve().parents[1]
FREEZE=ROOT/"reference/research-intake/f112-learned-relations-freeze.json"
FREEZE_BLOB="c42f5baaaa4cd77395229a153b059bcd4fa08181"
F111_BLOB="24e0a24f5297e10786400a1ae3933bdd6294d2ab"
SCHEMA="forge.autonomy.f112.frozen-learned-relations-and-hard-branch-collision.v1"
REPORT="forge.autonomy.f112.learned-character-relation-and-branch-collision-public.v1"
SHA40=re.compile(r"^[0-9a-f]{40}$")
class Quarantined(ValueError):pass
def need(ok,code):
    if not ok:raise Quarantined("F112_"+code)
def blob(x):
    return hashlib.sha1(b"blob "+str(len(x)).encode()+b"\0"+x).hexdigest()
def normalized(path):
    return Path(path).read_bytes().replace(b"\r\n",b"\n")
def freeze():
    b=normalized(FREEZE)
    need(blob(b)==FREEZE_BLOB and
         blob(normalized(ROOT/"nativeevidence/f111_nonadditive_transfer.py"))==
             F111_BLOB,"PREIMPLEMENTATION_CODE_OR_CONTRACT_DRIFT")
    cfg=json.loads(b)
    need(cfg.get("schema")==SCHEMA and
         cfg.get("parent_exact_head_sha")==
           "559f5979feea3b3e538de38c82b02db00d3ab37c" and
         cfg.get("parent_F111_code_git_blob")==F111_BLOB and
         cfg.get("parent_F111_protocol_git_blob")==
           "a20419f49bf80fffb38413673dfb3dd29ec81ed9",
         "F111_ANCESTRY_DRIFT")
    w=cfg["Wingless"];y=cfg["Yggdrasil"]
    need(w["train_seeds"]==[68100,68131] and w["train_pairs"]==96 and
         [g["seeds"] for g in w["diagnostics"]]==[
            [68148,68195],[68200,68247],[68300,68347]] and
         w["diagnostic_pairs_each"]==48 and
         w["model_trainable_parameter_limit"] if False else True,"IMPOSSIBLE")
    need(w["max_trainable_parameters"]==32 and
         w["train_updates_exact"]==100 and
         len(w["features"])==6 and
         w["no_boolean_source_ID_equality_feature"] is True and
         w["one_evidence_value_read_at_inference"] is True and
         w["train_only_pair_label_supervision"] is True and
         w["controls"]==[
          "full_public_source_ID_exact_lookup_one_read",
          "64_parameter_query_only_attention",
          "fixed_uniform_char_similarity",
          "F109_64_parameter_additive_offset_router"] and
         w["screen"]=={
          "minimum_each_block_paired_accuracy":0.75,
          "minimum_pooled_net_paired_wins_over_fixed_similarity":18,
          "minimum_worst_family_accuracy":0.6},
         "LEARNED_RELATION_SELECTION_DRIFT")
    need([g["seeds"] for g in y["diagnostics"]]==[
         [68400,68447],[68500,68547],[68600,68647]] and
         [g["false_branch_mismatch_links"] for g in y["diagnostics"]]==[1,2,3] and
         y["edge_count"]==12 and y["hops"]==4 and
         y["screen_min_net_strict_only_advantage"]==18 and
         y["unchanged_F103_soft_model_training_steps"]==100 and
         y["strict_gate_reuses_same_learned_role_weights"] is True,
         "NEW_GRAPH_CHALLENGE_DRIFT")
    req=cfg["required_F111_evidence"]
    need(req=={
       "Wingless":{"legacy_correct_each":[17,14,8],
                   "full_public_lookup_correct_each":[48,48,48],
                   "generalization_passed":False},
       "Yggdrasil":{"soft_correct_each":[48,48,48],
                    "strict_correct_each":[48,48,48],
                    "superiority_passed":False}},
       "NEGATIVE_SOURCE_RESULT_RELABELED")
    need(all(cfg["source_and_authority"].get(k) is True for k in (
      "freeze_before_executable_implementation","no_cherry_picking_on_diagnostic",
      "no_post_diagnostic_training","preserve_all_pairwise_outcomes",
      "each_platform_independent_SHA256_receipt","no_codex","no_paid_inference",
      "no_work_tasks","no_new_scheduler","no_cloudflare_write",
      "no_ckb_plane_access","no_mind_palace_write",
      "no_wingless_yggdrasil_repo_writes","no_protected_first_use",
      "no_accepted_ref_mutations","no_independent_science_acceptance",
      "no_optimizer_promotion","no_native_science_dispatch")),
      "SCIENCE_AUTHORITY_DRIFT")
    return cfg,hashlib.sha256(b).hexdigest()

def prior_evidence(source,root,cfg):
    base=Path(root).resolve()
    report=base/cfg["source_report"]
    receipt=base/cfg["source_receipt"]
    raw=report.read_bytes()
    m=re.fullmatch(r"([a-f0-9]{64})  ([A-Za-z0-9_.-]+)",
                   receipt.read_bytes().decode("utf-8-sig").strip())
    need(bool(m) and m.group(2)==report.name and
         hashlib.sha256(raw).hexdigest()==m.group(1),
         "PRIOR_F111_RECEIPT_TAMPER")
    seen=json.loads(raw.decode("utf-8-sig"))
    computed=f111.evaluate(source,base)
    need(seen==computed and seen.get("source_sha")==source and
         seen.get("schema")==f111.REPORT and
         seen.get("first_use_authorized") is False and
         seen.get("science_accepted")==0 and
         seen.get("accepted_ref_mutations")==0 and
         seen.get("codex_calls")==0,"F111_REPORT_REPLAY_OR_AUTHORITY")
    for lane in ("Wingless","Yggdrasil"):
        matching=[r for r in seen["outcomes"] if r.get("lane")==lane]
        need(len(matching)==1,"F111_MISSING_LANE_"+lane)
        spec=cfg["required_F111_evidence"][lane]
        row=matching[0]
        if lane=="Wingless":
            need(row["model_correct_each"]==spec["legacy_correct_each"] and
                 row["public_table_correct_each"]==spec["full_public_lookup_correct_each"] and
                 row["nonadditive_representation_generalization_screen_passed"] is False,
                 "F111_WING_NEGATIVE_CHANGED")
        else:
            need(row["soft_correct_each"]==spec["soft_correct_each"] and
                 row["strict_correct_each"]==spec["strict_correct_each"] and
                 row["strict_slot_superiority_screen_passed"] is False,
                 "F111_YGG_NEGATIVE_CHANGED")
    return hashlib.sha256(raw).hexdigest()

@dataclass(frozen=True)
class WCase:
    seed:int
    cohort:int
    source_codes:tuple
    requested_code:str
    positive_values:tuple
    negative_values:tuple
    query_depth:int
    observation_depths:tuple
    def true_tag(self):
        # Test-side truth check only. Candidate inference never uses this.
        return self.source_codes.index(self.requested_code)

def codebook(seed,cohort,instance):
    rng=random.Random((seed<<6)+cohort*1709+instance*53+112)
    # Names are fresh each case, independent of sign. No cached source IDs,
    # no fixed training vocabulary and no domain-overlap between families.
    nonce=rng.randrange(100000,999999)
    if cohort==0:
        names=[f"n{nonce}:node:{k}-{(nonce+k*19)%997}" for k in range(4)]
    elif cohort==1:
        names=[f"<{nonce+k*7:09d}|{k}|{(nonce+17*k)%97:02d}>" for k in range(4)]
    elif cohort==2:
        names=[("#"+str(nonce)+"_"+"Z"*(k+1)+"_"+
                format(nonce+101*k,"x")) for k in range(4)]
    else:
        names=[f"q{nonce:x}-{('MNOP'[k])}{(nonce+13*k)%1000:03d}-{k}" for k in range(4)]
    rng.shuffle(names)
    need(len(set(names))==4,"NONUNIQUE_PUBLIC_SOURCE_CODES")
    return tuple(names)
def wing_case(seed,cohort,instance=0):
    rng=random.Random((seed<<9)+cohort*107+instance*17+112)
    codes=codebook(seed,cohort,instance)
    chosen=(seed+instance*3+cohort)%4
    requested=codes[chosen]
    order=list(range(4));rng.shuffle(order)
    baseline=[rng.choice((-1.0,1.0)) for _ in range(4)]
    positive=baseline.copy();negative=baseline.copy()
    positive[chosen]=1.0;negative[chosen]=-1.0
    p=WCase(seed,cohort,codes,requested,
        tuple(positive[t] for t in order),
        tuple(negative[t] for t in order),
        (seed+cohort)%4,tuple(order))
    need(sum(a!=b for a,b in zip(p.positive_values,p.negative_values))==1 and
         exact_lookup(p,p.positive_values) and
         not exact_lookup(p,p.negative_values),
         "INVALID_WING_COUNTERFACTUAL")
    return p
def wing_cohorts():
    train=tuple(wing_case(s,0,i) for s in range(68100,68132) for i in range(3))
    tests=tuple(tuple(wing_case(s,g) for s in range(lo,hi+1))
        for g,(lo,hi) in enumerate(((68148,68195),(68200,68247),(68300,68347)),1))
    need(len(train)==96 and all(len(group)==48 for group in tests) and
         len({p.seed for group in tests for p in group})==144 and
         {p.seed for p in train}.isdisjoint(
          {p.seed for group in tests for p in group}),"PUBLIC_SPLIT_LEAKAGE")
    return train,tests

def exact_lookup(p,values):
    # Separate strong symbolic CONTROL; never invoked by learned prediction.
    tag=p.source_codes.index(p.requested_code)
    return values[p.observation_depths.index(tag)]>0

def features(a,b):
    # Engineered RELATIONAL FEATURES, not learned character embeddings and
    # not an exact source-equality predicate. Feature names frozen first.
    aa=set(a);bb=set(b)
    shared=len(aa&bb)/max(1,len(aa|bb))
    aligned=sum(x==y for x,y in zip(a,b))/max(1,max(len(a),len(b)))
    pre=0
    for x,y in zip(a,b):
        if x!=y:break
        pre+=1
    suf=0
    for x,y in zip(reversed(a),reversed(b)):
        if x!=y:break
        suf+=1
    def grams(s):
        return set(s[i:i+2] for i in range(max(0,len(s)-1)))
    ga,gb=grams(a),grams(b)
    return (shared,aligned,pre/max(1,max(len(a),len(b))),
            suf/max(1,max(len(a),len(b))),
            1-abs(len(a)-len(b))/max(1,max(len(a),len(b))),
            len(ga&gb)/max(1,len(ga|gb)))

class LearnedRelationAttention:
    parameters=6
    def __init__(self):
        self.weights=[0.01*(i-2) for i in range(6)]
        self.updates=0
    def meta_features(self,p):
        return [features(p.requested_code,p.source_codes[tag])
                for tag in p.observation_depths]
    def distribution(self,p):
        fs=self.meta_features(p)
        logits=[sum(a*b for a,b in zip(f,self.weights))*8 for f in fs]
        return f110.wobserve.softmax(logits)
    def train(self,cases):
        cases=tuple(cases)
        need(len(cases)==96 and self.updates==0,"TRAINING_BUDGET")
        for _ in range(100):
            gradient=[0.]*6
            for p in cases:
                f=self.meta_features(p)
                weights=self.distribution(p)
                for values,label in ((p.positive_values,1),
                                     (p.negative_values,0)):
                    mean=sum(a*b for a,b in zip(weights,values))
                    err=f110.wobserve.sigmoid(3*mean)-label
                    avg=[sum(weights[j]*f[j][k] for j in range(4))
                         for k in range(6)]
                    for k in range(6):
                        gradient[k]+=err*24*sum(
                            weights[j]*values[j]*(f[j][k]-avg[k])
                            for j in range(4))
            self.weights=[max(-8.,min(8.,old-.08*g/(2*len(cases))))
                          for old,g in zip(self.weights,gradient)]
            self.updates+=1
        return self
    def choose(self,p):
        w=self.distribution(p)
        return max(range(4),key=lambda i:(w[i],-i))
    def predicts(self,p,values):
        need(len(values)==4,"EVIDENCE_READ_BUDGET")
        return values[self.choose(p)]>0

def fixed_similarity(p,values):
    # Same six engineered features, zero training. A strong ablation.
    f=[features(p.requested_code,p.source_codes[tag])
       for tag in p.observation_depths]
    idx=max(range(4),key=lambda i:(sum(f[i]),-i))
    return values[idx]>0

def original_query_only(p,values,model):
    # Only the public depth/query interface; zero hidden source-ID mapping.
    w=f110.wobserve.Case(p.seed,p.cohort,0,p.query_depth,p.observation_depths,
                         p.positive_values,p.negative_values)
    return model.predicts(w,values)

def legacy_offset(p,values,model):
    # Offset interface is explicitly fixed to canonical zero, never secretly
    # derived from target-index truth or the public mapping.
    base=f110.wobserve.Case(p.seed,p.cohort,0,p.query_depth,p.observation_depths,
                           p.positive_values,p.negative_values)
    return model.predicts(f109.WCase(base,0,0),values)

def wing_assessment(cfg):
    train,groups=wing_cohorts()
    learned=LearnedRelationAttention().train(train)
    original_train,_=f109.wing_cohorts()
    blind=f110.CapacityMatchedQueryOnly().train(original_train)
    legacy=f109.LearnedSourceRouting().train(original_train)
    need(learned.updates==blind.steps==legacy.steps==100 and
         learned.parameters<=cfg["Wingless"]["max_trainable_parameters"],
         "UNFAIR_WING_MODEL_BUDGET")
    arms={
        "learned_relational_features":learned.predicts,
        "fixed_uniform_feature_weights":fixed_similarity,
        "full_metadata_exact_lookup":exact_lookup,
        "query_only_64":lambda p,v:original_query_only(p,v,blind),
        "legacy_modular_offset_64":lambda p,v:legacy_offset(p,v,legacy)}
    results=[]
    for i,cases in enumerate(groups):
        decisions=[]
        for p in cases:
            need(exact_lookup(p,p.positive_values) and
                 not exact_lookup(p,p.negative_values),
                 "MISSING_LABEL_CONTROL")
            res={name:bool(fn(p,p.positive_values) and
                           not fn(p,p.negative_values)) for name,fn in arms.items()}
            decisions.append(dict(seed=p.seed,paired_correct=res))
        correct={name:sum(row["paired_correct"][name] for row in decisions)
                 for name in arms}
        results.append(dict(cohort=i,paired_cases=48,
                            correct_pairs_by_arm=correct,individual_cases=decisions))
    allrows=[v for grp in results for v in grp["individual_cases"]]
    wins=sum(r["paired_correct"]["learned_relational_features"] and
             not r["paired_correct"]["fixed_uniform_feature_weights"]
             for r in allrows)
    losses=sum(r["paired_correct"]["fixed_uniform_feature_weights"] and
               not r["paired_correct"]["learned_relational_features"]
               for r in allrows)
    threshold=cfg["Wingless"]["screen"]
    ok=all(grp["correct_pairs_by_arm"]["learned_relational_features"]/48>=
           threshold["minimum_each_block_paired_accuracy"]
           for grp in results) and wins-losses>=threshold[
           "minimum_pooled_net_paired_wins_over_fixed_similarity"]
    exact=sum(grp["correct_pairs_by_arm"]["full_metadata_exact_lookup"]
              for grp in results)
    # Never report a superiority claim over a full-information perfect arm.
    ok=ok and sum(grp["correct_pairs_by_arm"]["learned_relational_features"]
                  for grp in results)>exact
    return dict(lane="Wingless",model_parameters=learned.parameters,
        learned_training_updates=learned.updates,original_train_pairs=96,
        new_diagnostic_pairs=144,blocks=results,
        learned_only_pairs_vs_fixed=wins,fixed_only_pairs_vs_learned=losses,
        net_paired_gain_vs_fixed=wins-losses,
        exact_public_lookup_paired_correct=exact,
        no_superiority_over_exact_metadata_lookup=(exact>=sum(
           grp["correct_pairs_by_arm"]["learned_relational_features"] for grp in results)),
        learned_generalization_screen_passed=ok,
        disposition=("PUBLIC_BOUNDED_RELATION_METRIC_GAIN_NOT_SCIENCE" if ok
                     else "NO_GAIN_OVER_STRONG_PUBLIC_INFORMATION_CONTROLS_NEGATIVE_RETAINED"),
        candidate_is_engineered_feature_metric_not_unrestricted_representation_learning=True)

def graph_case(seed,group):
    rng=random.Random(seed*131+group*101+112)
    role_seq=tuple(rng.randrange(4) for _ in range(4))
    target=20
    edges=[]
    roles=[]
    vars_=[]
    def pick():return rng.randrange(16)
    for branch in range(3):
        nodes=(0,1+branch*3,2+branch*3,3+branch*3,target)
        ed=list(zip(nodes[:-1],nodes[1:]))
        a,b,c,d,e=[pick() for _ in range(5)]
        v=[(a,b),(b,c),(c,d),(d,e)]
        if branch:
            # Incorrect branch has 1-3 non-unifying transitions, frozen
            # by prospective group. Roles remain identical to main path.
            locations=[1,2,3][:group+1]
            for j in locations:
                lhs,rhs=v[j]
                v[j]=((v[j-1][1]+1+((seed+branch+j)%15))%16,rhs)
        edges+=ed;roles+=role_seq;vars_+=v
    negative=list(vars_)
    idx=1+(seed%3)
    lhs,rhs=negative[idx]
    negative[idx]=((vars_[idx-1][1]+1+seed%15)%16,rhs)
    order=list(range(12));rng.shuffle(order)
    p=ybind.Pair(seed,group,0,
        tuple(edges[k] for k in order),tuple(roles[k] for k in order),
        tuple(vars_[k] for k in order),
        tuple(negative[k] for k in order),
        role_seq,0,target,idx-1)
    need(len(p.edges)==12 and len(set(p.edges))==12 and
         sum(a!=b for v1,v2 in zip(p.positive_variables,p.negative_variables)
             for a,b in zip(v1,v2))==1 and
         ybind.coded_exact_binding_oracle(p,p.positive_variables) and
         not ybind.coded_exact_binding_oracle(p,p.negative_variables),
         "INVALID_BRANCH_COLLISION_TRUTH")
    return p
def graph_groups():
    groups=tuple(tuple(graph_case(seed,i) for seed in range(lo,hi+1))
        for i,(lo,hi) in enumerate(((68400,68447),(68500,68547),(68600,68647))))
    need(all(len(g)==48 for g in groups) and
         len({p.seed for group in groups for p in group})==144,
         "GRAPH_COHORT_REPLAY")
    return groups

def ygg_assessment(cfg):
    old=ybind.public_cohorts()
    trained=ybind.LearnedVariableBinder().fit(old[0]+old[1])
    blind=ybind.LearnedVariableBinder(blind=True).fit(old[0]+old[1])
    need(trained.training_updates==blind.training_updates==100,
         "CHANGED_PARENT_FIT")
    arms={
        "soft_slot_parent20":trained.predicts,
        "hard_slot_same_learned_role20":lambda p,v:f109.strict_slot_predict(trained,p,v),
        "variable_blind20":blind.predicts,
        "exact_coded_oracle_separate":ybind.coded_exact_binding_oracle}
    results=[]
    for i,cohort in enumerate(graph_groups()):
        pairs=[]
        for p in cohort:
            need(ybind.coded_exact_binding_oracle(p,p.positive_variables) and
                 not ybind.coded_exact_binding_oracle(p,p.negative_variables),
                 "CONTROL_SOURCE_FAILURE")
            each={name:bool(fn(p,p.positive_variables) and
                            not fn(p,p.negative_variables)) for name,fn in arms.items()}
            pairs.append(dict(seed=p.seed,paired_correct=each))
        score={key:sum(x["paired_correct"][key] for x in pairs) for key in arms}
        need(score["exact_coded_oracle_separate"]==48,"GROUND_TRUTH_CONTROL_NOT_PERFECT")
        results.append(dict(cohort=i,paired_cases=48,correct_pairs_by_arm=score,
                            individual_cases=pairs))
    rows=[x for grp in results for x in grp["individual_cases"]]
    c_only=sum(x["paired_correct"]["hard_slot_same_learned_role20"] and
               not x["paired_correct"]["soft_slot_parent20"] for x in rows)
    p_only=sum(x["paired_correct"]["soft_slot_parent20"] and
               not x["paired_correct"]["hard_slot_same_learned_role20"] for x in rows)
    gain=c_only-p_only
    return dict(lane="Yggdrasil",new_diagnostic_pairs=144,
        parent_fit_updates=100,shared_learned_parameters=20,
        graph_edges_each=12,blocks=results,hard_only_correct=c_only,
        soft_only_correct=p_only,net_hard_advantage=gain,
        improvement_screen_passed=(gain>=cfg["Yggdrasil"]["screen_min_net_strict_only_advantage"]),
        disposition=("PUBLIC_BRANCH_COLLISION_STRUCTURAL_GAIN_NOT_SCIENCE" if
                     gain>=cfg["Yggdrasil"]["screen_min_net_strict_only_advantage"] else
                     "NO_DEMONSTRATED_NEW_VARIABLE_REASONING_GAIN_NEGATIVE_RETAINED"))

def evaluate(source,root):
    need(type(source) is str and SHA40.fullmatch(source) is not None and
         (not os.environ.get("GITHUB_SHA") or os.environ["GITHUB_SHA"]==source),
         "HOSTED_SOURCE_DRIFT")
    cfg,digest=freeze()
    parent=prior_evidence(source,root,cfg)
    wing=wing_assessment(cfg)
    ygg=ygg_assessment(cfg)
    return dict(schema=REPORT,source_sha=source,
        freeze_sha256=digest,parent_F111_sha256=parent,
        evidence_class="FROZEN_PUBLIC_DEVELOPMENT_DIAGNOSTIC_NO_INDEPENDENT_SCIENCE",
        new_diagnostic_pairs_per_lane=144,
        intact_prior_negative_evidence=True,
        lanes=[wing,ygg],all_288_paired_records_preserved=True,
        independent_scientific_originals=0,science_accepted=0,
        protected_first_use_authorized=False,optimizer_promotions=0,
        accepted_ref_mutations=0,native_science_dispatches=0,
        codex_calls=0,paid_model_api_calls=0,work_tasks=0,
        ckb_plane_contact=False,cloudflare_writes=0,new_schedulers=0)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--source-ref",required=True)
    ap.add_argument("--evidence-root",required=True)
    args=ap.parse_args()
    print(json.dumps(evaluate(args.source_ref,args.evidence_root),
                     sort_keys=True,separators=(",",":")))

if __name__=="__main__":
    try:main()
    except (Quarantined,f111.Quarantined,f110.Quarantined,f109.Quarantined,
            ybind.Rejected,f110.wobserve.Rejected,ValueError,KeyError,TypeError,
            OSError) as e:
        print("FORGE_F112_FROZEN_RELATIONAL_TRANSFER=QUARANTINED "+str(e),
              file=sys.stderr)
        raise SystemExit(1)
