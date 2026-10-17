"""F104: learned one-observation query-conditioned Wingless selector (PUBLIC DEV only).

This is a real trainable soft attention model with discrete one-slot inference,
not a coded depth oracle and not independently qualified Wingless science.
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
from dataclasses import dataclass, replace

ROOT=pathlib.Path(__file__).resolve().parents[1]
FREEZE=ROOT/"reference/research-intake/f104-wingless-observation-selection-freeze.json"
F103=ROOT/"reference/research-intake/f103-yggdrasil-variable-binding-freeze.json"
F101=ROOT/"reference/research-intake/f101-wingless-development-freeze.json"
F100=ROOT/"reference/research-intake/f100-frozen-successor-contract.json"
FREEZE_BLOB="c68143be42cea74f763cc430b4af3db80785012b"
F103_BLOB="f22fec961818275834bdd07188ca8441f14d55ec"
F101_BLOB="b4d6670b40865d8924a50aada619596c056e170b"
F100_BLOB="79718d11be36ac4742774cf3ab3d502ef2feab59"
PARENT="c0f205ceb8440f10f9b9179f0518abd900e6356e"
SCHEMA="forge.autonomy.f104.wingless-public-dev-observation-selection-freeze.v1"
REPORT="forge.autonomy.f104.wingless-public-dev-learned-observation-selector.v1"
BLOCKS=((63700,63715),(63732,63747),(63764,63779))

class Rejected(ValueError): pass
def need(ok, why):
    if not ok: raise Rejected("F104_"+why)
def sha_blob(raw):
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\x00"+raw).hexdigest()
def stable_bytes(p):
    return p.read_bytes().replace(b"\r\n",b"\n")

def frozen():
    raw=stable_bytes(FREEZE)
    need(len(raw)<48000 and sha_blob(raw)==FREEZE_BLOB,
         "FROZEN_PREREGISTRATION_DRIFT")
    need(sha_blob(stable_bytes(F103))==F103_BLOB and
         sha_blob(stable_bytes(F101))==F101_BLOB and
         sha_blob(stable_bytes(F100))==F100_BLOB,
         "ANCESTRY_CONTENT_DRIFT")
    f=json.loads(raw)
    need(f.get("schema")==SCHEMA and f.get("lane")=="Wingless" and
         f.get("candidate_id")=="W100-C2" and
         f.get("parent_f103_head_sha")==PARENT and
         f.get("parent_f103_contract_git_blob_sha")==F103_BLOB and
         f.get("parent_f101_wingless_contract_git_blob_sha")==F101_BLOB and
         f.get("parent_f100_contract_git_blob_sha")==F100_BLOB and
         f.get("parent_f99_negative_git_blob_sha")=="a280814e324d80bcc2590bbab939446180683e45",
         "PARENT_OR_CANDIDATE_DRIFT")
    m=f.get("mechanism",{})
    need(m.get("depth_vocab_size")==4 and
         m.get("observation_slots")==4 and
         m.get("observation_budget_per_prediction")==1 and
         m.get("trainable_attention_parameters")==16 and
         m.get("trainable_readout_parameters")==2 and
         m.get("total_trainable_parameters")==18 and
         m.get("maximum_training_updates")==100 and
         m.get("learning_rate")==4.0 and
         m.get("no_oracle_or_ground_truth_label_access_in_prediction") is True and
         m.get("no_programmed_depth_equality_selector") is True and
         m.get("no_oracle_used_for_gradient") is True,
         "MODEL_OR_TRAINING_BUDGET_DRIFT")
    d=f.get("cohort",{})
    need(d.get("public_seed_blocks")==[list(b) for b in BLOCKS] and
         d.get("cases_per_seed")==3 and d.get("train_blocks")==[0,1] and
         d.get("public_assessment_block")==2 and
         d.get("training_counterfactual_pairs")==96 and
         d.get("assessment_counterfactual_pairs")==48 and
         d.get("total_pairs")==144 and
         d.get("pair_labels")==[True,False] and
         d.get("same_untyped_graph_observation_tags_within_pair") is True and
         d.get("nonrequested_depth_evidence_shared_within_pair") is True and
         d.get("all_four_distinct_depth_tags_available_in_each_case") is True and
         d.get("prior_W_F10_seeds_reused") is False and
         d.get("prior_F101_seeds_reused") is False and
         d.get("prospective_first_use_consumed")==0,
         "FROZEN_COHORT_DRIFT")
    need(f.get("controls")==[
        "frozen_historical_W_F10_negative_reference_only",
        "independently_trained_same_capacity_depth_blind_selector",
        "query_depth_permutation_ablation",
        "fixed_first_observation_shortcut",
        "always_yes_shortcut",
        "coded_requested_depth_observation_oracle_control_only"],
         "MISSING_CONTROL")
    need(f.get("metrics",{}).get("screen_only_thresholds")=={
        "minimum_paired_accuracy":0.75,
        "minimum_improvement_vs_depth_blind":0.15,
        "minimum_worst_depth_accuracy":0.6,
        "minimum_changed_selection_fraction":0.5
    },"POST_RESULT_SCREEN_DRIFT")
    guards=f.get("guards",{})
    for key in ("freeze_first_commit_before_model_implementation",
                "report_all_arms_including_negative",
                "no_post_assessment_tuning",
                "no_protected_scientific_original","no_science_first_use",
                "no_accepted_ref_mutation","no_optimizer_promotion",
                "no_codex","no_paid_external_model_api","no_chatgpt_work_tasks",
                "no_ckb_plane_integration","no_new_scheduler",
                "no_cloudflare_change","no_wingless_or_yggdrasil_repository_mutations",
                "no_gpt_unattended_inference_claim"):
        need(guards.get(key) is True,"AUTHORITY_"+key.upper())
    return f,hashlib.sha256(raw).hexdigest()

@dataclass(frozen=True)
class Case:
    seed:int
    block:int
    specimen:int
    query_depth:int
    observation_depths:tuple
    positive_values:tuple
    negative_values:tuple

def generate(seed,block,specimen):
    need(block in range(3) and specimen in range(3) and
         BLOCKS[block][0]<=seed<=BLOCKS[block][1] and
         not 51300<=seed<=51500 and not 63100<=seed<=63179,
         "UNFROZEN_OR_HISTORICAL_SEED")
    rng=random.Random((seed<<8)+(block<<5)+specimen*7+104)
    query=(seed+specimen)%4
    depths=list(range(4))
    vals=[rng.choice((-1.0,1.0)) for _ in range(4)]
    pos=vals.copy()
    neg=vals.copy()
    pos[query]=1.0
    neg[query]=-1.0
    rng.shuffle(depths)
    if block==1: depths.reverse()
    if block==2: depths=depths[1:]+depths[:1]
    result=Case(seed,block,specimen,query,tuple(depths),
                tuple(pos[t] for t in depths),tuple(neg[t] for t in depths))
    need(set(result.observation_depths)==set(range(4)) and
         sum(a!=b for a,b in zip(result.positive_values,
                                  result.negative_values))==1 and
         all(a==b for a,b,t in zip(result.positive_values,
                                  result.negative_values,depths) if t!=query),
         "NONCOUNTERFACTUAL_OBSERVATION_PAIR")
    return result

def coded_depth_observation_oracle(case,observations):
    """Ground-truth verifier and standalone control. Not used by model or fit."""
    return observations[case.observation_depths.index(case.query_depth)]>0

def public_groups():
    groups=[]
    seen=set()
    for block,(lo,hi) in enumerate(BLOCKS):
        cases=[]
        for seed in range(lo,hi+1):
            for specimen in range(3):
                p=generate(seed,block,specimen)
                need((p.seed,p.specimen) not in seen,"DUPLICATE_CASE")
                seen.add((p.seed,p.specimen))
                need(coded_depth_observation_oracle(p,p.positive_values) and
                     not coded_depth_observation_oracle(p,p.negative_values),
                     "INVALID_ORACLE_PAIR")
                cases.append(p)
        need(len(cases)==48,"BLOCK_SIZE_MISMATCH")
        groups.append(tuple(cases))
    need(len(seen)==144,"TOTAL_COHORT_MISMATCH")
    return tuple(groups)

def sigmoid(x):
    return 1/(1+math.exp(-max(-35.0,min(35.0,x))))

def softmax(scores):
    high=max(scores)
    weights=[math.exp(value-high) for value in scores]
    total=sum(weights)
    return [value/total for value in weights]

class LearnedObservationSelector:
    """18 trainable weights; each prediction reads exactly one observation."""
    parameters=18
    def __init__(self,depth_blind=False):
        self.attention=[0.02*((i*7)%5-2) for i in range(16)]
        self.scale=3.0
        self.bias=0.0
        self.depth_blind=depth_blind
        self.training_updates=0
    def row(self,p):
        return 0 if self.depth_blind else p.query_depth
    def attention_weights(self,p):
        need(len(p.observation_depths)==4 and
             set(p.observation_depths)==set(range(4)) and
             p.query_depth in range(4),"INVALID_PUBLIC_OBSERVATIONS")
        row=self.row(p)
        return softmax([self.attention[4*row+tag] for tag in p.observation_depths])
    def soft_prediction(self,p,values):
        need(len(values)==4 and all(v in (-1.0,1.0) for v in values),
             "INVALID_OBSERVATION_VALUE")
        weights=self.attention_weights(p)
        mean=sum(w*v for w,v in zip(weights,values))
        return sigmoid(self.scale*mean+self.bias),mean,weights
    def fit(self,group,steps=100):
        cases=tuple(group)
        need(len(cases)==96 and steps==100 and self.training_updates==0,
             "TRAINING_BUDGET_OR_REPLAY")
        for _ in range(steps):
            derivative=[0.0]*16
            dscale=dbias=0.0
            for p in cases:
                for values,label in ((p.positive_values,1),(p.negative_values,0)):
                    prob,mean,weights=self.soft_prediction(p,values)
                    error=prob-label
                    dscale+=error*mean
                    dbias+=error
                    for index,tag in enumerate(p.observation_depths):
                        param=4*self.row(p)+tag
                        derivative[param]+=error*self.scale*weights[index]*(values[index]-mean)
            step=4.0/(len(cases)*2)
            self.attention=[max(-12.0,min(12.0,w-step*grad))
                            for w,grad in zip(self.attention,derivative)]
            self.scale=max(0.1,min(20.0,self.scale-step*dscale))
            self.bias=max(-6.0,min(6.0,self.bias-step*dbias))
            self.training_updates+=1
        return self
    def choose(self,p):
        weights=self.attention_weights(p)
        return max(range(4),key=lambda i:weights[i])
    def probability(self,p,values):
        need(len(values)==4,"ONE_SLOT_INPUT_FORMAT")
        chosen=self.choose(p)
        return sigmoid(self.scale*values[chosen]+self.bias)
    def predicts(self,p,values):
        return self.probability(p,values)>=0.5
    def selected_depth(self,p):
        return p.observation_depths[self.choose(p)]

def paired_accuracy(cases,predict):
    cases=tuple(cases)
    need(bool(cases),"EMPTY_COHORT")
    return sum(predict(p,p.positive_values) and not predict(p,p.negative_values)
               for p in cases)/len(cases)

def evaluate(source_sha):
    need(type(source_sha)==str and re.fullmatch(r"[0-9a-f]{40}",source_sha) is not None and
         (not os.environ.get("GITHUB_SHA") or source_sha==os.environ["GITHUB_SHA"]),
         "SOURCE_REF_NOT_EXACT")
    cfg,digest=frozen()
    groups=public_groups()
    train=groups[0]+groups[1]
    diagnostic=groups[2]
    learner=LearnedObservationSelector().fit(train)
    blind=LearnedObservationSelector(depth_blind=True).fit(train)
    scores={
        "learned_query_gated_selector":paired_accuracy(diagnostic,learner.predicts),
        "size_matched_query_blind_selector":paired_accuracy(diagnostic,blind.predicts),
        "query_permuted_ablation":paired_accuracy(
            diagnostic,lambda p,v:learner.predicts(
                replace(p,query_depth=(p.query_depth+1)%4),v)),
        "fixed_first_observation_shortcut":paired_accuracy(
            diagnostic,lambda p,v:v[0]>0),
        "always_yes_shortcut":paired_accuracy(diagnostic,lambda p,v:True),
        "coded_requested_depth_oracle":paired_accuracy(diagnostic,coded_depth_observation_oracle),
    }
    depth_groups={str(depth):paired_accuracy(
        [p for p in diagnostic if p.query_depth==depth],learner.predicts)
        for depth in range(4)}
    need(all(any(p.query_depth==depth for p in diagnostic) for depth in range(4)),
         "EMPTY_DEPTH_STRATUM")
    changing=sum(len(set(learner.selected_depth(replace(p,query_depth=q))
                         for q in range(4)))>=3 for p in diagnostic)/len(diagnostic)
    selection_accuracy=sum(learner.selected_depth(p)==p.query_depth
                           for p in diagnostic)/len(diagnostic)
    neg_fp=sum(learner.predicts(p,p.negative_values) for p in diagnostic)/len(diagnostic)
    worst=min(depth_groups.values())
    limits=cfg["metrics"]["screen_only_thresholds"]
    passed=(scores["learned_query_gated_selector"]>=limits["minimum_paired_accuracy"] and
            scores["learned_query_gated_selector"]-
            scores["size_matched_query_blind_selector"]>=
            limits["minimum_improvement_vs_depth_blind"] and
            worst>=limits["minimum_worst_depth_accuracy"] and
            changing>=limits["minimum_changed_selection_fraction"])
    return dict(
        schema=REPORT,source_sha=source_sha,lane="Wingless",candidate_id="W100-C2",
        freeze_sha256=digest,
        evidence_class="PUBLIC_TOY_DEVELOPMENT_NOT_AUTHENTIC_UNSEEN_SCIENCE",
        training_pairs=96,public_assessment_pairs=48,total_development_pairs=144,
        trainable_parameters=18,learned_training_updates=learner.training_updates,
        blind_control_training_updates=blind.training_updates,
        observation_budget_per_prediction=1,
        public_assessment_paired_accuracy=scores,requested_depth_accuracies=depth_groups,
        worst_depth_accuracy=worst,query_dependent_selection_fraction=changing,
        selected_correct_observation_fraction=selection_accuracy,
        conflicting_negative_false_positive_rate=neg_fp,
        public_development_screen_passed=passed,
        historical_W_F10_negative_0_of_96_preserved=True,
        coded_oracle_separate_control_only=True,
        protected_first_use_authorized=False,scientific_originals_executed=0,
        independently_accepted_science=0,optimizer_promotion_authorized=False,
        accepted_ref_mutations=0,codex_calls=0,paid_model_api_calls=0,
        chatgpt_work_tasks=0,ckb_plane_accessed=False)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--source-ref",required=True)
    args=parser.parse_args()
    print(json.dumps(evaluate(args.source_ref),sort_keys=True,separators=(",",":")))

if __name__=="__main__":
    try: main()
    except (Rejected,KeyError,ValueError,TypeError,OSError) as exc:
        print("FORGE_F104_WINGLESS_OBSERVATION_DEV=QUARANTINED "+str(exc),file=sys.stderr)
        raise SystemExit(1)
