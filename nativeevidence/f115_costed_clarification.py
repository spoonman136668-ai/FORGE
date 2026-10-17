"""F115 public synthetic experiment: cost-aware optional source clarification.

Frozen before implementation. The post-request witness is a SIMULATED external
attestation, not a learned representation, cryptographic custodian, or scientific
original. No predictor sees its response until explicitly paying the request
cost; source sign evidence remains limited to one selected value.
"""
from __future__ import annotations
import argparse
from collections import Counter
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import random
import f114_partial_relation_abstention as f114

ROOT=Path(__file__).resolve().parents[1]
FREEZE=ROOT/"reference/research-intake/f115-costed-clarification-freeze.json"
FROZEN_BLOB="17237f70831d3d686776f3cfdc2f23aa43d12171"
PARENT_BLOB="3d3c47748b8f146419e688f49067b06466749319"
PARENT_SHA="8a2be937cad270b89cedd9672772aca345f1cbb5"
REPORT="forge.autonomy.f115.costed-public-evidence-acquisition-synthetic.v1"
SHA40=re.compile(r"^[a-f0-9]{40}$")
RANGES=((70000,70047),(70100,70147),(70200,70247))
NAMES=("W115-Q","W115-N","W115-H")

class Rejected(ValueError):pass
def require(ok,reason):
    if not ok:raise Rejected("F115_"+reason)
def raw(path):
    return Path(path).read_bytes().replace(b"\r\n",b"\n")
def gitblob(b):
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def frozen():
    blob=raw(FREEZE)
    require(gitblob(blob)==FROZEN_BLOB and
            gitblob(raw(ROOT/"nativeevidence/f114_partial_relation_abstention.py"))==
            PARENT_BLOB,"PARENT_OR_PRECODE_FREEZE_CHANGED")
    cfg=json.loads(blob)
    require(cfg.get("schema")=="forge.autonomy.f115.frozen-costed-evidence-clarification.v1" and
            cfg["parent"]["exact_head"]==PARENT_SHA and
            cfg["parent"]["f114_source_blob"]==PARENT_BLOB and
            cfg["parent"]["f114_freeze_blob"]=="c2a4587aae1e1a0f05089d2c9e01fbfdc3f90002" and
            [x["seed_range"] for x in cfg["cohorts"]]==[[70000,70047],[70100,70147],[70200,70247]] and
            [x["reliability"] for x in cfg["cohorts"]]==[1.,.5,1.] and
            [x["paired_twins"] for x in cfg["cohorts"]]==[24,24,24],
            "SOURCE_COHORT_IDENTITY_DRIFT")
    u=cfg["cost_and_reward"]
    require(u["correct"]==1. and u["wrong"]==-4. and
            u["abstain"]==-.1 and u["request_cost"]==.25 and
            u["high_cost_override"]==1.5 and u["one_request_max"]==1 and
            u["one_evidence_value_read_max"]==1 and
            u["requested_witness_is_explicit_simulated_external_metadata_not_trainable"] is True and
            u["formula"]=="p*1 + (1-p)*(-4) - cost > -0.1","COST_FROZEN_RULE_CHANGED")
    expected=cfg["locked_outcome"]
    require([expected[k] for k in ("Q","N","H")]==[
            {"requests":48,"correct":48,"wrong":0,"abstentions":0},
            {"requests":0,"correct":0,"wrong":0,"abstentions":48},
            {"requests":0,"correct":0,"wrong":0,"abstentions":48}] and
            expected["total_cases"]==144 and
            expected["min_utility_improvement_over_always_abstain"]==20. and
            expected["counterfactual_identical_before_request"] is True and
            expected["no_learned_model_superiority_claim"] is True,
            "OUTCOME_THRESHOLDS_RETUNED")
    require(all(cfg["guardrails"].values()),"PROTECTED_SCIENTIFIC_AUTHORITY")
    return cfg,hashlib.sha256(blob).hexdigest()

@dataclass(frozen=True)
class Offer:
    public:f114.Public
    witness_channel:str
    reliability:float
    cost:float
    # Offline truth, signs, hidden target and twin identities NOT included.

@dataclass(frozen=True)
class Example:
    offer:Offer
    offline_true_tag:int
    public_twin:int
    case_id:int
    positive:tuple[float,...]
    negative:tuple[float,...]

def make_case(seed,family):
    require(type(seed) is int and type(family) is int and family in range(3) and
            RANGES[family][0]<=seed<=RANGES[family][1],"WRONG_FROZEN_SEED")
    index=seed-RANGES[family][0]
    twin=index//2
    base_seed=RANGES[family][0]+2*twin
    target=(twin//4+family)%4
    p,base,rival=f114.frame(base_seed,2,target)
    truth=rival if index%2 else base
    offer_type="attested_source_relation_one_bit" if family in (0,2) else "uninformative_public_tag_reply"
    reliability=1. if family in (0,2) else .5
    cost=1.5 if family==2 else .25
    offer=Offer(p,offer_type,reliability,cost)
    rng=random.Random(base_seed*727+115)
    signs=[1. if rng.randrange(2) else -1. for _ in range(4)]
    positive=signs.copy();negative=signs.copy()
    positive[truth]=1.;negative[truth]=-1.
    plus=tuple(positive[i] for i in p.observation_order)
    minus=tuple(negative[i] for i in p.observation_order)
    require(sum(a!=b for a,b in zip(plus,minus))==1 and
            f114.certificate(p) is None,"FALSE_RESOLVABLE_OR_COUNTERFACTUAL")
    return Example(offer,truth,twin,seed,plus,minus)

def groups():
    all_cases=tuple(tuple(make_case(seed,f) for seed in range(lo,hi+1))
            for f,(lo,hi) in enumerate(RANGES))
    for family,cases in enumerate(all_cases):
        require(len(cases)==48 and len({c.case_id for c in cases})==48,
                "COHORT_BUDGET_MISSING")
        for j in range(0,48,2):
            a,b=cases[j:j+2]
            require(a.offer==b.offer and
                    a.public_twin==b.public_twin and
                    a.offline_true_tag!=b.offline_true_tag and
                    (a.positive!=b.positive or a.negative!=b.negative),
                    "PUBLIC_TWIN_INFORMATION_LEAK")
    return all_cases

def metadata_reply(ex):
    """Simulated external source; available ONLY after policy calls request.

    Reliable offer reveals a new attested relation to the hidden source.
    Uninformative offer returns same tag for both indistinguishable twins.
    This is NOT a real authenticated signer or independent measurement.
    """
    near,_=f114.nearest(ex.offer.public)
    require(len(near)==2,"NOT_AN_AMBIGUITY_CASE")
    if ex.offer.witness_channel=="attested_source_relation_one_bit":
        return ex.offline_true_tag
    if ex.offer.witness_channel=="uninformative_public_tag_reply":
        return min(near)
    raise Rejected("UNKNOWN_SIMULATED_WITNESS_CHANNEL")

def would_request(offer):
    need=offer.reliability*1+(1-offer.reliability)*(-4)-offer.cost
    return need>-.1

def choose(offer,request,policy):
    """No offline true tag may appear in these inputs.

    Returns (chosen tag or None, request count). Never reads signs here.
    """
    selected=f114.certificate(offer.public)
    if selected is not None:
        return selected,0
    if policy=="selective":
        if not would_request(offer):
            return None,0
    elif policy in ("never","abstain"):
        return None,0
    elif policy=="forced":
        return f114.forced_relation(offer.public),0
    elif policy!="always":
        raise Rejected("UNKNOWN_FIXED_POLICY")
    tag=request()
    require(type(tag) is int and tag in f114.nearest(offer.public)[0],
            "INJECTED_REPLY_NOT_PUBLIC_CANDIDATE")
    # A known uninformative public reply is not independently authenticated:
    # do not translate it into an asserted scientific fact.
    return tag,1

def examine(ex,policy):
    calls=[]
    def request():
        require(len(calls)==0,"MULTIPLE_PUBLIC_EVIDENCE_REQUESTS")
        calls.append(1)
        return metadata_reply(ex)
    chosen,count=choose(ex.offer,request,policy)
    require(count==len(calls) and count<=1,"REQUEST_BUDGET")
    if chosen is None:
        status="abstain"
    else:
        index=ex.offer.public.observation_order.index(chosen)
        # One sign selection; the *other* signs do not affect any decision.
        status="correct" if ex.positive[index]>0 and ex.negative[index]<0 else "wrong"
    return {"id":ex.case_id,"public_twin":ex.public_twin,
        "public_offer_sha256":hashlib.sha256(json.dumps({
          "public":ex.offer.public.__dict__,"reliability":ex.offer.reliability,
          "cost":ex.offer.cost,"offer":ex.offer.witness_channel
        },sort_keys=True).encode()).hexdigest(),
        "chosen_tag":chosen,"requested":count,"status":status,
        "offline_true_tag":ex.offline_true_tag}

def assess(cases,policy):
    rows=[examine(ex,policy) for ex in cases]
    c=Counter(row["status"] for row in rows)
    requests=sum(row["requested"] for row in rows)
    cost_by_id={case.case_id:case.offer.cost for case in cases}
    acquisition_cost=sum(row["requested"]*cost_by_id[row["id"]] for row in rows)
    utility=c["correct"]-4*c["wrong"]-.1*c["abstain"]-acquisition_cost
    return {"total":len(rows),"correct":c["correct"],"wrong":c["wrong"],
        "abstentions":c["abstain"],"requests":requests,
        "total_request_cost":round(acquisition_cost,3),
        "utility":round(utility,4),"records":rows}

def evaluate(sha):
    require(type(sha) is str and SHA40.fullmatch(sha) and
            (not os.environ.get("GITHUB_SHA") or os.environ["GITHUB_SHA"]==sha),
            "CURRENT_GITHUB_SOURCE_SHA_REQUIRED")
    cfg,freeze_hash=frozen()
    parent=f114.evaluate(sha)
    require(parent["public_selective_retrieval_screen_passed"] is True and
            parent["certificate_resolvable_covered"]==96 and
            parent["certificate_unresolvable_abstained"]==48 and
            parent["certificate_covered_wrong"]==0 and
            parent["learned_superiority_claimed"] is False and
            parent["accepted_ref_mutations"]==0,
            "F114_PARENT_QUALIFICATION_CHANGED")
    cases=groups()
    policies=("selective","never","always","forced","abstain")
    blocks=[]
    for label,c in zip(("Q","N","H"),cases):
        scores={policy:assess(c,policy) for policy in policies}
        blocks.append({"cohort":"W115-"+label,"pairs":48,"policies":scores})
    for key,block in zip(("Q","N","H"),blocks):
        s=block["policies"]["selective"]
        expected=cfg["locked_outcome"][key]
        require(all(s[field]==value for field,value in expected.items()),
                "PRECOMMITTED_SELECTIVE_RESULT_FALSIFIED_"+key)
    main=sum(b["policies"]["selective"]["utility"] for b in blocks)
    never=sum(b["policies"]["never"]["utility"] for b in blocks)
    require(main-never>=cfg["locked_outcome"][
        "min_utility_improvement_over_always_abstain"],"BOUNDED_UTILITY_SCREEN_FAILED")
    return {"schema":REPORT,"source_sha":sha,
        "freeze_sha256":freeze_hash,
        "parent_f114_source_blob":PARENT_BLOB,
        "evidence_class":"SIMULATED_PUBLIC_METADATA_ACQUISITION_NOT_INDEPENDENT_SCIENCE",
        "public_pairs":144,"identical_public_twins":72,
        "certificate_parent_reproduced":True,
        "precommitted_selective_screen_passed":True,
        "selective_utility":round(main,3),
        "never_request_utility":round(never,3),
        "utility_improvement":round(main-never,3),
        "cohorts":blocks,
        "all_pairwise_decisions_retained":True,
        "simulated_attestation_not_verified_real_issuer":True,
        "learned_model_superiority_claimed":False,
        "independently_accepted_science":0,
        "protected_scientific_first_use":False,
        "native_scientific_dispatches":0,
        "optimizer_promotions":0,"accepted_ref_mutations":0,
        "codex_calls":0,"paid_model_calls":0,"work_tasks":0,
        "new_scheduler_created":False,"ckb_plane_contact":False,
        "cloudflare_writes":0,"mind_palace_writes":0}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--source-ref",required=True)
    a=parser.parse_args()
    print(json.dumps(evaluate(a.source_ref),sort_keys=True,separators=(",",":")))

if __name__=="__main__":
    try:main()
    except (Rejected,f114.Invalid,TypeError,ValueError,KeyError,OSError) as err:
        print("F115_SYNTHETIC_PUBLIC_CLARIFICATION=QUARANTINED "+str(err),file=sys.stderr)
        raise SystemExit(1)
