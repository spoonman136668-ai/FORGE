#!/usr/bin/env python3
"""MG55 original MG54 public-pooled goal-credit exact cold replay, no world steps.

This reads already exposed authentic original selected-action traces only.
It never imports gymnasium, runs Farama envs, or changes native agents.
"""
from __future__ import annotations
import argparse, collections, gc, hashlib, json, math, subprocess, zipfile
from pathlib import Path
from mg54_public_pooled_goal_credit_dev import (
    PooledGoalCredit, OriginalDoorMemory, pooled_context, public_exact_target_front,
)

HERE=Path(__file__).resolve().parent
PREREG=HERE/"mg55_mg54_pooled_credit_audit_prereg.json"
PARENT="d14ed35e79ba85e3abb747803fd4c6a5ee5b66c9"
FREEZE="07dbe11894f8858ad3ba358263d06128187cf5df"
ZIP_SHA="ef5a7882dd0775754c359d68da1e7248f39a50f90a55241ccb0757548ca480b1"
SOURCE_SHA="adcb892c5f69979896a9394725a29c7fbd285cd42658d04e71ac42deabd76382"
FAMILIES=("MiniGrid-KeyCorridorS3R2-v0","MiniGrid-KeyCorridorS4R3-v0",
          "MiniGrid-ObstructedMaze-1Dl-v0")
SEEDS=((1101101,1101103,1101107),(1101201,1101203,1101207),
       (1101301,1101303,1101307))
ON="mg54_public_context_pooled_goal_credit_enabled"
OFF="mg54_public_context_pooled_goal_credit_disabled"
PASS="MG55_IMMUTABLE_MG54_POOLED_CREDIT_EXACT_DECISION_REPLAY_PASS_NO_SCIENCE"

class HashWriter:
    def __init__(self): self.h=hashlib.sha256()
    def write(self,s): self.h.update(s.encode("ascii"))

def digest(x):
    h=HashWriter()
    json.dump(x,h,sort_keys=True,separators=(",",":"),ensure_ascii=True,allow_nan=False)
    return h.h.hexdigest()

def git(*args):
    return subprocess.run(["git",*args],cwd=HERE.parents[1],
                          text=True,capture_output=True,check=False)

def frozen():
    p=json.loads(PREREG.read_text(encoding="utf8"))
    v=p["parent"];c=p["cohort"];d=p["diagnostic"]
    if (p["schema"]!="itd02.mg55.original-mg54-pooled-credit-cold-actor-source-replay.v1"
        or p["phase"]!="RETROSPECTIVE_DIAGNOSTIC_FROZEN_BEFORE_EXECUTABLE_OR_NEW_FARAMA_ACTION"
        or v["mg54_exact_head"]!=PARENT or v["run"]!=40978021069
        or v["artifact"]!=12944275150
        or v["original_archive_zip_sha256"]!=ZIP_SHA
        or v["canonical_original_source_sha256"]!=SOURCE_SHA
        or v["original_classification"]!="MG54_POOLED_PUBLIC_GOAL_CREDIT_TASK_BENEFIT_NOT_SUPPORTED_NO_SCIENCE"
        or v["original_episodes"]!=216 or v["original_source_actions"]!=37047
        or tuple(c["families"])!=FAMILIES
        or tuple(map(tuple,c["exposed_dev_seeds"]))!=SEEDS
        or tuple(c["actor_roles"])!=(ON,OFF)
        or c["all_control_roles"]!=24
        or c["original_actor_trace_episodes"]!=18
        or c["expected_original_source_episodes"]!=216
        or c["expected_original_source_actions"]!=37047
        or c["expected_original_new_world_actions"]!=0
        or d["no_new_world"] is not True
        or p["classification"]["pass"]!=PASS
        or not all(p["prohibitions"].values())):
        raise ValueError("MG55_FROZEN_READONLY_SOURCE_PROTOCOL_DRIFT")
    for sha in (PARENT,FREEZE):
        if git("merge-base","--is-ancestor",sha,"HEAD").returncode:
            raise ValueError("MG55_PROSPECTIVE_AUDIT_FREEZE_NOT_ANCESTOR")
    allowed={".github/workflows/itd02-mg55-mg54-pooled-credit-replay.yml",
             "research/lcrm01/mg55_mg54_pooled_credit_audit_prereg.json",
             "research/lcrm01/mg55_mg54_pooled_credit_audit.py"}
    changes=git("diff","--name-only",PARENT,"HEAD")
    if changes.returncode or set(changes.stdout.splitlines())!=allowed:
        raise ValueError("MG55_UNAUTHORIZED_ORIGINAL_MODEL_OR_SCOPE_CHANGE")
    for filepath in ("research/lcrm01/mg54_public_pooled_goal_credit_dev.py",
                     "research/lcrm01/mg52_goal_relevant_eligibility_dev.py"):
        if git("diff","--quiet",PARENT,"HEAD","--",filepath).returncode:
            raise ValueError("MG55_ORIGINAL_POLICY_CHANGED")
    return p

def preflight():
    p=frozen()
    before={"image":[[[1,0,0] for _ in range(7)] for _ in range(7)],
            "direction":0,"mission":"pick up the red box"}
    after=json.loads(json.dumps(before))
    after["image"][3][4]=[7,0,0]
    from mg52_goal_relevant_eligibility_dev import observed_goal_signal
    if observed_goal_signal(before,0,after,0.0,False)!=2:
        raise ValueError("MG55_MG54_ORIGINAL_GOAL_SOURCE_SIGNAL_CHANGED")
    for enabled in (True,False):
        actor=PooledGoalCredit(enabled)
        selected=actor.choose(before)
        actor.observe_selected(before,selected,after,0.0,False)
        state=actor.checkpoint()
        if (PooledGoalCredit.restore(state).checkpoint()!=state
            or actor.pooled_signal_events!=1
            or actor.pooled_credit_assignments!=1):
            raise ValueError("MG55_ORIGINAL_COLD_ACTOR_SYNTHETIC_SELFTEST_FAILED")
    print("MG55_FROZEN_READONLY_CROSS_OS_PREFLIGHT_PASS_NO_SCIENCE")
    return p

def predecision(actor,before):
    copy=PooledGoalCredit.restore(actor.checkpoint())
    parent=OriginalDoorMemory.choose(copy,before)
    context=pooled_context(before)
    front=before["image"][3][5][0]
    parent_action_allowed=parent in (0,1,2)
    phase_ok=actor.phase=="seek"
    target_safe=public_exact_target_front(before) is None
    has_signal=actor.pooled_signal_events>=1
    eligible=(phase_ok and parent_action_allowed and target_safe and has_signal)
    choices=(0,1,2) if front not in (2,4,5,6,7) else (0,1)
    def sample(a): return actor.pooled.get(context+"|"+str(a),[0,0.0])
    def mean(a):
        n,credit=sample(a)
        return credit/(n+2)
    supported=[a for a in choices if sample(a)[0]>=2]
    best=max(supported,key=lambda a:(mean(a),a==parent,-a)) if supported else None
    alternative=best is not None and best!=parent
    gap=mean(best)-mean(parent) if alternative else None
    override=bool(eligible and alternative and gap>=0.125)
    return {"parent":parent,"phase_ok":phase_ok,
        "parent_navigation_action":parent_action_allowed,
        "target_not_exact_front":target_safe,
        "has_source_relevance_signal":has_signal,
        "eligible":eligible,"supported":bool(supported),
        "supported_alternative":alternative,
        "positive_context_credit":any(sample(a)[1]>0 for a in (0,1,2)),
        "same_context_source_trials":sum(sample(a)[0] for a in (0,1,2)),
        "gap":gap,"frozen_override_expected":override,
        "public_context":context,"public_before_sha":digest(before)}

def replay(source,p):
    if (source["schema"]!="itd02.mg54.original-source-public-pooled-goal-eligibility.dev.v1"
        or source["classification"]!=p["parent"]["original_classification"]
        or source["original_selected_action_count"]!=37047
        or source["exposed_transfer_DEV_seeds"]!=p["cohort"]["exposed_dev_seeds"]
        or source["source_original_Farama"]!="7f5853792ea7f04f75614661006d87fcf949f26d"
        or source["unchanged_mg44_source_blob_sha1"]!="2f93b9b5227d97d318cf5c05544f85c303496da7"
        or source["scientific_first_use"] is not False
        or source["independent_sealed_scientific_witness"] is not False
        or source["zero_external_actions"] is not True
        or source["native_models_or_controllers_modified"] is not False):
        raise ValueError("MG55_ORIGINAL_WORLD_SOURCE_BOUNDARY_CHANGED")
    rows=source["original_216_episodes"]
    if len(rows)!=216:raise ValueError("MG55_SOURCE_EPISODE_COHORT_INCOMPLETE")
    expected={(f,role,seed)
              for f,seeds in zip(FAMILIES,SEEDS)
              for role in source["per_family_per_role"][f] for seed in seeds}
    if len(expected)!=216 or any(len(source["per_family_per_role"][f])!=24 for f in FAMILIES):
        raise ValueError("MG55_ORIGINAL_24_ROLE_COHORT_CHANGED")
    seen=set();actions=0
    actors={}
    per_episode=[]
    grouped=collections.defaultdict(collections.Counter)
    contexts=collections.defaultdict(lambda:collections.defaultdict(set))
    semantics={}
    for ep in rows:
        identity=(ep["family"],ep["role"],ep["seed_dev_exposed"])
        if identity not in expected or identity in seen:
            raise ValueError("MG55_ORIGINAL_ACTOR_ID_DUPLICATE_OR_MISSING")
        seen.add(identity)
        events=ep["source_events"]
        if (len(events)!=ep["original_source_actions"]
            or not 1<=len(events)<=192
            or digest(events)!=ep["source_events_sha256"]
            or digest(events[0]["before"])!=ep["public_start_sha256"]):
            raise ValueError("MG55_EPISODE_SELECTED_EVENTS_SHA_INVALID")
        actions+=len(events)
        positive=0
        for i,e in enumerate(events,1):
            if (e["index"]!=i or e["external_actions"]!=0
                or type(e["action"]) is not int or not 0<=e["action"]<=6
                or e["mission"]!=ep["original_public_mission"]
                or digest(e["before"])!=e["before_sha256"]
                or digest(e["after"])!=e["after_sha256"]
                or (i>1 and e["before_sha256"]!=events[i-2]["after_sha256"])):
                raise ValueError("MG55_AUTHENTIC_ORIGINAL_SOURCE_ACTION_CHAIN_INVALID")
            positive+=int(e["reward"]>0 and e["terminated"] is True)
        if positive!=ep["original_terminal_goal_rewards"]:
            raise ValueError("MG55_ORIGINAL_TERMINAL_REWARD_INVALID")
        if ep["role"] not in (ON,OFF):continue
        family,role=ep["family"],ep["role"]
        enabled=role==ON
        actor=actors.get((family,role),PooledGoalCredit(enabled))
        if (actor.steering_enabled is not enabled
            or actor.total!=ep["prior_selected_source_samples"]):
            raise ValueError("MG55_ROLE_SOURCE_MEMORY_CROSSTALK")
        actor.begin_episode()
        old=(actor.pooled_opportunities,actor.pooled_overrides,
             actor.pooled_signal_events,actor.pooled_credit_assignments)
        stats=collections.Counter()
        sem=[]
        for e in events:
            before,after=e["before"],e["after"]
            selected=e["action"]
            info=predecision(actor,before) if enabled else None
            if enabled:
                stats["total_decisions"]+=1
                stats["phase_seek"]+=int(info["phase_ok"])
                stats["parent_nav_choice"]+=int(info["parent_navigation_action"])
                stats["target_not_front"]+=int(info["target_not_exact_front"])
                stats["has_prior_source_signal"]+=int(info["has_source_relevance_signal"])
                stats["all_initial_gates"]+=int(info["eligible"])
                stats["source_context_has_trials"]+=int(info["same_context_source_trials"]>0)
                stats["source_context_has_positive_credit"]+=int(info["positive_context_credit"])
                stats["eligible_with_support"]+=int(info["eligible"] and info["supported"])
                stats["eligible_with_alt"]+=int(info["eligible"] and info["supported_alternative"])
                stats["eligible_expected_override"]+=int(info["frozen_override_expected"])
                if info["eligible"] and info["supported_alternative"]:
                    gap=info["gap"]
                    if gap<=0: stats["alt_gap_le_zero"]+=1
                    elif gap<0.125:stats["alt_gap_0_to_eighth"]+=1
                    elif gap<0.25:stats["alt_gap_eighth_to_quarter"]+=1
                    elif gap<0.5:stats["alt_gap_quarter_to_half"]+=1
                    else:stats["alt_gap_at_least_half"]+=1
                contexts[(family,role)][info["public_context"]].add(info["public_before_sha"])
            actual=actor.choose(before)
            if actual!=selected:
                raise ValueError("MG55_ORIGINAL_MG54_SELECTED_POLICY_REPLAY_DIVERGED")
            actor.observe_selected(before,selected,after,e["reward"],e["terminated"])
            sem.append((selected,e["before_sha256"],e["after_sha256"],
                        e["reward"],e["terminated"],e["truncated"]))
        state=actor.checkpoint()
        if (actor.total!=ep["selected_source_samples_after"]
            or hashlib.sha256(state).hexdigest()!=ep["checkpoint_sha256"]
            or actor.pooled_opportunities-old[0]!=ep["source_pooled_goal_opportunities"]
            or actor.pooled_overrides-old[1]!=ep["source_pooled_goal_overrides"]
            or actor.pooled_signal_events-old[2]!=ep["source_pooled_goal_events"]
            or actor.pooled_credit_assignments-old[3]!=ep["source_pooled_credit_assignments"]
            or PooledGoalCredit.restore(state).checkpoint()!=state):
            raise ValueError("MG55_COLD_POOLED_ACTOR_STATE_MISMATCH")
        actors[(family,role)]=PooledGoalCredit.restore(state)
        semantics[(family,ep["seed_dev_exposed"],role)]=digest(sem)
        stats.update({"actions":len(events),
                      "source_opportunities":ep["source_pooled_goal_opportunities"],
                      "source_overrides":ep["source_pooled_goal_overrides"],
                      "source_signals":ep["source_pooled_goal_events"],
                      "source_credit_assignments":ep["source_pooled_credit_assignments"],
                      "genuine_goals":ep["original_terminal_goal_rewards"]})
        grouped[(family,role)].update(stats)
        per_episode.append({"family":family,"seed":ep["seed_dev_exposed"],
                            "role":role,"diagnostic":dict(stats),
                            "checkpoint_sha256":ep["checkpoint_sha256"],
                            "selected_events_sha256":ep["source_events_sha256"]})
    if seen!=expected or actions!=37047 or len(per_episode)!=18:
        raise ValueError("MG55_COMPLETE_SOURCE_OR_ACTOR_REPLAY_DENOMINATOR_INVALID")
    same=0
    for family,seeds in zip(FAMILIES,SEEDS):
        for seed in seeds:
            if semantics[(family,seed,ON)]!=semantics[(family,seed,OFF)]:
                raise ValueError("MG55_ORIGINAL_ENABLE_DISABLE_ACTION_PATH_DIFFERENCE")
            same+=1
    by_family={}
    for family in FAMILIES:
        by_family[family]={}
        for role in (ON,OFF):
            st=grouped[(family,role)]
            ref=source["per_family_per_role"][family][role]
            if st["actions"]!=ref["actions"] or st["genuine_goals"]!=ref["positive_goal_episodes"]:
                raise ValueError("MG55_AGGREGATE_GOAL_RECONCILIATION_FAILURE")
            actor=actors[(family,role)]
            obs=contexts[(family,role)] if role==ON else {}
            by_family[family][role]={
                **dict(st),
                "learned_source_context_action_keys":len(actor.pooled),
                "positive_credit_keys":sum(v[1]>0 for v in actor.pooled.values()),
                "positive_navigation_credit_keys":sum(
                    k.endswith(("|0","|1","|2")) and v[1]>0
                    for k,v in actor.pooled.items()),
                "credit_mass":round(sum(v[1] for v in actor.pooled.values()),8),
                "pooled_public_contexts":len(obs),
                "contexts_with_multiple_public_hashes":sum(len(v)>1 for v in obs.values()),
            }
    on=[grouped[(f,ON)] for f in FAMILIES]
    off=[grouped[(f,OFF)] for f in FAMILIES]
    if (sum(s["source_opportunities"] for s in on)!=379
        or sum(s["source_overrides"] for s in on)!=0
        or sum(s["source_signals"] for s in on)!=11
        or sum(s["source_credit_assignments"] for s in on)!=88
        or sum(s["genuine_goals"] for s in on)!=4
        or sum(s["genuine_goals"] for s in off)!=4
        or same!=9):
        raise ValueError("MG55_PRESERVED_MG54_FROZEN_NEGATIVE_CHANGED")
    return {"classification":PASS,
        "original_full_episode_count":len(rows),
        "original_selected_source_actions":actions,
        "new_original_world_actions":0,
        "semantically_identical_enabled_disabled_episode_pairs":same,
        "per_family_exact_actor_replay":by_family,
        "per_episode_exact_actor_replay":per_episode,
        "caveat":"This proves exact replay of selected public actions, not off-policy causal alternatives or physical state equivalence."}

def run(archive,out):
    p=preflight()
    with archive.open("rb") as f:
        if hashlib.file_digest(f,"sha256").hexdigest()!=ZIP_SHA:
            raise ValueError("MG55_ORIGINAL_IMMUTABLE_ZIP_BYTE_SHA_MISMATCH")
    first=None;digests=[]
    with zipfile.ZipFile(archive) as z:
        files={"comparison.log","first.json","second.json","first.log","second.log",
               "first-resources.json","second-resources.json","mg33c-synthetic.json"}
        if set(z.namelist())!=files:
            raise ValueError("MG55_ARCHIVED_ORIGINAL_SOURCE_LAYOUT_CHANGED")
        if SOURCE_SHA not in z.read("comparison.log").decode("utf8"):
            raise ValueError("MG55_TWO_PROCESS_SOURCE_SHA_COMPARISON_MISSING")
        for name in ("first.json","second.json"):
            with z.open(name) as f:record=json.load(f)
            if (record.get("canonical_source_sha256")!=SOURCE_SHA
                or digest(record["source"])!=SOURCE_SHA):
                raise ValueError("MG55_ORIGINAL_COMPLETE_CANONICAL_SOURCE_CHANGED")
            x=replay(record["source"],p)
            digests.append(digest(x))
            if first is None:first=x
            del x,record;gc.collect()
        if len(set(digests))!=1:
            raise ValueError("MG55_INDEPENDENT_FULL_COLD_REPLAY_DIFFERED")
        for name in ("first-resources.json","second-resources.json"):
            with z.open(name) as f:r=json.load(f)
            if r["original_source_sha256"]!=SOURCE_SHA or len(r["records"])!=216:
                raise ValueError("MG55_ORIGINAL_RESOURCE_ASSOCIATION_INVALID")
    report={"schema":"itd02.mg55.original-mg54-pooled-credit-readonly-report.v1",
            "classification":PASS,"source_original_sha256":SOURCE_SHA,
            "source_archive_zip_sha256":ZIP_SHA,
            "full_original_processes_replayed":2,"scientific_first_use":False,
            "original_mg54_science_negative_preserved":True,"diagnostic":first}
    report["canonical_audit_sha256"]=digest(report)
    out.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n",encoding="utf8")
    for family in FAMILIES:
        print("MG55_EXACT_POOLED_DECISION_GATES",json.dumps({
            "family":family,
            "enabled":first["per_family_exact_actor_replay"][family][ON],
            "disabled":first["per_family_exact_actor_replay"][family][OFF]},sort_keys=True))
    print("MG55_TWO_INDEPENDENT_ORIGINAL_COLD_POLICY_REPLAYS_MATCH",SOURCE_SHA)
    print("MG55_CANONICAL_AUDIT_SHA256",report["canonical_audit_sha256"])
    print("MG55_FROZEN_READONLY_CLASSIFICATION",report["classification"])

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--preflight",action="store_true")
    ap.add_argument("--archive",type=Path)
    ap.add_argument("--output",type=Path)
    a=ap.parse_args()
    if a.preflight:
        preflight();return
    if a.archive is None or a.output is None:
        ap.error("--archive and --output required")
    run(a.archive,a.output)

if __name__=="__main__":main()
