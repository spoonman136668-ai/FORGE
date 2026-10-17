"""F103 public-development learned variable-slot binding. NOT protected science.

Learns soft role and slot compatibility from frozen public counterfactuals.
The exact graph-binding oracle is only for labels and a coded control; neither
candidate probability nor parameter fitting calls that oracle.
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
FREEZE=ROOT/"reference/research-intake/f103-yggdrasil-variable-binding-freeze.json"
F102=ROOT/"reference/research-intake/f102-yggdrasil-role-dev-freeze.json"
F100=ROOT/"reference/research-intake/f100-frozen-successor-contract.json"
SCHEMA="forge.autonomy.f103.yggdrasil-public-dev-variable-binding-freeze.v1"
REPORT="forge.autonomy.f103.yggdrasil-public-dev-learned-variable-binding.v1"
FREEZE_BLOB="f22fec961818275834bdd07188ca8441f14d55ec"
F102_BLOB="8ac6290275bf59adeec51fe69c53b337db85fc6c"
F100_BLOB="79718d11be36ac4742774cf3ab3d502ef2feab59"
PARENT="6f9a64ae9cd9b7631f6296268e98120b7f4cafb2"
BLOCKS=((63500,63515),(63532,63547),(63564,63579))

class Rejected(ValueError): pass
def need(condition,reason):
    if not condition: raise Rejected("F103_"+reason)
def gitblob(raw):
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
def canonical_raw(path):
    return path.read_bytes().replace(b"\r\n",b"\n")

def frozen():
    raw=canonical_raw(FREEZE)
    need(len(raw)<48000 and gitblob(raw)==FREEZE_BLOB,"PREREGISTERED_CONTRACT_DRIFT")
    need(gitblob(canonical_raw(F102))==F102_BLOB and
         gitblob(canonical_raw(F100))==F100_BLOB,"ANCESTOR_CONTENT_DRIFT")
    f=json.loads(raw)
    need(f.get("schema")==SCHEMA and f.get("lane")=="Yggdrasil" and
         f.get("candidate_id")=="Y100-C2" and
         f.get("parent_f102_head_sha")==PARENT and
         f.get("parent_f102_contract_blob_sha")==F102_BLOB and
         f.get("parent_f100_contract_blob_sha")==F100_BLOB and
         f.get("parent_f99_negative_blob_sha")=="a280814e324d80bcc2590bbab939446180683e45",
         "LINEAGE_OR_CANDIDATE_DRIFT")
    m=f.get("trainable_candidate",{})
    need(m.get("max_slots")==16 and m.get("role_vocab_size")==4 and
         m.get("path_hops")==4 and m.get("node_budget")==21 and
         m.get("edge_budget")==12 and m.get("maximum_trainable_parameters")==128 and
         m.get("maximum_optimizer_steps")==100 and m.get("learning_rate")==0.2 and
         m.get("initialization_seed")==103 and m.get("candidate_must_not_call_coded_oracle") is True and
         m.get("no_explicit_label_or_binding_truth_feature") is True,
         "TRAINING_OR_MODEL_BUDGET_DRIFT")
    d=f.get("public_development",{})
    need(d.get("seed_blocks")==[list(x) for x in BLOCKS] and
         d.get("case_instances_per_seed")==3 and d.get("train_blocks")==[0,1] and
         d.get("assessment_block")==2 and
         d.get("train_counterfactual_pairs")==96 and
         d.get("assessment_counterfactual_pairs")==48 and
         d.get("total_counterfactual_pairs")==144 and
         d.get("positive_negative_labels")==[True,False] and
         d.get("graph_edges_identical_within_pair") is True and
         d.get("typed_edge_roles_identical_within_pair") is True and
         d.get("exactly_one_changed_variable_argument") is True and
         d.get("old_y_f9_seeds_reused") is False and
         d.get("f102_seed_blocks_reused") is False and
         d.get("protected_first_use_consumed")==0,
         "DATASET_OR_GROUND_TRUTH_DRIFT")
    need(f.get("controls")==[
        "historical_frozen_Y_F9_negative_reference_only",
        "independently_trained_size_matched_role_aware_variable_blind",
        "randomized_variable_slot_labels_without_consistent_renaming",
        "always_yes_shortcut",
        "coded_exact_typed_binding_oracle_control_only"],"CONTROL_REMOVED")
    need(f.get("metrics",{}).get("screen_only_thresholds")=={
        "minimum_paired_accuracy":0.75,
        "minimum_improvement_vs_variable_blind":0.15,
        "minimum_worst_group_accuracy":0.6,
        "minimum_variable_renaming_agreement":0.95},
        "POST_RESULT_RETUNED_THRESHOLDS")
    guards=f.get("guards",{})
    for guard in ("preregistration_must_precede_implementation","all_arms_and_controls_reported",
                  "negative_findings_preserved","no_post_assessment_threshold_or_model_tuning",
                  "no_secret_original_seeds","no_protected_first_use",
                  "no_accepted_ref_mutations","no_codex","no_paid_external_model_api",
                  "no_chatgpt_work_tasks","no_ckb_plane_integration",
                  "no_additional_scheduler_or_controller","no_cloudflare_write",
                  "no_wingless_or_yggdrasil_repository_edit","no_optimizer_promotion",
                  "no_new_original_science","no_autonomous_gpt_inference_claim"):
        need(guards.get(guard) is True,"DISALLOWED_"+guard.upper())
    return f,hashlib.sha256(raw).hexdigest()

@dataclass(frozen=True)
class Pair:
    seed:int
    block:int
    specimen:int
    edges:tuple
    roles:tuple
    positive_variables:tuple
    negative_variables:tuple
    query_roles:tuple
    source:int
    target:int
    conflict_site:int

def generate(seed,block,specimen):
    need(block in range(3) and specimen in range(3) and
         BLOCKS[block][0]<=seed<=BLOCKS[block][1] and
         seed not in range(51400,51448) and not 63400<=seed<=63479,
         "UNFROZEN_OR_HISTORICAL_SEED")
    rng=random.Random((seed<<10)+(block<<5)+specimen+103)
    nodes=list(range(1,21))
    rng.shuffle(nodes)
    main=(0,*nodes[:4])
    competing=(0,*nodes[4:7],main[-1])
    edges=list(zip(main[:-1],main[1:]))+list(zip(competing[:-1],competing[1:]))
    pool=nodes[7:]
    edges.extend((pool[i],pool[i+1]) for i in range(0,8,2))
    query=((seed+specimen)%4,rng.randrange(4),rng.randrange(4),rng.randrange(4))
    roles=(*query,*query,*(rng.randrange(4) for _ in range(4)))
    a,b,c=[rng.randrange(16) for _ in range(3)]
    x,y,z=[rng.randrange(16) for _ in range(3)]
    incompatible=(y+1+rng.randrange(15))%16
    main_vars=[(rng.randrange(16),a),(a,b),(b,c),(c,rng.randrange(16))]
    competitor_vars=[(rng.randrange(16),x),(x,y),(incompatible,z),(z,rng.randrange(16))]
    variables=main_vars+competitor_vars+[
        (rng.randrange(16),rng.randrange(16)) for _ in range(4)]
    negative=[list(v) for v in variables]
    conflict=(seed+specimen)%3
    negative[conflict+1][0]=(variables[conflict][1]+1+rng.randrange(15))%16
    order=list(range(12))
    rng.shuffle(order)
    p=Pair(seed,block,specimen,tuple(edges[i] for i in order),
           tuple(roles[i] for i in order),
           tuple(variables[i] for i in order),
           tuple(tuple(negative[i]) for i in order),tuple(query),
           0,main[-1],conflict)
    need(len(p.edges)==len(set(p.edges))==12 and
         sum(a!=b for x,y in zip(p.positive_variables,p.negative_variables)
             for a,b in zip(x,y))==1 and
         len(p.query_roles)==4 and len(set(v for pair in p.edges for v in pair))<=21,
         "MALFORMED_PAIRED_BINDING_CASE")
    return p

def coded_exact_binding_oracle(p,variables):
    """Independent strong-control truth only. Never used in candidate or fitting."""
    reached={(p.source,None)}
    for hop,query_role in enumerate(p.query_roles):
        nxt=set()
        for (u,v),role,(lhs,rhs) in zip(p.edges,p.roles,variables):
            if role!=query_role: continue
            for node,old_rhs in reached:
                if node==u and (hop==0 or old_rhs==lhs):
                    nxt.add((v,rhs))
        reached=nxt
    return any(node==p.target for node,token in reached)

def public_cohorts():
    groups=[]
    seen=set()
    for block,(lo,hi) in enumerate(BLOCKS):
        cases=[]
        for seed in range(lo,hi+1):
            for instance in range(3):
                p=generate(seed,block,instance)
                need((seed,instance) not in seen,"CASE_REPLAY")
                seen.add((seed,instance))
                need(coded_exact_binding_oracle(p,p.positive_variables) and
                     not coded_exact_binding_oracle(p,p.negative_variables),
                     "GROUND_TRUTH_NOT_COUNTERFACTUAL")
                cases.append(p)
        need(len(cases)==48,"COHORT_SIZE_DRIFT")
        groups.append(tuple(cases))
    return tuple(groups)

def sigmoid(value):
    return 1/(1+math.exp(-max(-32.,min(32.,value))))

def slot_overlap(one,other):
    """Dot product over canonical one-hot slot vectors, invariant to alpha-renaming."""
    return sum((1 if k==one else 0)*(1 if k==other else 0) for k in range(16))

class LearnedVariableBinder:
    """20 learned scalars: 16 role gates + 2 soft slot gates + 2 readout."""
    parameter_count=20
    def __init__(self,blind=False):
        self.role=[2.0 if i//4==i%4 else -1.5 for i in range(16)]
        self.slot=[0.0,0.0]
        self.scale=16.0
        self.bias=-0.8
        self.blind=blind
        self.training_updates=0
    def probability(self,p,variables):
        need(len(p.edges)==len(p.roles)==len(variables)==12,
             "UNBOUNDED_OR_MISSING_VARIABLE_EDGES")
        state={(p.source,-1):(1.0,[0.0]*18)}
        for hop,query_role in enumerate(p.query_roles):
            next_state={}
            for (u,v),role,(lhs,rhs) in zip(p.edges,p.roles,variables):
                index=query_role*4+role
                role_gate=sigmoid(self.role[index])
                for (node,previous_slot),(mass,derivative) in state.items():
                    if node!=u: continue
                    if hop==0 or self.blind:
                        binding_gate=1.0
                        binding_index=None
                    else:
                        overlap=slot_overlap(previous_slot,lhs)
                        binding_index=1 if overlap==1 else 0
                        binding_gate=sigmoid(self.slot[binding_index])
                    gate=role_gate*binding_gate
                    state_key=(v,rhs if not self.blind else -1)
                    accumulated,grad=next_state.get(state_key,(0.0,[0.0]*18))
                    accumulated+=mass*gate
                    grad=[g+delta*gate for g,delta in zip(grad,derivative)]
                    grad[index]+=mass*binding_gate*role_gate*(1-role_gate)
                    if binding_index is not None:
                        grad[16+binding_index]+=mass*role_gate*binding_gate*(1-binding_gate)
                    next_state[state_key]=(accumulated,grad)
            state=next_state
        target_mass=sum(value[0] for key,value in state.items() if key[0]==p.target)
        target_grad=[sum(value[1][j] for key,value in state.items() if key[0]==p.target)
                     for j in range(18)]
        return sigmoid(self.scale*target_mass+self.bias),target_mass,target_grad
    def fit(self,cases,steps=100):
        items=tuple(cases)
        need(len(items)==96 and steps==100 and self.training_updates==0,
             "INVALID_TRAINING_BUDGET_OR_RETRAIN_ATTEMPT")
        for _ in range(steps):
            gradients=[0.0]*18
            ds=db=0.0
            for p in items:
                for variables,label in ((p.positive_variables,1),(p.negative_variables,0)):
                    probability,mass,gradient=self.probability(p,variables)
                    error=probability-label
                    for k in range(18):
                        gradients[k]+=error*self.scale*gradient[k]
                    ds+=error*mass
                    db+=error
            step=0.2/(2*len(items))
            self.role=[max(-8.0,min(8.0,w-step*g))
                       for w,g in zip(self.role,gradients[:16])]
            self.slot=[max(-8.0,min(8.0,w-step*g))
                       for w,g in zip(self.slot,gradients[16:])]
            self.scale=max(0.1,min(40.0,self.scale-step*ds))
            self.bias=max(-8.0,min(8.0,self.bias-step*db))
            self.training_updates+=1
        return self
    def predicts(self,p,variables):
        return self.probability(p,variables)[0]>=0.5

def paired_accuracy(cases,predict):
    cases=tuple(cases)
    need(bool(cases),"EMPTY_EVALUATION")
    return sum(predict(p,p.positive_variables) and
               not predict(p,p.negative_variables) for p in cases)/len(cases)

def remap_variables(p):
    mapping=list(range(16))
    random.Random((p.seed<<4)+p.specimen+103).shuffle(mapping)
    rename=lambda variables:tuple((mapping[lhs],mapping[rhs])
                                  for lhs,rhs in variables)
    return Pair(p.seed,p.block,p.specimen,p.edges,p.roles,
                rename(p.positive_variables),rename(p.negative_variables),
                p.query_roles,p.source,p.target,p.conflict_site)

def remap_nodes(p):
    ids=sorted({p.source,p.target}|{n for edge in p.edges for n in edge})
    mapping={n:101+3*i for i,n in enumerate(reversed(ids))}
    return Pair(p.seed,p.block,p.specimen,
                tuple((mapping[u],mapping[v]) for u,v in p.edges),
                p.roles,p.positive_variables,p.negative_variables,
                p.query_roles,mapping[p.source],mapping[p.target],p.conflict_site)

def independent_edge_slot_disruption(p,variables):
    """Ablation destroys shared slot names across edges, not coherent renaming."""
    masks=[(i*5+p.seed+p.specimen)%16 for i in range(12)]
    return tuple(((lhs+masks[i])%16,(rhs+masks[i]+7)%16)
                 for i,(lhs,rhs) in enumerate(variables))

def evaluate(source_sha):
    need(isinstance(source_sha,str) and re.fullmatch(r"[0-9a-f]{40}",source_sha) and
         (not os.environ.get("GITHUB_SHA") or os.environ["GITHUB_SHA"]==source_sha),
         "EXACT_SOURCE_REF_REQUIRED")
    config,sha256=frozen()
    groups=public_cohorts()
    training=groups[0]+groups[1]
    assessment=groups[2]
    learner=LearnedVariableBinder().fit(training)
    blind=LearnedVariableBinder(blind=True).fit(training)
    scores={
        "learned_variable_slot_binder":paired_accuracy(assessment,learner.predicts),
        "size_matched_role_aware_variable_blind":paired_accuracy(assessment,blind.predicts),
        "independent_slot_disruption_ablation":paired_accuracy(
            assessment,lambda p,v:learner.predicts(
                p,independent_edge_slot_disruption(p,v))),
        "always_yes_shortcut":paired_accuracy(assessment,lambda p,v:True),
        "coded_exact_binding_oracle":paired_accuracy(assessment,coded_exact_binding_oracle),
    }
    family={}
    for role in range(4):
        cases=[p for p in assessment if p.query_roles[0]==role]
        need(bool(cases),"MISSING_ROLE_FAMILY")
        family[str(role)]=paired_accuracy(cases,learner.predicts)
    conflict={}
    for site in range(3):
        cases=[p for p in assessment if p.conflict_site==site]
        need(bool(cases),"MISSING_CONFLICT_SITE")
        conflict[str(site)]=paired_accuracy(cases,learner.predicts)
    rename=sum(learner.predicts(p,v)==learner.predicts(remap_variables(p),x)
               for p in assessment
               for v,x in ((p.positive_variables,remap_variables(p).positive_variables),
                           (p.negative_variables,remap_variables(p).negative_variables)))/(2*len(assessment))
    node_rename=sum(learner.predicts(p,v)==learner.predicts(remap_nodes(p),v)
                    for p in assessment
                    for v in (p.positive_variables,p.negative_variables))/(2*len(assessment))
    worst=min(*family.values(),*conflict.values())
    thresholds=config["metrics"]["screen_only_thresholds"]
    passed=(scores["learned_variable_slot_binder"]>=thresholds["minimum_paired_accuracy"]
            and scores["learned_variable_slot_binder"]-
            scores["size_matched_role_aware_variable_blind"]>=
            thresholds["minimum_improvement_vs_variable_blind"]
            and worst>=thresholds["minimum_worst_group_accuracy"]
            and rename>=thresholds["minimum_variable_renaming_agreement"])
    return dict(schema=REPORT,source_sha=source_sha,lane="Yggdrasil",
                candidate_id="Y100-C2",frozen_contract_sha256=sha256,
                evidence_class="RESTRICTED_PUBLIC_DEVELOPMENT_NO_PROTECTED_FIRST_USE",
                training_pairs=len(training),assessment_pairs=len(assessment),
                total_development_pairs=144,trainable_parameters=learner.parameter_count,
                learned_training_updates=learner.training_updates,
                variable_blind_training_updates=blind.training_updates,
                paired_public_dev_accuracy=scores,worst_group_accuracy=worst,
                role_family_accuracy=family,conflict_site_accuracy=conflict,
                variable_renaming_agreement=rename,node_renaming_agreement=node_rename,
                incompatible_binding_false_positive_rate=sum(
                    learner.predicts(p,p.negative_variables) for p in assessment)/len(assessment),
                public_development_screen_passed=passed,
                historical_Y_F9_negative_0_of_192_preserved=True,
                oracle_only_separate_control=True,
                first_use_authorized=False,scientific_originals_executed=0,
                independent_scientific_results_accepted=0,optimizer_promotion_authorized=False,
                accepted_ref_mutations=0,codex_invocations=0,paid_api_calls=0,
                chatgpt_work_tasks=0,ckb_plane_accessed=False)

def main():
    cli=argparse.ArgumentParser()
    cli.add_argument("--source-ref",required=True)
    args=cli.parse_args()
    print(json.dumps(evaluate(args.source_ref),sort_keys=True,separators=(",",":")))

if __name__=="__main__":
    try:main()
    except (Rejected,OSError,ValueError,TypeError,KeyError) as error:
        print("FORGE_F103_VARIABLE_BINDING=QUARANTINED "+str(error),file=sys.stderr)
        raise SystemExit(1)
