#!/usr/bin/env python3
"""MG53: full authentic MG52 original-source goal-credit replay, read-only.

The original frozen MG52 actor is imported and replayed against exact *own
selected* public source events. No Farama env or native model is run.
The diagnostic makes NO off-policy or counterfactual performance claims.
"""
from __future__ import annotations
import argparse,collections,gc,hashlib,json,math,subprocess,zipfile
from pathlib import Path
from mg52_goal_relevant_eligibility_dev import (
    GoalRelevantEligibility,OriginalDoorMemory,
    compact_context,public_exact_target_front)

HERE=Path(__file__).resolve().parent
PREREG=HERE/"mg53_mg52_goal_credit_audit_prereg.json"
PARENT="1e0e911aff669983bd12e0fc469be7898e1a6f98"
FREEZE="33ba5070007d5c9b41b2d43cdc081f535d7d1c12"
ZIP_SHA="67d9e6cff9728ae9b3298f7653ffd05edcc6838d1d956fbd6e8cf542527cc9b6"
SOURCE_SHA="66ba8e5f456addd882c292720d0b4d418c460d4937f8d4c21acb5114688f8c88"
FAMILIES=("MiniGrid-KeyCorridorS3R2-v0",
          "MiniGrid-KeyCorridorS4R3-v0",
          "MiniGrid-ObstructedMaze-1Dl-v0")
SEEDS=((1081101,1081103,1081107),
       (1081201,1081203,1081207),
       (1081301,1081303,1081307))
ON="mg52_original_goal_relevant_eligibility_enabled"
OFF="mg52_original_goal_relevant_eligibility_disabled"

class HashWriter:
    def __init__(self):self.h=hashlib.sha256()
    def write(self,s):self.h.update(s.encode("ascii"))
def digest(x):
    writer=HashWriter()
    json.dump(x,writer,sort_keys=True,separators=(",",":"),
              ensure_ascii=True,allow_nan=False)
    return writer.h.hexdigest()
def git(*args):
    return subprocess.run(["git",*args],cwd=HERE.parents[1],
        capture_output=True,text=True,check=False)
def frozen():
    p=json.loads(PREREG.read_text(encoding="utf8"))
    v=p["parent"];c=p["cohort"]
    if (p["schema"]!="itd02.mg53.original-MG52-selected-goal-credit-cold-replay-retrospective.v1"
        or p["phase"]!="DIAGNOSTIC_RULES_FROZEN_BEFORE_EXECUTABLE_OR_ARCHIVED_SOURCE_INSPECTION"
        or v["mg52_exact_head"]!=PARENT
        or v["mg52_actions_run"]!=40973373359
        or v["mg52_artifact"]!=12941646119
        or v["artifact_zip_sha256"]!=ZIP_SHA
        or v["canonical_original_source_sha256"]!=SOURCE_SHA
        or v["original_negative"]!="MG52_GOAL_RELEVANT_ELIGIBILITY_DEV_TASK_BENEFIT_NOT_SUPPORTED_NO_SCIENCE"
        or v["original_episodes"]!=198 or v["original_source_actions"]!=36754
        or tuple(c["families"])!=FAMILIES
        or tuple(map(tuple,c["exposed_dev_seeds"]))!=SEEDS
        or tuple(c["actor_roles"])!=(ON,OFF)
        or c["all_control_roles"]!=22
        or c["expected_actor_trace_episodes"]!=18
        or c["expected_original_world_episodes"]!=198
        or c["expected_original_source_actions"]!=36754
        or c["original_world_new_actions"]!=0
        or p["classification"]["pass"]!="MG53_IMMUTABLE_MG52_GOAL_CREDIT_REPLAY_AND_CAUSE_BOUNDARY_DIAGNOSTIC_PASS_NO_SCIENCE"
        or not all(p["prohibitions"].values())):
        raise ValueError("MG53_FROZEN_MG52_ORIGINAL_METRIC_CUSTODY_DRIFT")
    for sha in (PARENT,FREEZE):
        if git("merge-base","--is-ancestor",sha,"HEAD").returncode:
            raise ValueError("MG53_METRIC_FREEZE_NOT_ANCESTOR")
    changes=git("diff","--name-only",PARENT,"HEAD")
    allowed={".github/workflows/itd02-mg53-mg52-goal-credit-replay.yml",
             "research/lcrm01/mg53_mg52_goal_credit_audit_prereg.json",
             "research/lcrm01/mg53_mg52_goal_credit_audit.py"}
    if changes.returncode or set(changes.stdout.splitlines())!=allowed:
        raise ValueError("MG53_OUTSIDE_IMMUTABLE_READONLY_SOURCE_SCOPE")
    if git("diff","--quiet",PARENT,"HEAD","--",
           "research/lcrm01/mg52_goal_relevant_eligibility_dev.py").returncode:
        raise ValueError("MG53_ORIGINAL_MG52_POLICY_NOT_UNCHANGED")
    return p

def preflight():
    p=frozen()
    before={"image":[[[1,0,0] for j in range(7)] for i in range(7)],
            "direction":0,"mission":"pick up the red box"}
    after=json.loads(json.dumps(before))
    after["image"][3][4]=[7,0,0]
    from mg52_goal_relevant_eligibility_dev import observed_goal_signal
    if observed_goal_signal(before,0,after,0.0,False)!=2:
        raise ValueError("MG53_FROZEN_ORIGINAL_GOAL_CREDIT_METRIC_NOT_IDENTICAL")
    for enabled in (True,False):
        actor=GoalRelevantEligibility(enabled)
        action=actor.choose(before)
        actor.observe_selected(before,action,after,0.0,False)
        state=actor.checkpoint()
        if (GoalRelevantEligibility.restore(state).checkpoint()!=state
            or actor.source_goal_signals!=1
            or actor.credit_assignments!=1):
            raise ValueError("MG53_UNCHANGED_SOURCE_ONLY_COLD_ACTOR_SELFTEST_FAIL")
    print("MG53_FROZEN_DUAL_HOST_READONLY_GOAL_CREDIT_SOURCE_PREFLIGHT_PASS")
    return p

def predecision(actor,before):
    # Read only: parent scorer is invoked on a separately cold-restored actor.
    # It can affect the disposable shadow's pending selection and counters,
    # never the real source replay actor.
    copy=GoalRelevantEligibility.restore(actor.checkpoint())
    parent=OriginalDoorMemory.choose(copy,before)
    context=compact_context(before)
    front=before["image"][3][5]
    steerable=(actor.phase=="seek" and parent in (0,1,2)
               and public_exact_target_front(before) is None)
    choices=(0,1,2) if front[0] not in (2,4,5,6,7) else (0,1)
    def sample(a):
        return actor.memory.get(context+"|"+str(a),[0,0.0])
    def mean(a):
        n,credit=sample(a)
        return credit/(n+2)
    support=[a for a in choices if sample(a)[0]>=2]
    best=max(support,key=lambda a:(mean(a),a==parent,-a)) if support else None
    alt=best is not None and best!=parent
    gap=(mean(best)-mean(parent)) if alt else None
    has_credit=any(sample(a)[1]>0 for a in (0,1,2))
    return {"parent":parent,"steerable":steerable,
        "source_abstract":context,
        "current_public_sha":digest(before),
        "same_context_prior_samples":sum(sample(a)[0] for a in (0,1,2)),
        "steerable_action_supported":len(support)>0,
        "has_any_positive_credit":has_credit,
        "supported_alt":alt,
        "alternative_advantage":gap,
        "frozen_threshold_satisfied":bool(steerable and alt and gap>=0.5)}

def replay(source,p):
    if (source["schema"]!="itd02.mg52.original-source-goal-consequence-eligibility.dev.v1"
        or source["classification"]!=p["parent"]["original_negative"]
        or source["original_selected_action_count"]!=36754
        or source["exposed_transfer_DEV_seeds"]!=p["cohort"]["exposed_dev_seeds"]
        or source["source_original_Farama"]!="7f5853792ea7f04f75614661006d87fcf949f26d"
        or source["unchanged_mg44_source_blob_sha1"]!=p["sources"]["original_mg44_source_blob"]
        or source["scientific_first_use"] is not False
        or source["independent_sealed_scientific_witness"] is not False
        or source["native_models_or_controllers_modified"] is not False
        or source["native_full_compute_energy_parity_qualified"] is not False
        or source["zero_external_actions"] is not True):
        raise ValueError("MG53_ORIGINAL_MG52_SOURCE_SCIENCE_CUSTODY_CHANGED")
    rows=source["original_198_episodes"];roles=p["cohort"]["all_control_roles"]
    if len(rows)!=198:
        raise ValueError("MG53_ORIGINAL_ROLE_EPISODES_INCOMPLETE")
    expected={(f,role,seed) for f,sd in zip(FAMILIES,SEEDS)
              for role in source["per_family_per_role"][f] for seed in sd}
    if len(expected)!=198 or any(
        len(source["per_family_per_role"][f])!=roles for f in FAMILIES):
        raise ValueError("MG53_EXACT_ORIGINAL_FAMILY_ROLE_COHORT_NOT_22")
    seen=set();original_actions=0
    original_actor={};family_contexts=collections.defaultdict(lambda:collections.defaultdict(set))
    episode_receipts=[]
    grouped=collections.defaultdict(collections.Counter)
    for ep in rows:
        identity=(ep["family"],ep["role"],ep["seed_dev_exposed"])
        if identity not in expected or identity in seen:
            raise ValueError("MG53_ORIGINAL_SOURCE_ROLE_IDENTITY_DUPLICATE_OR_INVALID")
        seen.add(identity)
        events=ep["source_events"]
        if (not 1<=len(events)<=192
            or len(events)!=ep["original_source_actions"]
            or digest(events)!=ep["source_events_sha256"]
            or digest(events[0]["before"])!=ep["public_start_sha256"]):
            raise ValueError("MG53_ORIGINAL_EPISODE_SOURCE_EVENTS_SHA_MISMATCH")
        original_actions+=len(events)
        # All source actors must satisfy independent public-chain custody.
        positive=0
        for i,e in enumerate(events,1):
            if (e["index"]!=i or e["external_actions"]!=0
                or type(e["action"]) is not int or not 0<=e["action"]<=6
                or e["mission"]!=ep["original_public_mission"]
                or digest(e["before"])!=e["before_sha256"]
                or digest(e["after"])!=e["after_sha256"]
                or (i>1 and e["before_sha256"]!=events[i-2]["after_sha256"])):
                raise ValueError("MG53_ORIGINAL_SELECTED_EVENT_CHAIN_FAIL")
            positive+=int(e["reward"]>0 and e["terminated"] is True)
        if positive!=ep["original_terminal_goal_rewards"]:
            raise ValueError("MG53_ORIGINAL_REWARD_CUSTODY_DRIFT")
        if ep["role"] not in (ON,OFF):
            continue
        role=ep["role"];family=ep["family"]
        enabled=role==ON
        actor=original_actor.get((family,role))
        if actor is None:actor=GoalRelevantEligibility(enabled)
        if actor.eligibility_enabled is not enabled:
            raise ValueError("MG53_ORIGINAL_MATCHED_ABLATION_ROLE_CHANGED")
        if actor.total!=ep["prior_selected_source_samples"]:
            raise ValueError("MG53_ORIGINAL_PRIOR_SELECTED_SAMPLE_COLD_FAMILY_MISMATCH")
        actor.begin_episode()
        start={"signals":actor.source_goal_signals,
               "assignments":actor.credit_assignments,
               "opportunities":actor.value_opportunities,
               "overrides":actor.value_overrides}
        stats=collections.Counter()
        for e in events:
            before,after=e["before"],e["after"]
            selected=e["action"]
            info=predecision(actor,before) if enabled else None
            if enabled:
                stats["total_decisions"]+=1
                stats["parent_steerable"]+=int(info["steerable"])
                stats["has_same_context_sample"]+=int(info["same_context_prior_samples"]>0)
                stats["has_any_positive_credit"]+=int(info["has_any_positive_credit"])
                stats["has_steerable_supported_action"]+=int(
                    info["steerable"] and info["steerable_action_supported"])
                stats["has_positive_credit_in_steerable"]+=int(
                    info["steerable"] and info["has_any_positive_credit"])
                stats["has_supported_alternative"]+=int(
                    info["steerable"] and info["supported_alt"])
                if info["steerable"] and info["supported_alt"]:
                    gap=info["alternative_advantage"]
                    if gap<=0:stats["alt_gap_le_zero"]+=1
                    elif gap<0.25:stats["alt_gap_0_to_quarter"]+=1
                    elif gap<0.5:stats["alt_gap_quarter_to_half"]+=1
                    else:stats["alt_gap_at_least_half"]+=1
                stats["frozen_threshold_satisfied"]+=int(info["frozen_threshold_satisfied"])
                family_contexts[(family,role)][info["source_abstract"]].add(
                    info["current_public_sha"])
            proposed=actor.choose(before)
            if proposed!=selected:
                raise ValueError("MG53_UNCHANGED_MG52_OWN_SELECTED_POLICY_REPLAY_DIVERGED")
            actor.observe_selected(before,selected,after,e["reward"],e["terminated"])
        state=actor.checkpoint()
        if (actor.total!=ep["selected_source_samples_after"]
            or hashlib.sha256(state).hexdigest()!=ep["checkpoint_sha256"]
            or actor.value_overrides-start["overrides"]!=
               ep["source_goal_eligibility_overrides"]
            or actor.value_opportunities-start["opportunities"]!=
               ep["source_goal_value_opportunities"]
            or actor.source_goal_signals-start["signals"]!=
               ep["source_goal_relevance_events"]
            or actor.credit_assignments-start["assignments"]!=
               ep["source_goal_credit_assignments"]):
            raise ValueError("MG53_ORIGINAL_SOURCE_COLD_CHECKPOINT_CREDIT_REPLAY_MISMATCH")
        if GoalRelevantEligibility.restore(state).checkpoint()!=state:
            raise ValueError("MG53_SOURCE_COLD_MEMORY_NOT_RESTORED")
        original_actor[(family,role)]=GoalRelevantEligibility.restore(state)
        stats.update({
            "source_actions":len(events),
            "source_relevance_events":ep["source_goal_relevance_events"],
            "credit_assignments":ep["source_goal_credit_assignments"],
            "original_positive_goals":ep["original_terminal_goal_rewards"],
            "selected_value_opportunities":ep["source_goal_value_opportunities"],
            "real_source_policy_overrides":ep["source_goal_eligibility_overrides"]})
        grouped[(family,role)].update(stats)
        episode_receipts.append({"family":family,"role":role,"seed":ep["seed_dev_exposed"],
                                 "diagnostic":dict(stats),
                                 "source_checkpoint_sha256":ep["checkpoint_sha256"],
                                 "source_episode_events_sha256":ep["source_events_sha256"]})
    if seen!=expected or original_actions!=36754 or len(episode_receipts)!=18:
        raise ValueError("MG53_ALL_SOURCE_OR_ACTOR_EPISODE_DENOMINATORS_CHANGED")
    per_family={}
    for family in FAMILIES:
        per_family[family]={}
        for role in (ON,OFF):
            st=grouped[(family,role)]
            prior=source["per_family_per_role"][family][role]
            if st["source_actions"]!=prior["actions"] or st["original_positive_goals"]!=prior["positive_goal_episodes"]:
                raise ValueError("MG53_ORIGINAL_AGGREGATE_GOALS_OR_ACTIONS_DRIFT")
            memory=original_actor[(family,role)].memory
            retained=[v for v in memory.values() if v[1]>0]
            steer=[v for k,v in memory.items() if k.endswith(("|0","|1","|2"))]
            observed=family_contexts[(family,role)]
            per_family[family][role]={
                **dict(st),
                "learned_context_action_keys":len(memory),
                "positive_credit_keys":len(retained),
                "positive_credit_steer_keys":sum(v[1]>0 for v in steer),
                "total_credit_mass":round(sum(v[1] for v in memory.values()),8),
                "abstract_contexts_observed":len(observed),
                "abstract_contexts_with_multiple_public_views":
                    sum(len(hashes)>1 for hashes in observed.values()),
                "unique_original_public_contexts":
                    len({h for hashes in observed.values() for h in hashes})}
    if (sum(per_family[f][ON]["source_relevance_events"] for f in FAMILIES)!=10
        or sum(per_family[f][ON]["credit_assignments"] for f in FAMILIES)!=80
        or sum(per_family[f][ON]["selected_value_opportunities"] for f in FAMILIES)!=641
        or sum(per_family[f][ON]["real_source_policy_overrides"] for f in FAMILIES)!=0
        or sum(per_family[f][ON]["original_positive_goals"] for f in FAMILIES)!=3
        or sum(per_family[f][OFF]["original_positive_goals"] for f in FAMILIES)!=3):
        raise ValueError("MG53_ORIGINAL_NEGATIVE_AND_SPARSE_CREDIT_CONTROL_DRIFT")
    return {
        "classification":"MG53_IMMUTABLE_MG52_GOAL_CREDIT_REPLAY_AND_CAUSE_BOUNDARY_DIAGNOSTIC_PASS_NO_SCIENCE",
        "verified_total_198_original_role_episodes":len(rows),
        "verified_original_selected_actions":original_actions,
        "original_world_new_actions":0,
        "per_family_original_actor_replay":per_family,
        "per_episode_original_actor_replay":episode_receipts,
        "caveat":"Original selected behavior replay only; source-public abstraction compression does not prove physical state aliasing. No off-policy counterfactual trajectories."
    }

def run(archive,out):
    p=preflight()
    with archive.open("rb") as f:
        if hashlib.file_digest(f,"sha256").hexdigest()!=ZIP_SHA:
            raise ValueError("MG53_IMMUTABLE_GITHUB_ORIGINAL_ZIP_SHA_INVALID")
    first=None;fingerprints=[]
    with zipfile.ZipFile(archive) as z:
        expected={"comparison.log","first.json","second.json","first.log",
            "second.log","first-resources.json","second-resources.json",
            "mg33c-synthetic.json"}
        if set(z.namelist())!=expected:
            raise ValueError("MG53_ORIGINAL_ARTIFACT_LAYOUT_CHANGED")
        if SOURCE_SHA not in z.read("comparison.log").decode("utf8"):
            raise ValueError("MG53_ORIGINAL_INDEPENDENT_PROCESS_COMPARISON_MISSING")
        for name in ("first.json","second.json"):
            with z.open(name) as f:record=json.load(f)
            if (record.get("canonical_source_sha256")!=SOURCE_SHA
                or digest(record["source"])!=SOURCE_SHA):
                raise ValueError("MG53_ORIGINAL_FULL_CANONICAL_SOURCE_HASH_INVALID")
            result=replay(record["source"],p)
            fingerprints.append(digest(result))
            if first is None:first=result
            del result,record;gc.collect()
        if len(set(fingerprints))!=1:
            raise ValueError("MG53_DUAL_PROCESS_FULL_STATE_REPLAY_DIVERGENCE")
        for name in ("first-resources.json","second-resources.json"):
            with z.open(name) as f:res=json.load(f)
            if (res["original_source_sha256"]!=SOURCE_SHA
                or len(res["records"])!=198):
                raise ValueError("MG53_ORIGINAL_SOURCE_RESOURCE_ASSOCIATION_MISMATCH")
    receipt={
        "schema":"itd02.mg53.original-MG52-goal-credit-source-diagnostic.v1",
        "classification":first["classification"],
        "source_SHA256":SOURCE_SHA,"archive_ZIP_SHA256":ZIP_SHA,
        "source_processes_independent_and_identical":2,
        "original_MG52_science_negative_preserved":True,
        "scientific_first_use":False,
        "diagnostic":first}
    receipt["canonical_audit_sha256"]=digest(receipt)
    out.write_text(json.dumps(receipt,sort_keys=True,indent=2)+"\n",encoding="utf8")
    for family in FAMILIES:
        print("MG53_GOAL_CREDIT_CAUSE_BOUNDARY",json.dumps({
            "family":family,
            "enabled":first["per_family_original_actor_replay"][family][ON],
            "disabled":first["per_family_original_actor_replay"][family][OFF]},
            sort_keys=True))
    print("MG53_INDEPENDENT_COMPLETE_ORIGINAL_SOURCE_AND_COLD_ACTOR_REPLAY_PASS",SOURCE_SHA)
    print("MG53_CANONICAL_GOAL_CREDIT_AUDIT_SHA256",receipt["canonical_audit_sha256"])
    print("MG53_FROZEN_DIAGNOSTIC_CLASSIFICATION",receipt["classification"])

def main():
    a=argparse.ArgumentParser()
    a.add_argument("--preflight",action="store_true")
    a.add_argument("--archive",type=Path)
    a.add_argument("--output",type=Path)
    q=a.parse_args()
    if q.preflight:preflight();return
    if q.archive is None or q.output is None:
        a.error("--archive and --output required")
    run(q.archive,q.output)
if __name__=="__main__":main()
