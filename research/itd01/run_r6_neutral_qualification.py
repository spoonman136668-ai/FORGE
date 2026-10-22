"""R6: ONE fixed public-only generic action policy over R3 AND R5 neutral events.

A transparent scripted developer ceiling, NOT a learned native architecture.
No original H1/H2, hidden graph, source-family flag, or legacy event names.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import time
from public_dev import PUBLIC_FAMILIES, action, canonical
from public_dev_r3 import PublicCausalDevWorld
from r5_causal_dev import R5CausalWorld
from r6_neutral_ontology import (normalize_public_observation,
                                  public_transition_from_step)
from run_public_baselines import peak_rss_bytes


def neutral_scripted_public_policy(initial: dict, step):
    """Same unchanged SCRIPTED policy for both R3 and R5 (NOT cognition).

    Only expects neutral observed-effect/confirmation, public entity labels,
    publicly observed partial/ready and legal action catalogue. Causal graph
    roles, world-family name and event producer identities are not inputs.
    """
    assert initial["schema"] == "itd01.observe-neutral.v1"
    names = sorted(e["id"] for e in initial["entities"])
    put, undo = initial["entities"][0]["legal_values"]
    used=0

    def probe_action(verb,target=None,value=None):
        nonlocal used
        used+=1
        if used>41:
            raise ValueError("ITD01_R6_PUBLIC_AGENT_OVERRAN_ACTION_LIMIT")
        return step(action(verb,target,value))

    def after_act(src, value):
        result=probe_action("intervene",src,value)
        observed=[]
        for _ in range(3):
            result=probe_action("wait")
            observed.extend(result["observation"]["events"])
        return result, observed

    for candidate in names:
        last, events=after_act(candidate,put)
        ready=[e for e in events if e["type"]=="observed-effect"]
        if not ready:
            probe_action("intervene",candidate,undo)
            continue
        # The first observable effect identifies a downstream PUBLIC node.
        src=candidate
        next_entity=ready[-1]["entity"]
        status=ready[-1]["observation"]
        # Retry same upstream action if PUBLIC effect says it is only partial.
        if status=="partial":
            last,events=after_act(src,put)
            ready=[e for e in events if e["type"]=="observed-effect"
                   and e["observation"]=="ready"]
            if not ready:
                return probe_action("commit")
            next_entity=ready[-1]["entity"]
        if status not in ("ready","partial"):
            return probe_action("commit")
        # Unknown number of stages: continue while public effects reveal the
        # next entity, stopping only on PUBLIC confirmation.
        visited={src}
        for _ in range(3):
            if next_entity in visited:
                return probe_action("commit")
            visited.add(next_entity)
            last,events=after_act(next_entity,put)
            if any(e["type"]=="observed-confirmation" for e in events):
                return probe_action("commit")
            ready=[e for e in events if e["type"]=="observed-effect"
                   and e["observation"]=="ready"]
            if ready:
                next_entity=ready[-1]["entity"]
                continue
            return probe_action("commit")
        return probe_action("commit")
    return probe_action("commit")


def run_one(world_class, family, seed, episode):
    world=world_class(family,episode,seed)
    first=normalize_public_observation(world.reset())
    current_turn=0
    event_counts={"observed-effect":0,"observed-confirmation":0,
                  "incidental-observation":0}
    normal_hash=hashlib.sha256(b"ITD01_R6_NEUTRAL_EVENTS").digest()

    def public_step(action_dict):
        nonlocal current_turn, normal_hash
        # The script receives a PUBLIC result ONLY; the actual world object
        # never crosses the scripted agent's step data interface.
        raw=world.step(action_dict)
        normalized=public_transition_from_step(raw)
        obs=normalized["observation"]
        current_turn+=1
        for e in obs["events"]:
            event_counts[e["type"]]+=1
        normal_hash=hashlib.sha256(normal_hash + canonical(normalized)).digest()
        return normalized
    last=neutral_scripted_public_policy(first,public_step)
    receipt=world.public_trace_receipt()
    if (not receipt["done"] or receipt["steps"]!=current_turn or
        receipt["steps"]>41 or receipt["scientific_first_use"]):
        raise RuntimeError("ITD01_R6_PUBLIC_TRACE_CUSTODY_OR_ACTION_LIMIT")
    return {"reward":last["reward"],"steps":receipt["steps"],
            "public_original_trace_sha256":receipt["trace_head_sha256"],
            "public_normalized_trace_sha256":normal_hash.hex(),
            "neutral_events_count":event_counts}


def evaluate(count=80):
    output={}
    for world_name,world_class in (("R3_two_stage",PublicCausalDevWorld),
                                    ("R5_three_stage",R5CausalWorld)):
        branch={}
        for fam_idx,family in enumerate(PUBLIC_FAMILIES):
            results=[run_one(world_class,family,
                             610000+fam_idx*100000+i,
                             f"DEV-R6-{world_name}-{fam_idx}-{i}")
                     for i in range(count)]
            branch[family]={
                "tasks":count,
                "goal_success":sum(o["reward"] for o in results)/count,
                "mean_actions":sum(o["steps"] for o in results)/count,
                "max_actions":max(o["steps"] for o in results),
                "observed_event_type_totals":{kind:sum(o["neutral_events_count"][kind]
                                                      for o in results)
                                               for kind in ("observed-effect",
                                                            "observed-confirmation",
                                                            "incidental-observation")},
                "public_reward_hash":hashlib.sha256(canonical([o["reward"] for o in results])).hexdigest(),
                "neutral_public_trace_heads_hash":hashlib.sha256(canonical(
                    [o["public_normalized_trace_sha256"] for o in results])).hexdigest(),
            }
        output[world_name]=branch
    return output


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--smoke",action="store_true")
    args=p.parse_args()
    s=time.process_time()
    results=evaluate(8 if args.smoke else 80)
    report={
        "schema":"itd01.r6.neutral-event-public-only-qualification.v1",
        "evidence_class":"DEVELOPMENT_ENGINEERING_NOT_HIDDEN_SCIENCE",
        "scientific_first_use":False,
        "native_wingless_trained":False,
        "native_yggdrasil_trained":False,
        "model":"UNTRAINED_SHARED_PUBLIC_SCRIPTED_DIAGNOSTIC_ONLY",
        "external_authority":"NONE_DEV_ONLY",
        "worlds":results,
        "source_free_cpu_seconds":round(time.process_time()-s,6),
        "peak_shared_process_rss_bytes":peak_rss_bytes()}
    print(json.dumps(report,sort_keys=True,separators=(",",":")))
    if any(v["goal_success"]<.8 for family in results.values()
           for v in family.values()):
        raise SystemExit("R6_GENERIC_PUBLIC_NEUTRAL_SCRIPTED_CONTROL_NO_GO")


if __name__=="__main__":
    main()
