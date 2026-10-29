#!/usr/bin/env python3
"""MG21 original Farama DEV: native source-selected online learning, 0 FIT.

Each actor is independently cold-started at the FIRST new original family seed.
Only its own authenticated selected source outcomes are carried into the SECOND
development seed in that family. Nothing is a hidden reward, map or action plan.
These development seeds become exposed immediately on first run. NOT science.
"""
from __future__ import annotations
import argparse,base64,hashlib,json,math,random,time,traceback
from pathlib import Path
import gymnasium as gym
import minigrid
from mg17_original_family_source_qual import public,digest,frozen,attest_source
from mg18_native_mission_boundary_audit import WingBridge
from research.native.itd02.mg19.original_mission_cells import OriginalMissionAdapter
from research.native.itd02.mg19.genuine_mission_cells import MissionCells
from mg21_source_lineage_audit import audit as audit_source_lineage

HERE=Path(__file__).resolve().parent
CONTRACT=HERE/"mg21_original_fresh_cohort_prereg.json"
SCHEMA="itd02.mg21.original-genuine-mission-source-online-development.v1"
ROLES=("wingless_MG19_native","yggdrasil_MG19_local_cells",
       "independent_public_transition_count_conventional","uniform_original_random")
UPSTREAM="7f5853792ea7f04f75614661006d87fcf949f26d"

def canonical(x):
    return json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=True,allow_nan=False).encode("ascii")

def sha(x):
    if type(x) is bytes:return hashlib.sha256(x).hexdigest()
    return hashlib.sha256(canonical(x)).hexdigest()

class Conventional:
    """Independent tabular selected public state/action consequence control.

    Exact public state includes ORIGINAL mission, pixels and heading. Selection
    balances historical selected reward vs least tried action. No env oracle.
    """
    def __init__(self,counts=None,total=0):
        self.counts={} if counts is None else counts
        self.total=total
    def choose(self,before):
        key=digest(before)
        rows=self.counts.get(key,{})
        start=int(key[:2],16)%7
        scores=[]
        for a in range(7):
            cell=rows.get(str(a),{"count":0,"success":0})
            score=100*cell["success"]//(cell["count"]+1)-cell["count"]
            scores.append(score)
        top=max(scores)
        return next(a for step in range(7) if scores[a:=(start+step)%7]==top)
    def observe(self,before,action,after,reward,terminated):
        if type(action) is not int or action not in range(7):
            raise ValueError("MG21_CONTROL_INVALID_SELECTED_SOURCE")
        key=digest(before)
        row=self.counts.setdefault(key,{})
        value=row.setdefault(str(action),{"count":0,"success":0})
        value["count"]+=1
        value["success"]+=int(reward>0 and terminated)
        self.total+=1
    def checkpoint(self):
        return canonical({"schema":"mg21.conventional.exact-original-public-count.v1",
                          "counts":self.counts,"total":self.total})
    @classmethod
    def restore(cls,raw):
        state=json.loads(raw)
        if set(state)!={"schema","counts","total"} or state["schema"]!="mg21.conventional.exact-original-public-count.v1":
            raise ValueError("MG21_CONTROL_STATE_SCHEMA")
        obj=cls(state["counts"],state["total"])
        if obj.checkpoint()!=raw or obj.total!=sum(v["count"] for row in obj.counts.values() for v in row.values()):
            raise ValueError("MG21_CONTROL_SELECTED_COUNTERS_BAD")
        return obj

def one_episode(family,seed,role,cap,prior_checkpoint,go_path,source_entry):
    env=gym.make(family)
    go=ygg=adapter=control=None
    observed=[];start_count=0
    start=time.perf_counter();cpu=time.process_time()
    try:
        if getattr(env.action_space,"n",None)!=7 or gym.spec(family).entry_point!=source_entry:
            raise ValueError("MG21_NOT_PINNED_ORIGINAL_PUBLIC_7_ACTION_FAMILY")
        raw,_=env.reset(seed=seed)
        frame=public(raw)
        initial_mission=frame["mission"];initial_sha=digest(frame)
        if role==ROLES[0]:
            go=WingBridge(go_path)
            if prior_checkpoint is not None:
                reply=go.request("load",state=base64.b64encode(prior_checkpoint).decode("ascii"))
                start_count=reply["updates"]
                if go.snapshot()!=prior_checkpoint:
                    raise ValueError("MG21_GO_NOT_COLD_RESTORED")
            go.request("begin_episode")
        elif role==ROLES[1]:
            ygg=MissionCells() if prior_checkpoint is None else MissionCells.restore(prior_checkpoint)
            start_count=ygg.samples
            adapter=OriginalMissionAdapter()
            adapter.reset_public(frame)
            ygg.start_session(adapter,"mg21-"+family+"-"+str(seed),live=True)
        elif role==ROLES[2]:
            control=Conventional() if prior_checkpoint is None else Conventional.restore(prior_checkpoint)
            start_count=control.total
        elif role==ROLES[3]:
            rng=random.Random("MG21-original-unassisted:"+family+":"+str(seed))
            if prior_checkpoint is not None:
                raise ValueError("MG21_RANDOM_CONTROL_HAS_MEMORY")
        else:raise ValueError("MG21_UNREGISTERED_ROLE")
        for number in range(1,cap+1):
            before=public(raw)
            if before["mission"]!=initial_mission:
                raise ValueError("MG21_SOURCE_MISSION_CHANGED")
            if role==ROLES[0]:
                selected=go.request("choose",before=before)
                action,status=selected.get("action"),selected.get("status")
            elif role==ROLES[1]:
                selected=ygg.choose(before)
                if selected.get("external_fallback") is not False:
                    raise ValueError("MG21_YGG_EXTERNAL_ACTION_FALLBACK")
                action,status=selected["action"],selected["status"]
            elif role==ROLES[2]:
                action=control.choose(before);status="INDEPENDENT_SELECTED_PUBLIC_COUNT_CONTROL"
            else:
                action=rng.randrange(7);status="UNASSISTED_ORIGINAL_RANDOM_ACTION"
            if type(action) is not int or action not in range(7) or type(status) is not str or not status:
                raise ValueError("MG21_NATIVE_SELECTED_ACTION_MISSING")
            if go is not None:go.request("commit",before=before,action=action)
            elif adapter is not None:
                if adapter.submit(action)!=action:raise ValueError("MG21_YGG_ACTION_REMAP")
            # The ONE real source-selected step: no external policy or planner.
            raw_after,reward,terminated,truncated,_=env.step(action)
            after=public(raw_after)
            if after["mission"]!=initial_mission or type(terminated)is not bool or type(truncated)is not bool:
                raise ValueError("MG21_ORIGINAL_SOURCE_MISSION_OR_TERMINAL_DRIFT")
            value=float(reward)
            if not math.isfinite(value):
                raise ValueError("MG21_UNTRUSTED_SOURCE_REWARD")
            if go is not None:
                ack=go.request("feedback",before=before,action=action,after=after,
                               reward=value,terminal=terminated or truncated)
                count=ack["updates"]
            elif ygg is not None:
                adapter.complete(after,value,terminated,truncated)
                ygg.learn_selected(adapter,before,after)
                count=ygg.samples
            elif control is not None:
                control.observe(before,action,after,value,terminated or truncated)
                count=control.total
            else:count=None
            if role!=ROLES[3] and count!=start_count+number:
                raise ValueError("MG21_LOST_SOURCE_SELECTED_FEEDBACK")
            observed.append({"index":number,"before":before,"action":action,"after":after,
                             "mission":initial_mission,"policy_status":status,
                             "reward":value,"terminated":terminated,"truncated":truncated,
                             "before_sha256":digest(before),"after_sha256":digest(after),
                             "external_actions":0})
            raw=raw_after
            if terminated or truncated:break
        if go is not None:
            state=go.snapshot()
            cold=WingBridge(go_path)
            try:
                ack=cold.request("load",state=base64.b64encode(state).decode("ascii"))
                if ack["updates"]!=start_count+len(observed) or cold.snapshot()!=state:
                    raise ValueError("MG21_GO_COLD_SELECTED_MEMORY_LOSS")
            finally:cold.close()
        elif ygg is not None:
            state=ygg.checkpoint()
            if MissionCells.restore(state).checkpoint()!=state:
                raise ValueError("MG21_YGG_COLD_SELECTED_MEMORY_LOSS")
        elif control is not None:
            state=control.checkpoint()
            if Conventional.restore(state).checkpoint()!=state:
                raise ValueError("MG21_CONVENTIONAL_COLD_SELECTED_MEMORY_LOSS")
        else:state=None
        summary={"family":family,"seed_dev_exposed":seed,"role":role,
                 "public_start_sha256":initial_sha,"original_public_mission":initial_mission,
                 "original_source_actions":len(observed),
                 "prior_selected_source_samples":start_count,
                 "selected_source_samples_after":None if state is None else start_count+len(observed),
                 "original_terminal_goal_rewards":sum(int(e["reward"]>0 and e["terminated"]) for e in observed),
                 "observed_public_changes":sum(e["before_sha256"]!=e["after_sha256"] for e in observed),
                 "unique_public_views":len({e["before_sha256"] for e in observed}),
                 "distinct_actions":len({e["action"] for e in observed}),
                 "checkpoint_sha256":None if state is None else sha(state),
                 "source_events_sha256":sha(observed),"source_events":observed}
        metrics={"role":role,"family":family,"dev_seed":seed,
                 "wall_seconds":round(time.perf_counter()-start,6),
                 "python_cpu_seconds":round(time.process_time()-cpu,6)}
        return summary,metrics,state
    finally:
        env.close()
        if go is not None:go.close()

def run(source_root,go_path):
    lineage=audit_source_lineage()
    p=json.loads(CONTRACT.read_text(encoding="utf-8"))
    if not Path(minigrid.__file__).resolve().is_relative_to(source_root.resolve()):
        raise ValueError("MG21_IMPORTED_MINIGRID_NOT_PINNED")
    upstream=frozen()
    attest_source(source_root,upstream)
    registry={item["id"]:item["entry_point"] for item in upstream["families"]}
    rows=[];resources=[]
    for cohort in p["dev"]["original_farama_envs"]:
        family=cohort["environment"]
        active={role:None for role in ROLES}
        for seed in cohort["seeds"]:
            by_seed=[]
            for role in ROLES:
                line,metrics,new_state=one_episode(
                    family,seed,role,p["dev"]["per_episode_source_action_cap"],
                    active[role],go_path,registry[family])
                rows.append(line);resources.append(metrics);by_seed.append(line)
                if role!=ROLES[3]:active[role]=new_state
            if len({r["public_start_sha256"] for r in by_seed})!=1:
                raise ValueError("MG21_EQUAL_ORIGINAL_FAMILY_SEED_START_FAILED")
    if len(rows)!=32 or any(not x["source_events"] or x["original_source_actions"]>128 for x in rows):
        raise ValueError("MG21_ORIGINAL_PUBLIC_DEV_ROLE_MATRIX_INCOMPLETE")
    tally={}
    for family in registry:
        if family not in [c["environment"] for c in p["dev"]["original_farama_envs"]]:
            continue
        tally[family]={}
        for role in ROLES:
            group=[r for r in rows if r["role"]==role and r["family"]==family]
            if len(group)!=2 or group[0]["prior_selected_source_samples"]!=0:
                raise ValueError("MG21_NOT_TWO_SEQUENTIAL_ORIGINAL_SOURCE_EPISODES")
            if role!=ROLES[3] and group[1]["prior_selected_source_samples"]!=group[0]["selected_source_samples_after"]:
                raise ValueError("MG21_NOT_PERSISTENT_ORIGINAL_SOURCE_MEMORY_BETWEEN_SEEDS")
            tally[family][role]={
                "episodes":2,"original_goal_rewards":sum(r["original_terminal_goal_rewards"] for r in group),
                "original_selected_source_actions":sum(r["original_source_actions"] for r in group),
                "distinct_selected_actions_by_seed":[r["distinct_actions"] for r in group],
                "public_changes":sum(r["observed_public_changes"] for r in group),
                "external_actions":0}
    source={"schema":SCHEMA,"classification":"MG21_ORIGINAL_SOURCE_DEVELOPMENT_RECORDED_NOT_SCIENTIFIC_FIRST_USE",
            "source_commit":UPSTREAM,"native_pins":p["source_pins"],
            "source_lineage_receipt_sha":lineage["canonical_custody_sha256"],
            "new_original_source_env_actions":sum(r["original_source_actions"] for r in rows),
            "original_source_32_independent_role_episodes":rows,
            "per_family_per_role":tally,
            "external_live_actions":0,
            "scientific_first_use":False,
            "native_models_promoted":False,
            "accepted_models_and_forge_controller_unchanged":True}
    return {"schema":SCHEMA,"source":source,"source_sha256":sha(source),
            "resources_outside_source_digest":resources,
            "classification":source["classification"]}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--source-root",type=Path)
    ap.add_argument("--native-go",type=Path)
    ap.add_argument("--output",type=Path)
    ap.add_argument("--compare",nargs=2,type=Path)
    opts=ap.parse_args()
    if opts.compare:
        a,b=[json.loads(path.read_text()) for path in opts.compare]
        if (a["source"]!=b["source"] or a["source_sha256"]!=b["source_sha256"] or
            a["source_sha256"]!=sha(a["source"]) or
            len(a["source"]["original_source_32_independent_role_episodes"])!=32 or
            a["source"]["external_live_actions"]!=0 or
            a["source"]["scientific_first_use"] is not False):
            raise ValueError("MG21_ORIGINAL_SOURCE_INDEPENDENT_TWO_PROCESS_OR_CUSTODY_FAILED")
        print("MG21_TWO_INDEPENDENT_ORIGINAL_SOURCE_DEV_REPRO_PASS",a["source_sha256"])
        print("MG21_ORIGINAL_GOAL_SUMMARY",json.dumps(a["source"]["per_family_per_role"],sort_keys=True))
        return
    if not (opts.source_root and opts.native_go and opts.output):
        ap.error("required --source-root and --native-go and --output")
    started=time.perf_counter()
    try:
        result=run(opts.source_root,opts.native_go)
    except Exception as exc:
        result={"schema":SCHEMA,
                "classification":"MG21_ORIGINAL_DEV_ENGINEERING_SOURCE_BLOCKED",
                "error":str(exc),"type":type(exc).__name__,
                "trace_tail":traceback.format_exc().splitlines()[-14:],
                "scientific_first_use":False}
    result["wall_seconds_outside_source_digest"]=round(time.perf_counter()-started,6)
    opts.output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print("MG21_ORIGINAL_DEV_CLASSIFICATION",result["classification"])
    if result["classification"].endswith("BLOCKED"):
        raise RuntimeError(result["error"])
    print("MG21_ORIGINAL_DEV_SOURCE_SHA",result["source_sha256"])
    print("MG21_ORIGINAL_DEV_SUMMARY",json.dumps(result["source"]["per_family_per_role"],sort_keys=True))
if __name__=="__main__":
    main()
