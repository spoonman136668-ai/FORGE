#!/usr/bin/env python3
"""MG55: full authentic MG54 original-source goal-credit replay, read-only.

The original frozen MG54 actor is imported and replayed against exact *own
selected* public source events. No Farama env or native model is run.
The diagnostic makes NO off-policy or counterfactual performance claims.
"""
from __future__ import annotations
import argparse,collections,gc,hashlib,json,math,subprocess,zipfile
from pathlib import Path
from mg54_public_pooled_goal_credit_dev import (
    PooledGoalCredit,OriginalDoorMemory,
    pooled_context,public_exact_target_front)

HERE=Path(__file__).resolve().parent
PREREG=HERE/"mg55_mg54_pooled_credit_audit_prereg.json"
PARENT="d14ed35e79ba85e3abb747803fd4c6a5ee5b66c9"
FREEZE="860a4cc66054df7f96e846815fe925e387789bc2"
ZIP_SHA="ef5a7882dd0775754c359d68da1e7248f39a50f90a55241ccb0757548ca480b1"
SOURCE_SHA="adcb892c5f69979896a9394725a29c7fbd285cd42658d04e71ac42deabd76382"
FAMILIES=("MiniGrid-KeyCorridorS3R2-v0",
          "MiniGrid-KeyCorridorS4R3-v0",
          "MiniGrid-ObstructedMaze-1Dl-v0")
SEEDS=((1101101,1101103,1101107),
       (1101201,1101203,1101207),
       (1101301,1101303,1101307))
ON="mg54_public_context_pooled_goal_credit_enabled"
OFF="mg54_public_context_pooled_goal_credit_disabled"

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
    q=p["parent"];c=p["cohort"];ex=p["expected"]
    if (p["schema"]!="itd02.mg55.original-mg54-pooled-goal-credit-retrospective-replay.v1"
        or p["phase"]!="FROZEN_METRICS_BEFORE_AUDIT_EXECUTABLE_OR_ARCHIVE_INSPECTION"
        or q["exact_head"]!=PARENT
        or q["original_run"]!=40978021069 or q["original_artifact"]!=12944275150
        or q["zip_sha256"]!=ZIP_SHA or q["full_source_sha256"]!=SOURCE_SHA
        or q["negative"]!="MG54_POOLED_PUBLIC_GOAL_CREDIT_TASK_BENEFIT_NOT_SUPPORTED_NO_SCIENCE"
        or q["episodes"]!=216 or q["source_actions"]!=37047
        or tuple(c["families"])!=FAMILIES
        or tuple(map(tuple,c["exposed_seeds"]))!=SEEDS
        or tuple(c["roles"])!=(ON,OFF)
        or c["all_roles_per_family"]!=24
        or c["actor_episodes"]!=18
        or c["expected_original_episodes"]!=216
        or c["expected_original_source_actions"]!=37047
        or c["new_env_actions"]!=0
        or ex!={"signal_events":11,"credit_assignments":88,
                "value_opportunities":379,"actual_overrides":0,
                "positive_goals_on":4,"positive_goals_off":4}
        or p["classification"]["pass"]!="MG55_MG54_IMMUTABLE_POOLED_CREDIT_EXACT_REPLAY_DIAGNOSTIC_PASS_NO_SCIENCE"
        or not all(p["prohibitions"].values())):
        raise ValueError("MG55_FROZEN_SOURCE_OR_DIAGNOSTIC_CONTRACT_DRIFT")
    for sha in (PARENT,FREEZE):
        if git("merge-base","--is-ancestor",sha,"HEAD").returncode:
            raise ValueError("MG55_FREEZE_NOT_BEFORE_EXECUTABLE")
    diff=git("diff","--name-only",PARENT,"HEAD")
    allowed={".github/workflows/itd02-mg55-mg54-pooled-credit-replay.yml",
             "research/lcrm01/mg55_mg54_pooled_credit_audit_prereg.json",
             "research/lcrm01/mg55_mg54_pooled_credit_audit.py"}
    if diff.returncode or set(diff.stdout.splitlines())!=allowed:
        raise ValueError("MG55_ISOLATED_READONLY_RESEARCH_SCOPE_VIOLATED")
    if git("diff","--quiet",PARENT,"HEAD","--",
           "research/lcrm01/mg54_public_pooled_goal_credit_dev.py").returncode:
        raise ValueError("MG55_ORIGINAL_MG54_ACTOR_CHANGED")
    return p

def preflight():
    p=frozen()
    before={"image":[[[1,0,0] for j in range(7)] for i in range(7)],
            "direction":0,"mission":"pick up the red box"}
    after=json.loads(json.dumps(before))
    after["image"][3][4]=[7,0,0]
    from mg54_public_pooled_goal_credit_dev import original_goal_signal
    if original_goal_signal(before,0,after,0.0,False)!=2:
        raise ValueError("MG55_FROZEN_SOURCE_PUBLIC_GOAL_EFFECT_CHANGED")
    for steering in (True,False):
        actor=PooledGoalCredit(steering)
        action=actor.choose(before)
        actor.observe_selected(before,action,after,0.0,False)
        state=actor.checkpoint()
        if (PooledGoalCredit.restore(state).checkpoint()!=state
            or actor.pooled_signal_events!=1
            or actor.pooled_credit_assignments!=1):
            raise ValueError("MG55_UNCHANGED_POOLED_COLD_ACTOR_SELFTEST_FAIL")
    print("MG55_FROZEN_DUAL_OS_READONLY_POOLED_GOAL_SOURCE_PREFLIGHT_PASS")
    return p

def predecision(actor,before):
    # Immutable original actor state; parent chosen only on cold-restored
    # disposable shadow, no new environment action or policy intervention.
    copy=PooledGoalCredit.restore(actor.checkpoint())
    parent=OriginalDoorMemory.choose(copy,before)
    context=pooled_context(before)
    front=before["image"][3][5]
    structural=(actor.phase=="seek" and parent in (0,1,2)
                and public_exact_target_front(before) is None)
    signal=actor.pooled_signal_events>=1
    steerable=structural and signal
    choices=(0,1,2) if front[0] not in (2,4,5,6,7) else (0,1)
    def sample(a):return actor.pooled.get(context+"|"+str(a),[0,0.0])
    def mean(a):
        n,credit=sample(a)
        return credit/(n+2)
    support=[a for a in choices if sample(a)[0]>=2]
    best=max(support,key=lambda a:(mean(a),a==parent,-a)) if support else None
    alt=best is not None and best!=parent
    advantage=mean(best)-mean(parent) if alt else None
    positive=sum(sample(a)[1]>0 for a in (0,1,2))
    return {"parent":parent,"source_abstract":context,
            "public_before_sha256":digest(before),
            "structurally_steerable":structural,
            "original_signal_available":signal,
            "steerable":steerable,
            "same_context_prior_samples":sum(sample(a)[0] for a in (0,1,2)),
            "eligible_supported_action":bool(support),
            "supported_alt":alt,
            "alternative_advantage":advantage,
            "positive_credit_steering_action_count":positive,
            "best_action":best,
            "frozen_threshold_satisfied":bool(steerable and alt and advantage>=0.125)}

def replay(source,p):
    if (source["schema"]!="itd02.mg54.original-source-public-pooled-goal-eligibility.dev.v1"
        or source["classification"]!=p["parent"]["negative"]
        or source["original_selected_action_count"]!=37047
        or source["exposed_transfer_DEV_seeds"]!=p["cohort"]["exposed_seeds"]
        or source["source_original_Farama"]!="7f5853792ea7f04f75614661006d87fcf949f26d"
        or source["unchanged_mg44_source_blob_sha1"]!=p["source"]["mg44_blob"]
        or source["scientific_first_use"] is not False
        or source["independent_sealed_scientific_witness"] is not False
        or source["native_models_or_controllers_modified"] is not False
        or source["native_full_compute_energy_parity_qualified"] is not False
        or source["zero_external_actions"] is not True):
        raise ValueError("MG55_ORIGINAL_MG54_SOURCE_SCIENCE_CUSTODY_CHANGED")
    rows=source["original_216_episodes"];roles=p["cohort"]["all_roles_per_family"]
    if len(rows)!=216:
        raise ValueError("MG55_ORIGINAL_ROLE_EPISODES_INCOMPLETE")
    expected={(f,role,seed) for f,sd in zip(FAMILIES,SEEDS)
              for role in source["per_family_per_role"][f] for seed in sd}
    if len(expected)!=216 or any(
        len(source["per_family_per_role"][f])!=roles for f in FAMILIES):
        raise ValueError("MG55_EXACT_ORIGINAL_FAMILY_ROLE_COHORT_NOT_24")
    seen=set();original_actions=0
    original_actor={};family_contexts=collections.defaultdict(lambda:collections.defaultdict(set))
    episode_receipts=[]
    grouped=collections.defaultdict(collections.Counter)
    for ep in rows:
        identity=(ep["family"],ep["role"],ep["seed_dev_exposed"])
        if identity not in expected or identity in seen:
            raise ValueError("MG55_ORIGINAL_SOURCE_ROLE_IDENTITY_DUPLICATE_OR_INVALID")
        seen.add(identity)
        events=ep["source_events"]
        if (not 1<=len(events)<=192
            or len(events)!=ep["original_source_actions"]
            or digest(events)!=ep["source_events_sha256"]
            or digest(events[0]["before"])!=ep["public_start_sha256"]):
            raise ValueError("MG55_ORIGINAL_EPISODE_SOURCE_EVENTS_SHA_MISMATCH")
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
                raise ValueError("MG55_ORIGINAL_SELECTED_EVENT_CHAIN_FAIL")
            positive+=int(e["reward"]>0 and e["terminated"] is True)
        if positive!=ep["original_terminal_goal_rewards"]:
            raise ValueError("MG55_ORIGINAL_REWARD_CUSTODY_DRIFT")
        if ep["role"] not in (ON,OFF):
            continue
        role=ep["role"];family=ep["family"]
        enabled=role==ON
        actor=original_actor.get((family,role))
        if actor is None:actor=PooledGoalCredit(enabled)
        if actor.steering_enabled is not enabled:
            raise ValueError("MG55_ORIGINAL_MATCHED_ABLATION_ROLE_CHANGED")
        if actor.total!=ep["prior_selected_source_samples"]:
            raise ValueError("MG55_ORIGINAL_PRIOR_SELECTED_SAMPLE_COLD_FAMILY_MISMATCH")
        actor.begin_episode()
        start={"signals":actor.pooled_signal_events,
               "assignments":actor.pooled_credit_assignments,
               "opportunities":actor.pooled_opportunities,
               "overrides":actor.pooled_overrides}
        stats=collections.Counter()
        for e in events:
            before,after=e["before"],e["after"]
            selected=e["action"]
            info=predecision(actor,before) if enabled else None
            if enabled:
                stats["total_decisions"]+=1
                stats["parent_structural_seek"]+=int(info["structurally_steerable"])
                stats["prior_task_signal_available"]+=int(info["original_signal_available"])
                stats["parent_structural_with_signal"]+=int(info["steerable"])
                stats["has_any_prior_sample"]+=int(info["same_context_prior_samples"]>0)
                stats["positive_credit_any_steer_action"]+=int(
                    info["positive_credit_steering_action_count"]>0)
                stats["supported_steer_action"]+=int(
                    info["steerable"] and info["eligible_supported_action"])
                stats["supported_alternative"]+=int(
                    info["steerable"] and info["supported_alt"])
                if info["steerable"] and info["supported_alt"]:
                    gap=info["alternative_advantage"]
                    if gap<=0:stats["gap_nonpositive"]+=1
                    elif gap<0.0625:stats["gap_0_to_sixteenth"]+=1
                    elif gap<0.125:stats["gap_sixteenth_to_eighth"]+=1
                    else:stats["gap_at_least_eighth"]+=1
                stats["frozen_threshold_satisfied"]+=int(
                    info["frozen_threshold_satisfied"])
                family_contexts[(family,role)][info["source_abstract"]].add(
                    info["public_before_sha256"])
            proposed=actor.choose(before)
            if proposed!=selected:
                raise ValueError("MG55_UNCHANGED_MG54_OWN_SELECTED_POLICY_REPLAY_DIVERGED")
            actor.observe_selected(before,selected,after,e["reward"],e["terminated"])
        state=actor.checkpoint()
        if (actor.total!=ep["selected_source_samples_after"]
            or hashlib.sha256(state).hexdigest()!=ep["checkpoint_sha256"]
            or actor.pooled_overrides-start["overrides"]!=
               ep["source_pooled_goal_overrides"]
            or actor.pooled_opportunities-start["opportunities"]!=
               ep["source_pooled_goal_opportunities"]
            or actor.pooled_signal_events-start["signals"]!=
               ep["source_pooled_goal_events"]
            or actor.pooled_credit_assignments-start["assignments"]!=
               ep["source_pooled_credit_assignments"]):
            raise ValueError("MG55_ORIGINAL_SOURCE_COLD_CHECKPOINT_CREDIT_REPLAY_MISMATCH")
        if PooledGoalCredit.restore(state).checkpoint()!=state:
            raise ValueError("MG55_SOURCE_COLD_MEMORY_NOT_RESTORED")
        original_actor[(family,role)]=PooledGoalCredit.restore(state)
        stats.update({
            "source_actions":len(events),
            "source_relevance_events":ep["source_pooled_goal_events"],
            "credit_assignments":ep["source_pooled_credit_assignments"],
            "original_positive_goals":ep["original_terminal_goal_rewards"],
            "selected_value_opportunities":ep["source_pooled_goal_opportunities"],
            "real_source_policy_overrides":ep["source_pooled_goal_overrides"]})
        grouped[(family,role)].update(stats)
        episode_receipts.append({"family":family,"role":role,"seed":ep["seed_dev_exposed"],
                                 "diagnostic":dict(stats),
                                 "source_checkpoint_sha256":ep["checkpoint_sha256"],
                                 "source_episode_events_sha256":ep["source_events_sha256"]})
    if seen!=expected or original_actions!=37047 or len(episode_receipts)!=18:
        raise ValueError("MG55_ALL_SOURCE_OR_ACTOR_EPISODE_DENOMINATORS_CHANGED")
    per_family={}
    for family in FAMILIES:
        per_family[family]={}
        for role in (ON,OFF):
            st=grouped[(family,role)]
            prior=source["per_family_per_role"][family][role]
            if st["source_actions"]!=prior["actions"] or st["original_positive_goals"]!=prior["positive_goal_episodes"]:
                raise ValueError("MG55_ORIGINAL_AGGREGATE_GOALS_OR_ACTIONS_DRIFT")
            memory=original_actor[(family,role)].pooled
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
    if (sum(per_family[f][ON]["source_relevance_events"] for f in FAMILIES)!=11
        or sum(per_family[f][ON]["credit_assignments"] for f in FAMILIES)!=88
        or sum(per_family[f][ON]["selected_value_opportunities"] for f in FAMILIES)!=379
        or sum(per_family[f][ON]["real_source_policy_overrides"] for f in FAMILIES)!=0
        or sum(per_family[f][ON]["original_positive_goals"] for f in FAMILIES)!=4
        or sum(per_family[f][OFF]["original_positive_goals"] for f in FAMILIES)!=4):
        raise ValueError("MG55_ORIGINAL_NEGATIVE_AND_SPARSE_CREDIT_CONTROL_DRIFT")
    return {
        "classification":"MG55_MG54_IMMUTABLE_POOLED_CREDIT_EXACT_REPLAY_DIAGNOSTIC_PASS_NO_SCIENCE",
        "verified_total_216_original_role_episodes":len(rows),
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
            raise ValueError("MG55_IMMUTABLE_GITHUB_ORIGINAL_ZIP_SHA_INVALID")
    first=None;fingerprints=[]
    with zipfile.ZipFile(archive) as z:
        expected={"comparison.log","first.json","second.json","first.log",
            "second.log","first-resources.json","second-resources.json",
            "mg33c-synthetic.json"}
        if set(z.namelist())!=expected:
            raise ValueError("MG55_ORIGINAL_ARTIFACT_LAYOUT_CHANGED")
        if SOURCE_SHA not in z.read("comparison.log").decode("utf8"):
            raise ValueError("MG55_ORIGINAL_INDEPENDENT_PROCESS_COMPARISON_MISSING")
        for name in ("first.json","second.json"):
            with z.open(name) as f:record=json.load(f)
            if (record.get("canonical_source_sha256")!=SOURCE_SHA
                or digest(record["source"])!=SOURCE_SHA):
                raise ValueError("MG55_ORIGINAL_FULL_CANONICAL_SOURCE_HASH_INVALID")
            result=replay(record["source"],p)
            fingerprints.append(digest(result))
            if first is None:first=result
            del result,record;gc.collect()
        if len(set(fingerprints))!=1:
            raise ValueError("MG55_DUAL_PROCESS_FULL_STATE_REPLAY_DIVERGENCE")
        for name in ("first-resources.json","second-resources.json"):
            with z.open(name) as f:res=json.load(f)
            if (res["original_source_sha256"]!=SOURCE_SHA
                or len(res["records"])!=216):
                raise ValueError("MG55_ORIGINAL_SOURCE_RESOURCE_ASSOCIATION_MISMATCH")
    receipt={
        "schema":"itd02.mg55.original-MG54-pooled-goal-credit-replay-diagnostic.v1",
        "classification":first["classification"],
        "source_SHA256":SOURCE_SHA,"archive_ZIP_SHA256":ZIP_SHA,
        "source_processes_independent_and_identical":2,
        "original_MG54_science_negative_preserved":True,
        "scientific_first_use":False,
        "diagnostic":first}
    receipt["canonical_audit_sha256"]=digest(receipt)
    out.write_text(json.dumps(receipt,sort_keys=True,indent=2)+"\n",encoding="utf8")
    for family in FAMILIES:
        print("MG55_GOAL_CREDIT_CAUSE_BOUNDARY",json.dumps({
            "family":family,
            "enabled":first["per_family_original_actor_replay"][family][ON],
            "disabled":first["per_family_original_actor_replay"][family][OFF]},
            sort_keys=True))
    print("MG55_INDEPENDENT_COMPLETE_ORIGINAL_SOURCE_AND_COLD_ACTOR_REPLAY_PASS",SOURCE_SHA)
    print("MG55_CANONICAL_GOAL_CREDIT_AUDIT_SHA256",receipt["canonical_audit_sha256"])
    print("MG55_FROZEN_DIAGNOSTIC_CLASSIFICATION",receipt["classification"])

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
