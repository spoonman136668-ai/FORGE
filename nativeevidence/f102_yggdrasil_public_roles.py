"""F102: authentic small learned typed-role message composition on PUBLIC DEV only.

The candidate fits 18 parameters by analytic gradients on counterfactual typed
paths. The exact typed-path oracle is used ONLY to validate generated labels and
as a separate coded control, never in the learned probability or fit routine.
The public toy graph construction is deliberately constrained and proves no
prospective scientific original, independent generalization or GPT inference.
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
FROZEN=ROOT/"reference/research-intake/f102-yggdrasil-role-dev-freeze.json"
F100=ROOT/"reference/research-intake/f100-frozen-successor-contract.json"
SCHEMA="forge.autonomy.f102.yggdrasil-public-dev-learned-typed-role-composition.v1"
REPORT="forge.autonomy.f102.yggdrasil-public-dev-real-learned-role-composer.v1"
PARENT_F101="c7080b5e53145840bf3f799cd481760f9918e404"
PARENT_F100="356955de3548a56eb916471c505ab36f4f232957"
F100_BLOB="79718d11be36ac4742774cf3ab3d502ef2feab59"
BLOCKS=((63400,63415),(63432,63447),(63464,63479))
class Rejected(ValueError):pass
def need(ok,reason):
    if not ok:raise Rejected("F102_"+reason)
def blob(data):
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\x00"+data).hexdigest()
def frozen():
    raw=FROZEN.read_bytes()
    need(len(raw)<48000,"FROZEN_OVERSIZED")
    f=json.loads(raw)
    f100=F100.read_bytes().replace(b"\r\n",b"\n")
    need(blob(f100)==F100_BLOB and
         f.get("schema")==SCHEMA and f.get("parent_f101_sha")==PARENT_F101 and
         f.get("parent_f100_sha")==PARENT_F100 and
         f.get("parent_f100_contract_git_blob_sha")==F100_BLOB and
         f.get("parent_f99_negative_git_blob_sha")=="a280814e324d80bcc2590bbab939446180683e45" and
         f.get("lane")=="Yggdrasil" and f.get("candidate_id")=="Y100-C1",
         "FROZEN_SOURCE_OR_LINEAGE_DRIFT")
    hist=f.get("frozen_historical_negative",{})
    need(hist.get("experiment")=="Y-F9" and hist.get("learned_paired_correct")==0 and
         hist.get("coded_role_oracle_correct")==192 and hist.get("pairs")==192 and
         hist.get("classification")=="HISTORICAL_DEVELOPMENT_NEGATIVE_NOT_ACCEPTED_ORIGINAL",
         "NEGATIVE_HISTORY_RELABELED")
    mech=f.get("learned_mechanism",{})
    need(mech.get("role_vocabulary")==4 and mech.get("query_role_sequence_length")==4 and
         mech.get("adjacency_budget")==12 and mech.get("node_budget")==21 and
         mech.get("learned_compatibility_parameters")==16 and mech.get("learned_readout_parameters")==2 and
         mech.get("total_trainable_parameters")==18 and
         mech.get("maximum_training_updates")==100 and mech.get("sgd_learning_rate")==0.4 and
         mech.get("inference_must_not_call_typed_role_oracle") is True,
         "LEARNED_MODEL_BUDGET_DRIFT")
    dev=f.get("public_development",{})
    need(dev.get("seed_blocks")==[list(x) for x in BLOCKS] and
         dev.get("cases_per_seed")==3 and
         dev.get("train_blocks")==[0,1] and dev.get("public_assessment_block")==2 and
         dev.get("train_pairs")==96 and dev.get("assessment_pairs")==48 and
         dev.get("total_pairs")==144 and
         dev.get("positive_negative_labels")==[True,False] and
         dev.get("counterfactual_role_swaps_per_pair")==1 and
         dev.get("untyped_edges_identical_across_pair") is True and
         dev.get("old_Y_F9_seeds_reused") is False and
         dev.get("protected_original_first_use_consumed")==0,"DEVELOPMENT_SEED_OR_DATA_DRIFT")
    controls=f.get("controls")
    need(controls==["frozen_role_blind_Y_F9_historical_reference_only",
                    "independently_trained_size_matched_role_blind",
                    "query_role_permutation_ablation","always_yes_shortcut",
                    "coded_exact_typed_role_oracle_control_only"],"MISSING_FULL_CONTROLS")
    metrics=f.get("metrics",{})
    need(metrics.get("screen_only_thresholds")=={
        "minimum_paired_accuracy":0.75,
        "minimum_improvement_vs_size_matched_roleblind":0.15,
        "minimum_worst_role_family_accuracy":0.60} and
        metrics.get("candidate_pass_is_not_scientific_acceptance") is True,
        "POST_RESULT_RETUNED_SCREEN")
    flags=f.get("guards",{})
    for key in ("preregistration_committed_before_executable_code",
                "all_arms_and_controls_must_be_reported","results_may_be_negative",
                "no_post_assessment_tuning","no_model_api_calls","no_codex",
                "no_work_scheduled_task","no_ckb_plane","no_accepted_ref_mutation",
                "no_optimizer_promotion","no_independent_scientific_result",
                "no_first_use_authorization"):
        need(flags.get(key) is True,"MISSING_"+key.upper())
    return f,hashlib.sha256(raw).hexdigest()

@dataclass(frozen=True)
class Pair:
    seed:int
    block:int
    specimen:int
    edges:tuple
    positive_roles:tuple
    negative_roles:tuple
    query_roles:tuple
    source:int
    target:int

def generate(seed,block,specimen):
    need(block in range(3) and specimen in range(3) and
         BLOCKS[block][0]<=seed<=BLOCKS[block][1] and
         seed not in range(51400,51448),"UNFROZEN_OR_ORIGINAL_SEED")
    rng=random.Random((seed<<8)+specimen*7+block)
    nodes=list(range(1,21))
    rng.shuffle(nodes)
    path=[0]+nodes[:4]
    edges=list(zip(path[:-1],path[1:]))
    isolated=nodes[4:]
    for i in range(8):
        if block==2 and i==0:
            edge=(0,isolated[0])
        else:
            a,b=isolated[(2*i)%len(isolated)],isolated[(2*i+1)%len(isolated)]
            edge=(b,a) if block==1 else (a,b)
        edges.append(edge)
    positive=[rng.randrange(4) for _ in range(12)]
    negative=positive.copy()
    changed_step=rng.randrange(4)
    negative[changed_step]=(positive[changed_step]+1+rng.randrange(3))%4
    order=list(range(12))
    rng.shuffle(order)
    case=Pair(seed,block,specimen,tuple(edges[i] for i in order),
              tuple(positive[i] for i in order),tuple(negative[i] for i in order),
              tuple(positive[:4]),0,path[-1])
    need(len(case.edges)==len(set(case.edges))==12 and
         sum(a!=b for a,b in zip(case.positive_roles,case.negative_roles))==1,
         "UNREGISTERED_COUNTERFACTUAL_GRAPH")
    return case

def coded_typed_role_oracle(case,roles):
    """Ground-truth and coded strong control ONLY; never part of learned model."""
    reached={case.source}
    for query_role in case.query_roles:
        nxt=set()
        for (u,v),r in zip(case.edges,roles):
            if u in reached and r==query_role:nxt.add(v)
        reached=nxt
    return case.target in reached

def public_groups():
    groups=[]
    seen=set()
    for block,(lo,hi) in enumerate(BLOCKS):
        entries=[]
        for seed in range(lo,hi+1):
            for specimen in range(3):
                p=generate(seed,block,specimen)
                identity=(p.seed,p.specimen)
                need(identity not in seen,"REPLAYED_DEVELOPMENT_CASE")
                seen.add(identity)
                need(coded_typed_role_oracle(p,p.positive_roles) and
                     not coded_typed_role_oracle(p,p.negative_roles),
                     "INCORRECT_FROZEN_ROLE_SWAP_GROUND_TRUTH")
                entries.append(p)
        need(len(entries)==48,"PUBLIC_BLOCK_SIZE_DRIFT")
        groups.append(tuple(entries))
    need(sum(map(len,groups))==144,"PUBLIC_COHORT_COUNT_DRIFT")
    return tuple(groups)

def sigmoid(value):
    if value>32:return 1-1e-14
    if value< -32:return 1e-14
    return 1/(1+math.exp(-value))

class LearnedRoleComposer:
    """Soft matching is a trainable 4x4 scalar gate, not an equality oracle."""
    def __init__(self,blind=False):
        self.compatibility=[0.02*((i*7)%5-2) for i in range(16)]
        self.readout_scale=8.0
        self.readout_bias=-0.5
        self.blind=blind
        self.training_updates=0
    def probability(self,case,roles):
        need(len(roles)==12,"INPUT_EDGE_ROLE_COUNT")
        state={case.source:1.0}
        grads={case.source:[0.0]*16}
        for query_role in case.query_roles:
            nxt={}
            derivatives={}
            for (u,v),relation in zip(case.edges,roles):
                if u not in state:continue
                idx=(0 if self.blind else query_role)*4+(0 if self.blind else relation)
                gate=sigmoid(self.compatibility[idx])
                nxt[v]=nxt.get(v,0.0)+state[u]*gate
                delta=derivatives.setdefault(v,[0.0]*16)
                previous=grads[u]
                for k in range(16):
                    delta[k]+=previous[k]*gate
                delta[idx]+=state[u]*gate*(1-gate)
            state=nxt
            grads=derivatives
        mass=state.get(case.target,0.0)
        derivative=grads.get(case.target,[0.0]*16)
        return sigmoid(self.readout_scale*mass+self.readout_bias),mass,derivative
    def fit(self,cases,steps=100):
        inputs=tuple(cases)
        need(len(inputs)==96 and steps==100 and self.training_updates==0,
             "LEARNED_MODEL_TRAINING_BUDGET_OR_REPLAY")
        for _ in range(steps):
            dc=[0.0]*16
            ds=db=0.0
            for case in inputs:
                for roles,label in ((case.positive_roles,1),(case.negative_roles,0)):
                    prob,mass,derivative=self.probability(case,roles)
                    error=prob-label
                    for i in range(16):
                        dc[i]+=error*self.readout_scale*derivative[i]
                    ds+=error*mass
                    db+=error
            step=0.4/(len(inputs)*2)
            self.compatibility=[
                max(-9.0,min(9.0,weight-step*change))
                for weight,change in zip(self.compatibility,dc)]
            self.readout_scale=max(0.1,min(30.0,self.readout_scale-step*ds))
            self.readout_bias=max(-8.0,min(8.0,self.readout_bias-step*db))
            self.training_updates+=1
        return self
    def predicts(self,case,roles):
        return self.probability(case,roles)[0]>=0.5

def paired_accuracy(cases,predict):
    cohort=tuple(cases)
    need(bool(cohort),"EMPTY_PUBLIC_ASSESSMENT")
    return sum(predict(p,p.positive_roles) and not predict(p,p.negative_roles)
               for p in cohort)/len(cohort)
def remap_nodes(case):
    """Independent node-renaming invariance control, not used for fitting."""
    ids=sorted({case.source,case.target}|
               {n for edge in case.edges for n in edge})
    mapping={n:i*3+101 for i,n in enumerate(reversed(ids))}
    return Pair(case.seed,case.block,case.specimen,
                tuple((mapping[u],mapping[v]) for u,v in case.edges),
                case.positive_roles,case.negative_roles,case.query_roles,
                mapping[case.source],mapping[case.target])

def evaluate(source_sha):
    need(type(source_sha) is str and re.fullmatch(r"[0-9a-f]{40}",source_sha) is not None and
         (not os.environ.get("GITHUB_SHA") or os.environ["GITHUB_SHA"]==source_sha),
         "FORGE_SOURCE_REF_MISMATCH")
    cfg,digest=frozen()
    groups=public_groups()
    train=groups[0]+groups[1]
    diagnostic=groups[2]
    learner=LearnedRoleComposer().fit(train)
    blind=LearnedRoleComposer(blind=True).fit(train)
    scores={
        "learned_typed_role_composer":paired_accuracy(diagnostic,learner.predicts),
        "size_matched_role_blind":paired_accuracy(diagnostic,blind.predicts),
        "query_role_permuted_ablation":paired_accuracy(
            diagnostic,lambda p,r:learner.predicts(
                Pair(p.seed,p.block,p.specimen,p.edges,p.positive_roles,
                     p.negative_roles,tuple((x+1)%4 for x in p.query_roles),
                     p.source,p.target),r)),
        "always_yes_shortcut":paired_accuracy(diagnostic,lambda p,r:True),
        "coded_typed_role_oracle":paired_accuracy(diagnostic,coded_typed_role_oracle),
    }
    family_scores={}
    for role in range(4):
        subset=[p for p in diagnostic if p.query_roles[0]==role]
        need(bool(subset),"MISSING_PUBLIC_ROLE_FAMILY")
        family_scores[str(role)]=paired_accuracy(subset,learner.predicts)
    min_role=min(family_scores.values())
    min_group=min(paired_accuracy(block,learner.predicts) for block in groups)
    rename=sum(learner.predicts(p,roles)==learner.predicts(remap_nodes(p),roles)
               for p in diagnostic for roles in (p.positive_roles,p.negative_roles))/(len(diagnostic)*2)
    neg_false_positive=sum(learner.predicts(p,p.negative_roles) for p in diagnostic)/len(diagnostic)
    targets=cfg["metrics"]["screen_only_thresholds"]
    passed=(scores["learned_typed_role_composer"]>=targets["minimum_paired_accuracy"] and
            scores["learned_typed_role_composer"]-scores["size_matched_role_blind"]>=
            targets["minimum_improvement_vs_size_matched_roleblind"] and
            min_role>=targets["minimum_worst_role_family_accuracy"] and
            min_group>=targets["minimum_worst_role_family_accuracy"])
    return dict(
        schema=REPORT,source_sha=source_sha,lane="Yggdrasil",candidate_id="Y100-C1",
        frozen_protocol_sha256=digest,
        evidence_class="BOUNDED_PUBLIC_SYNTHETIC_DEVELOPMENT_NOT_INDEPENDENT_SCIENCE",
        total_public_development_pairs=144,training_pairs=96,
        public_development_assessment_pairs=48,
        trainable_parameters=18,learned_training_updates=learner.training_updates,
        blind_control_training_updates=blind.training_updates,
        paired_public_dev_accuracy=scores,worst_role_family_accuracy=min_role,
        worst_public_graph_group_accuracy=min_group,
        role_family_accuracies=family_scores,node_renaming_prediction_agreement=rename,
        negative_role_swap_false_positive_rate=neg_false_positive,
        public_development_screen_passed=passed,
        historical_Y_F9_zero_of_192_negative_preserved=True,
        coded_oracle_only_control=True,
        scientific_originals_executed=0,independent_scientific_results_accepted=0,
        first_use_authorized=False,optimizer_promotion_authorized=False,
        accepted_ref_mutations=0,codex_invocations=0,external_model_api_calls=0,
        chatgpt_work_tasks=0,ckb_plane_accessed=False)
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source-ref",required=True)
    args=p.parse_args()
    print(json.dumps(evaluate(args.source_ref),sort_keys=True,separators=(",",":")))
if __name__=="__main__":
    try:main()
    except (Rejected,OSError,KeyError,TypeError,ValueError) as exc:
        print("FORGE_F102_LEARNED_TYPED_ROLE_DEV=QUARANTINED "+str(exc),file=sys.stderr)
        raise SystemExit(1)
