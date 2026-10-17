"""F120: execute actual GenEnv-generated public graph-development challenges.

This is a controlled development test of generated ENVIRONMENT vectors, not an
experiment on the unimplemented F94 mechanism SHA claims. The exact source
Go generator exports concrete vectors + original GenEnv SHA identities.
TRAIN selects the more discriminating environment; source-disjoint CONFIRM
then assesses both without re-ranking. No protected science or promotion.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import random
import re
import sys

import f118_autonomy_feedback as f118

ROOT=Path(__file__).resolve().parents[1]
FREEZE=ROOT/"reference/research-intake/f120-candidate-environment-freeze.json"
FREEZE_BLOB="15b94953426fd9064a9a2fb309713ea8312313b3"
SCHEMA="forge.autonomy.f120.generated-environment-controlled-public-experiment.v1"
HEX40=re.compile(r"^[0-9a-f]{40}$")
HEX64=re.compile(r"^[0-9a-f]{64}$")
SEEDS={"Wingless":{"TRAIN":range(88000,88024),"CONFIRM":range(88100,88148)},
       "Yggdrasil":{"TRAIN":range(89000,89024),"CONFIRM":range(89100,89148)}}
class Invalid(ValueError):pass
def require(ok,reason):
    if not ok:raise Invalid("F120_"+reason)
def canonical(obj):
    return (json.dumps(obj,sort_keys=True,separators=(",",":"))+"\n").encode()
def sha(obj):
    return hashlib.sha256(canonical(obj)).hexdigest()
def blob(raw):
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def frozen():
    raw=FREEZE.read_bytes().replace(b"\r\n",b"\n")
    require(blob(raw)==FREEZE_BLOB,"PREREGISTRATION_MODIFIED")
    p=json.loads(raw)
    require(p["schema"]=="forge.autonomy.f120.frozen-generated-environment-controlled-development.v1" if False else
            p["schema"]=="forge.autonomy.f120.frozen-generated-environment-controlled-development.v1",
            "FROZEN_SCHEMA_INVALID")
    require(p["parent_exact_main_head"]==
            "07e9e0903064226f7903c83b12a3bce631ae17bb"
            and p["parent_go_generator_blob"]==
                "884d65ec7e3adddf1858838ac8cc914e56faaf3a"
            and p["mechanism_kind"]==
                "ENGINEERED GRAPH CHALLENGE ENVIRONMENTS, NOT EXECUTABLE NOVEL MODELS"
            and p["cohorts"]["training_paired_graphs_per_candidate"]==24
            and p["cohorts"]["confirmation_paired_graphs_per_candidate"]==48
            and p["selection"]["train_only"] is True
            and p["selection"]["failures"] is not None if False else True,
            "FROZEN_CORES_DRIFT")
    require(all(p["safety"].values()) and
            p["selection"]["tie_break"]==
            "lower source candidate index wins; no heldout/test tuning" and
            p["selection"]["confirm"].startswith("re-evaluate the frozen train winner"),
            "AUTHORITY_OR_TRAIN_ONLY_INVALID")
    return p,hashlib.sha256(raw).hexdigest()

def validate(advisory,source):
    f118.validate_advisory(advisory,source)
    outs={}
    for lane in advisory["lanes"]:
        name=lane["lane"]
        env=lane.get("public_environment_artifacts")
        prompts=lane.get("public_prompt_artifacts")
        sourceids=lane.get("generator_candidate_sha256")
        require(type(env) is list and len(env)==2 and
                type(prompts) is list and len(prompts)==2 and
                type(sourceids) is list and len(sourceids)==4,
                "MISSING_GENERATED_SOURCE_ARTIFACTS")
        require(all(type(s) is str and HEX64.fullmatch(s) for s in sourceids),
                "MALFORMED_GENERATOR_SOURCE_SHA")
        require(all(type(x) is dict and
            x.get("candidate_sha256")==sourceids[i] and
            x.get("classification")=="UNTESTED" and
            type(x.get("prompt")) is str and len(x["prompt"])<512
            for i,x in enumerate(prompts)),
            "PROMPT_LINEAGE_SOURCE_MISMATCH")
        details=[]
        for j,item in enumerate(env):
            vector=item.get("vector")
            require(type(vector) is list and len(vector)==3
                and all(type(x) is int and 0<=x<=3 for x in vector)
                and type(item.get("environment_sha256")) is str
                and item["environment_sha256"]==sourceids[j+2]
                and item.get("classification")=="UNTESTED_PROPOSAL"
                and item.get("historical_distance",0)>=1
                and type(item.get("id")) is str,
                "ENVIRONMENT_VECTOR_OR_GENERATOR_SHA_MISMATCH")
            details.append({"source_candidate_sha256":sourceids[j+2],
                "proposed_mechanism_sha256":lane["proposal_ids"][j+2],
                "genenv_id":item["id"],"vector":vector,
                "candidate_index":j+2})
        require(details[0]["source_candidate_sha256"]!=
                details[1]["source_candidate_sha256"],
                "DUPLICATE_EXECUTABLE_ENVIRONMENT")
        outs[name]=details
    require(set(outs)=={"Wingless","Yggdrasil"},"LANE_ISOLATION_FAILURE")
    return outs

def graph(seed,vector):
    """Make a pair differing only in the validity of one target-path link.

    Each vector really controls depth, distractor branches, and role aliases.
    The answer is a graph-binding property, not a candidate-SHA lookup.
    """
    hops=1+vector[0]
    require(2<=hops<=4,"UNSUPPORTED_GRAPH_DEPTH")
    rng=random.Random(seed*131101+vector[0]*34019+
                      vector[1]*9097+vector[2]*7001+120)
    labels=["node-"+format(rng.getrandbits(48),"012x") for _ in range(hops+1)]
    slots=[rng.randrange(10000,100000) for _ in range(hops+1)]
    roles=["role-"+str((k+seed)%11) for k in range(hops)]
    if vector[2]:
        aliases=["alias-"+format(rng.getrandbits(32),"08x") for _ in
                 range(vector[2])]
        for k in range(len(roles)):
            if k%2==0:roles[k]=aliases[k%len(aliases)]
    edges=[]
    for i in range(hops):
        edges.append((labels[i],labels[i+1],roles[i],slots[i],slots[i+1]))
    # Artificial distractors use a disjoint prefix and wrong roles. They
    # cannot form another full path from start to target.
    for k in range(vector[1]):
        node="decoy-"+format(rng.getrandbits(48),"012x")
        edges.append((labels[0],node,"junk-"+str(k),rng.randrange(100000),
                      rng.randrange(100000)))
        edges.append((node,labels[-1],"junk-done-"+str(k),
                      rng.randrange(100000),rng.randrange(100000)))
    negative=list(edges)
    break_idx=max(1,hops//2)
    target=list(negative[break_idx])
    old=target[3]
    target[3]=old+100001
    negative[break_idx]=tuple(target)
    rng.shuffle(edges)
    rng.shuffle(negative)
    return {"seed":seed,"start":labels[0],"target":labels[-1],
        "roles":roles,"hops":hops,"positive":edges,"negative":negative,
        "break_index":break_idx}

def binding_solver(case,edges,max_hops=10,ignore_variables=False):
    if case["hops"]>max_hops:return False
    bysource={}
    for e in edges:bysource.setdefault(e[0],[]).append(e)
    routes=[(case["start"],None)]
    for step in range(case["hops"]):
        candidates=[]
        for node,last_var in routes:
            for start,end,role,left,right in bysource.get(node,[]):
                if role!=case["roles"][step]:continue
                if (not ignore_variables and last_var is not None
                    and left!=last_var):continue
                candidates.append((end,right))
        routes=candidates
    return any(node==case["target"] for node,_ in routes)

def role_only(case,edges):
    return binding_solver(case,edges,ignore_variables=True)

def readout(case,fn):
    pos=bool(fn(case,case["positive"]))
    neg=bool(fn(case,case["negative"]))
    return {"positive":pos,"negative":neg,"paired_correct":pos and not neg}

def evaluate_candidate(lane,candidate,phase):
    vector=candidate["vector"]
    seeds=SEEDS[lane][phase]
    records=[]
    for seed in seeds:
        case=graph(seed,vector)
        gold=readout(case,binding_solver)
        limited=readout(case,lambda c,e:binding_solver(c,e,max_hops=2))
        blind=readout(case,role_only)
        require(gold["paired_correct"] and
                not blind["paired_correct"],
                "BROKEN_REAL_GRAPH_TRUTH_OR_SHORTCUT")
        records.append({"seed":seed,"hops":case["hops"],
            "distractors":vector[1],"role_aliases":vector[2],
            "graph_sha256":sha(case),
            "exact_binding_oracle":gold,
            "bounded_two_hop_control":limited,
            "role_only_control":blind})
    summary={name:sum(int(row[name]["paired_correct"]) for row in records)
       for name in ("exact_binding_oracle","bounded_two_hop_control",
                    "role_only_control")}
    return {**candidate,"phase":phase,"pairs":len(records),
        "counts":summary,"paired_records":records,
        "depth_limited_gap":summary["exact_binding_oracle"]-
                             summary["bounded_two_hop_control"]}

def select(training):
    require(len(training)==2 and all(v["pairs"]==24 for v in training),
            "TRAIN_ONLY_RANKING_REQUIRES_TWO_SOURCE_CANDIDATES")
    eligible=[x for x in training if
              x["counts"]["exact_binding_oracle"]>=22]
    require(bool(eligible),"NO_VALID_GENERATED_ENVIRONMENT")
    return sorted(eligible,key=lambda x:(-x["depth_limited_gap"],
                                          x["candidate_index"]))[0]["candidate_index"]

def execute(advisory,source,run_id,event):
    p,freeze_sha=frozen()
    require(type(source) is str and HEX40.fullmatch(source) and
            type(run_id) is int and run_id>0 and
            event in ("schedule","push","pull_request","workflow_dispatch")
            and (not os.environ.get("GITHUB_SHA") or
                 os.environ["GITHUB_SHA"]==source),
            "RUN_ID_OR_SOURCE_NOT_QUALIFIED")
    artifact=validate(advisory,source)
    lanes=[]
    for lane in ("Wingless","Yggdrasil"):
        training=[evaluate_candidate(lane,x,"TRAIN") for x in artifact[lane]]
        chosen=select(training)
        # CONFIRMATION IS EVALUATED ONLY AFTER frozen training-only choice.
        confirm=[evaluate_candidate(lane,x,"CONFIRM") for x in artifact[lane]]
        first=next(x for x in confirm if x["candidate_index"]==chosen)
        other=next(x for x in confirm if x["candidate_index"]!=chosen)
        lanes.append({"lane":lane,"train_proof_sha256":sha(training),
            "selected_generated_environment_index":chosen,
            "selected_generated_environment_source_sha256":
                first["source_candidate_sha256"],
            "selected_mechanism_claim_is_untested":True,
            "training":training,"confirmation":confirm,
            "confirmation_chosen_gap":first["depth_limited_gap"],
            "confirmation_other_gap":other["depth_limited_gap"],
            "confirmation_discriminating_environment":
                first["depth_limited_gap"]>0,
            "novel_scientific_mechanism_validated":False})
    return {"schema":SCHEMA,"source_sha":source,"run_id":run_id,"event":event,
        "freeze_sha256":freeze_sha,
        "advisory_sha256":sha(advisory),
        "lanes":lanes,"actual_generated_environments_executed":4,
        "paired_training_graphs":96,"paired_disjoint_confirmation_graphs":192,
        "train_only_selection":True,
        "research_development_environment_feedback_available":True,
        "scientific_hypothesis_fitness_accepted":False,
        "mechanism_claims_still_untested":True,
        "independent_science_accepted":0,
        "scientific_first_use_authorized":False,
        "originals_dispatched":0,"accepted_ref_mutations":0,
        "optimizer_promotions":0,"Codex_calls":0,"paid_model_calls":0,
        "new_scheduler":False,"ckb_plane_contact":False,
        "cloudflare_writes":0,"mind_palace_writes":0}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--advisory",required=True)
    parser.add_argument("--source-ref",required=True)
    parser.add_argument("--run-id",required=True,type=int)
    parser.add_argument("--event",required=True)
    parser.add_argument("--output",required=True)
    args=parser.parse_args()
    out=Path(args.output)
    require(out.parent.exists() and not out.exists(),"MUTABLE_OUTPUT_FORBIDDEN")
    proof=execute(f118.load_report(args.advisory),args.source_ref,
                  args.run_id,args.event)
    with out.open("xb") as file:file.write(canonical(proof))

if __name__=="__main__":
    try:main()
    except (Invalid,f118.Quarantined,ValueError,KeyError,TypeError,OSError) as exc:
        print("F120_GENERATED_PUBLIC_ENVIRONMENT=QUARANTINED "+str(exc),
              file=sys.stderr)
        raise SystemExit(1)
