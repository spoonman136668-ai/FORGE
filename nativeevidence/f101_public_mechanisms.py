"""F101: bounded learned mechanism DEV prototypes, never protected scientific originals.

The independent, immutable F101 algorithm plan is committed before this file.
All training and evaluation use predefined PUBLIC development seed blocks only.
No model APIs, Codex, Cloudflare, external calls or accepted-ref mutations.
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

ROOT=pathlib.Path(__file__).resolve().parents[1]
F100=ROOT/"reference/research-intake/f100-frozen-successor-contract.json"
PLAN=ROOT/"reference/research-intake/f101-frozen-public-dev-implementation-plan.json"
SCHEMA="forge.autonomy.f101.public-development-unaccepted.v1"
PLAN_SCHEMA="forge.autonomy.f101.frozen-public-dev-prototype-plan.v1"
class Quarantine(ValueError):pass
def need(ok,reason):
    if not ok:raise Quarantine("F101_"+reason)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def initial(cid,count):
    seed=int.from_bytes(hashlib.sha256((cid+":F101:implementation:v1").encode()).digest()[:8],"big")
    rng=random.Random(seed)
    return [rng.uniform(-0.25,0.25) for _ in range(count)]
def rng_for(lane,seed):
    seed_bytes=hashlib.sha256((lane+":"+str(seed)).encode()).digest()
    return random.Random(int.from_bytes(seed_bytes[:8],"big"))
def plan():
    d=json.loads(PLAN.read_text(encoding="utf-8"))
    from f100_frozen_successors import audit
    proof=audit(source_sha=os.getenv("GITHUB_SHA") or "a"*40)
    need(proof["candidates_frozen"]==4 and
         proof["new_experiments_executed"]==0 and
         proof["scientific_first_use_authorized"] is False,
         "F100_FIRST_USE_OR_SOURCE_DRIFT")
    need(d.get("schema")==PLAN_SCHEMA and d.get("preimplementation_preregistration") is True and
         d.get("parent_contract_blob")=="79718d11be36ac4742774cf3ab3d502ef2feab59" and
         d.get("parent_head")=="356955de3548a56eb916471c505ab36f4f232957" and
         d.get("scope")=="PUBLIC_DEVELOPMENT_ONLY_NO_PROTECTED_ORIGINAL",
         "PREIMPLEMENTATION_PLAN_DRIFT")
    need(d.get("candidate_order")==["W100-C1","W100-C2","Y100-C1","Y100-C2"] and
         d.get("seeds",{}).get("train_blocks")==[0,1] and
         d["seeds"].get("dev_block")==2 and
         d["seeds"].get("per_seed_matched_examples")==2 and
         d["seeds"].get("no_post_result_tuning") is True,
         "CANDIDATE_OR_PUBLIC_SPLIT_DRIFT")
    opt=d.get("optimization",{})
    need(opt.get("kind")=="deterministic_cyclic_finite_difference_logistic_cross_entropy" and
         opt.get("max_steps")==100 and opt.get("perturbation")==0.1 and
         opt.get("step_size")==0.35 and opt.get("clip_parameters")==[-8,8] and
         opt.get("loss_cap")==20 and opt.get("all_candidates_evaluated") is True,
         "OPTIMIZER_DRIFT")
    models=d.get("model",{})
    need({k:v.get("parameter_count") for k,v in models.items()}==
         {"W100-C1":9,"W100-C2":9,"Y100-C1":11,"Y100-C2":19},
         "PARAMETER_BUDGET_DRIFT")
    auth=d.get("authorization",{})
    need(auth.get("protected_first_use") is False and
         auth.get("genenv_policy_training") is False and
         auth.get("autonomous_gpt_executor") is False and
         all(type(auth.get(k)) is int and auth[k]==0 for k in
             ("model_inference_api_calls","codex_calls","paid_model_api_calls",
              "accepted_ref_mutations","scientific_original_dispatches")),
         "EXECUTION_AUTHORITY_UNEXPECTED")
    return d
def pair(lane,seed):
    """Matched public DEV counterfactuals, independent of frozen historical IDs."""
    r=rng_for(lane,seed)
    if lane=="Wingless":
        depth=r.choice([2,3,4])
        false_depth=r.choice([d for d in [2,3,4] if d!=depth])
        internal=r.sample(list(range(1,7)),depth-1)
        chain=[0]+internal+[7]
        edges=tuple((chain[i],chain[i+1],0) for i in range(len(chain)-1))
        # Unrelated loops cannot form alternate source->target paths.
        unused=[u for u in range(1,7) if u not in internal]
        edges+=tuple((u,u,0) for u in unused[:2])
        cases=[dict(lane=lane,seed=seed,edges=edges,depth=d,truth=int(d==depth),
                    group=str(depth)) for d in (depth,false_depth)]
    else:
        actual=tuple(r.randrange(4) for _ in range(3))
        wrong=list(actual)
        pos=r.randrange(3)
        wrong[pos]=(wrong[pos]+r.randrange(1,4))%4
        middle=r.sample(list(range(1,7)),2)
        nodes=[0]+middle+[7]
        edges=tuple((nodes[i],nodes[i+1],actual[i]) for i in range(3))
        cases=[dict(lane=lane,seed=seed,edges=edges,roles=roles,
                    truth=int(roles==actual),group=str(actual[0])) for roles in
               (actual,tuple(wrong))]
    if r.randrange(2):cases.reverse()
    need(len(cases)==2 and sum(z["truth"] for z in cases)==1 and
         cases[0]["edges"]==cases[1]["edges"],"UNMATCHED_COUNTERFACTUAL_PAIR")
    return tuple(cases)
def source_controls(x):
    """A strong exact coded oracle used ONLY as a NON-TRAINABLE control."""
    reachable={0}
    if x["lane"]=="Wingless":
        for _ in range(x["depth"]):
            reachable={v for u,v,_ in x["edges"] if u in reachable}
    else:
        for role in x["roles"]:
            reachable={v for u,v,r in x["edges"] if r==role and u in reachable}
    return int(7 in reachable)
def logistic(x):
    x=max(-30.,min(30.,x))
    return 1/(1+math.exp(-x))
def forward(x,params,cid):
    """Query-aware SOFT propagation, not an oracle nor any exact truth-match."""
    h=[0.0]*8
    h[0]=1.
    if x["lane"]=="Wingless":
        depth=x["depth"]
        for step in range(depth):
            nxt=[0.0]*8
            for u,v,_ in x["edges"]:
                if cid=="W100-C1":
                    gate=logistic(params[0]+params[1]*step/4+
                                  params[2]*v/7+params[3]*depth/4)
                else:
                    # Learned observation weights depend on query depth and
                    # source/target geometry; the truth label is unavailable.
                    gate=logistic(params[0]+params[1]*u/7+
                                  params[2]*v/7+params[3]*depth/4)
                nxt[v]+=h[u]*gate
            h=[min(1.,v) for v in nxt]
        return logistic(params[8]*h[7]*5+params[4]+params[5+depth-2])
    role_codes=x["roles"]
    for role in role_codes:
        nxt=[0.0]*8
        for u,v,edge_role in x["edges"]:
            if cid=="Y100-C1":
                # Learned 1D embedding compatibility, not hardcoded equality.
                distance=(params[edge_role]-params[4+role])**2
                gate=logistic(params[8]-distance)
            else:
                # Learned two-coordinate, node-renaming invariant binding.
                # Only connectivity + typed role codes, never node IDs as slots.
                distance=((params[2*edge_role]-params[8+2*role])**2+
                          (params[2*edge_role+1]-params[8+2*role+1])**2)
                gate=logistic(params[16]-distance)
            nxt[v]+=h[u]*gate
        h=[min(1.,v) for v in nxt]
    return logistic(params[10]*h[7]*5+params[9] if cid=="Y100-C1"
                    else params[18]*h[7]*5+params[17])
def masked_query(x,variant):
    y=dict(x)
    if variant=="full":return y
    if variant=="missing":
        if y["lane"]=="Wingless":y["depth"]=3
        else:y["roles"]=(0,0,0)
        return y
    need(variant=="permuted","INVALID_ABLATION")
    h=hashlib.sha256(repr((y["lane"],y["seed"],y.get("depth",y.get("roles")),
                           y["truth"],"F101-PRECOMMITTED-PUBLIC-NULL")).encode()).digest()
    # Null query is unrelated to the matching source/query condition.
    # The truth value is used only to ensure an independent seed per example,
    # never as an input to a trained model: this is a CONTROL, not a candidate.
    r=random.Random(int.from_bytes(h[:8],"big"))
    if y["lane"]=="Wingless":y["depth"]=r.choice([2,3,4])
    else:y["roles"]=tuple(r.randrange(4) for _ in range(3))
    return y
def samples(lane,seed_block):
    return [pair(lane,seed) for seed in seed_block]
def loss(params,pairs,cid,mask):
    total=0.
    n=0
    for matched in pairs:
        for example in matched:
            p=forward(masked_query(example,mask),params,cid)
            total-=example["truth"]*math.log(max(1e-10,p))
            total-=(1-example["truth"])*math.log(max(1e-10,1-p))
            n+=1
    return min(20.,total/n)
def train(cid,params,train_pairs,variant):
    weights=list(params)
    for step in range(100):
        i=step%len(weights)
        old=weights[i]
        weights[i]=old+0.1
        high=loss(weights,train_pairs,cid,variant)
        weights[i]=old-0.1
        low=loss(weights,train_pairs,cid,variant)
        weights[i]=max(-8.,min(8.,old-0.35*(high-low)/0.2))
    return weights
def evaluate(cid,params,pairs,variant):
    correct=0
    pairs_correct=0
    groups={}
    for matched in pairs:
        checks=[]
        for x in matched:
            pred=int(forward(masked_query(x,variant),params,cid)>=0.5)
            correct+=int(pred==x["truth"])
            checks.append(pred==x["truth"])
        ok=all(checks)
        pairs_correct+=int(ok)
        # Stratum is from the original PUBLIC environment, never a held-out
        # scientific original; negative cases are counted exactly once.
        grp=next(z["group"] for z in matched if z["truth"]==1)
        stat=groups.setdefault(grp,[0,0])
        stat[0]+=int(ok)
        stat[1]+=1
    return dict(pairs=len(pairs),paired_correct=pairs_correct,
                paired_accuracy=pairs_correct/len(pairs),
                question_accuracy=correct/(2*len(pairs)),
                worst_group_paired_accuracy=min(n/d for n,d in groups.values()))
def run(source):
    need(type(source) is str and re.fullmatch(r"[0-9a-f]{40}",source) and
         (not os.getenv("GITHUB_SHA") or os.getenv("GITHUB_SHA")==source),
         "GITHUB_SOURCE_DRIFT")
    frozen_plan=plan()
    f100=json.loads(F100.read_text(encoding="utf-8"))
    results=[]
    for lane in f100["lanes"]:
        name=lane["lane"]
        blocks=lane["public_development_seed_blocks"]
        train_ids=[n for a,b in blocks[:2] for n in range(a,b+1)]
        dev_ids=[n for n in range(blocks[2][0],blocks[2][1]+1)]
        need(len(train_ids)==32 and len(dev_ids)==16 and
             not(set(train_ids)&set(dev_ids)) and
             all(n>60000 for n in train_ids+dev_ids),"SEED_LEAK_OR_BUDGET")
        train_pairs=samples(name,train_ids)
        dev_pairs=samples(name,dev_ids)
        need(all(source_controls(x)==x["truth"] for q in train_pairs+dev_pairs for x in q),
             "PUBLIC_GENERATOR_ORACLE_CONTRADICTION")
        for candidate in lane["candidates"]:
            cid=candidate["id"]
            count=frozen_plan["model"][cid]["parameter_count"]
            weights=initial(cid,count)
            # Train all four candidates, plus independent size-matched
            # information-missing and query-randomized learned controls.
            outputs={}
            for variant in ("full","missing","permuted"):
                trained=train(cid,weights,train_pairs,variant)
                outputs[variant]=evaluate(cid,trained,dev_pairs,variant)
                outputs[variant]["weights_sha256"]=sha(
                    json.dumps([round(v,10) for v in trained],separators=(",",":")).encode())
            threshold=lane["preliminary_development_screen"]
            primary=outputs["full"]
            missing=outputs["missing"]
            passed=(primary["paired_accuracy"]>=threshold["minimum_paired_accuracy"] and
                    primary["paired_accuracy"]-missing["paired_accuracy"]>=
                    threshold["minimum_improvement_vs_size_matched_blind"] and
                    primary["worst_group_paired_accuracy"]>=
                    threshold["minimum_worst_group_paired_accuracy"])
            results.append(dict(lane=name,candidate_id=cid,
              mechanism_family=candidate["mechanism_family"],parameters=count,
              train_public_pairs=len(train_pairs),dev_public_pairs=len(dev_pairs),
              optimizer_steps=100,learned_public_dev=outputs,
              historical_blind_paired_accuracy=0.,
              always_yes_paired_accuracy=0.,
              coded_oracle_paired_accuracy=1.,
              passed_public_dev_thresholds=passed,
              outcome="PUBLIC_DEVELOPMENT_ONLY_NOT_ACCEPTED_SCIENCE",
              scientific_first_use_authorized=False))
    need(len(results)==4 and [r["candidate_id"] for r in results]==
         ["W100-C1","W100-C2","Y100-C1","Y100-C2"],"INCOMPLETE_CANDIDATE_POPULATION")
    return dict(schema=SCHEMA,forge_source_sha=source,
         f101_plan_sha256=sha(PLAN.read_bytes()),candidate_results=results,
         public_development_candidate_tests=4,
         public_development_control_training_runs=8,
         protected_scientific_originals=0,
         accepted_scientific_results=0,accepted_reference_mutations=0,
         research_worker_dispatches=0,model_api_calls=0,codex_calls=0,
         paid_inference_calls=0,scientific_first_use_authorized=False,
         policy_promotion_authorized=False,autonomous_gpt_executor_active=False)
def main(argv):
    p=argparse.ArgumentParser()
    p.add_argument("--source-ref",required=True)
    args=p.parse_args(argv)
    print(json.dumps(run(args.source_ref),sort_keys=True,separators=(",",":")))
if __name__=="__main__":
    try:main(sys.argv[1:])
    except (Quarantine,KeyError,TypeError,ValueError,OSError) as exc:
        print("FORGE_F101_PUBLIC_ONLY_PROTOTYPES_QUARANTINED "+str(exc),file=sys.stderr)
        raise SystemExit(1)
