#!/usr/bin/env python3
"""MG39B independent source-pinned MG38 engineered affordance ablation on new DEV.

The only method difference in the ablated candidate is removal of the two
engineered generic public-front pickup/toggle prior bonuses. Synthetic
source check compares the entire unchanged MG38 choose method minus this
one block to our ablated method. No native model modifications or hidden pose.
"""
from __future__ import annotations
import argparse,collections,hashlib,inspect,json,math,subprocess,time,traceback
from pathlib import Path
from mg31_original_public_exploration import FAMILIES,UPSTREAM,digest
from mg37_mg36_navigation_audit import event_metric
from mg33_original_frontier_dev import frontier_episode as mg33_episode
from mg34_original_graph_lookahead import frontier_episode as mg34_episode
from mg36_action_modelbased_original_dev import corrected_class,control_episode
from mg38_navigation_aware_original_dev import (
    NavigationAwareModel, navigation_episode as original_mg38_episode)

HERE=Path(__file__).resolve().parent
PREREG=HERE/"mg39b_original_affordance_ablation_prereg.json"
PARENT="46e7cc2acf84487f15f5eb21c785967ac6ac31cc"
FREEZE="a5e9efe7a76ba105cd662e935bc82491208f2624"
MG38="5512fa26a55484ebd5e0db1c3927c396ab231cdf"
CORRECTED="f6a0363fd0c0c1ae0f312a4de9062b9395e70aac"
ROLES=(
 "wingless_mg19_unchanged","yggdrasil_mg19_unchanged",
 "mg33_public_history_frontier_unchanged",
 "mg34_graph_lookahead_unchanged",
 "mg33c_actiononly_ucb_exact_source",
 "mg33c_actiononly_round_robin_exact_source",
 "mg38_generic_affordance_prior_enabled_exact_source",
 "mg39b_generic_affordance_prior_removed",
 "seeded_uniform_random")
SEEDS=((1011101,1011103,1011107),(1011201,1011203,1011207),
       (1011301,1011303,1011307),(1011401,1011403,1011407))

def git(*a):
    return subprocess.run(["git",*a],cwd=HERE.parents[1],
                          capture_output=True,text=True,check=False)

def freeze():
    p=json.loads(PREREG.read_text(encoding="utf8"))
    d=p["design"];parent=p["parent"]
    if (p["schema"]!="itd02.mg39b.original-public-affordance-ablation-paired-dev.v1"
        or p["phase"]!="PROSPECTIVE_SOURCE_AND_COHORT_FREEZE_BEFORE_EXECUTABLE_OR_ORIGINAL_ACTIONS"
        or parent["mg39_head"]!=PARENT or parent["mg38_head"]!=MG38
        or p["source"]["farama"]!=UPSTREAM
        or p["source"]["mg33c_exact"]!=CORRECTED
        or tuple(d["families"])!=FAMILIES or tuple(d["roles"])!=ROLES
        or tuple(map(tuple,d["fresh_exposed_dev_seeds"]))!=SEEDS
        or d["episodes"]!=108 or d["source_actions_per_episode_max"]!=192
        or d["full_independent_original_source_processes"]!=2
        or not all(p["prohibitions"].values())):
        raise ValueError("MG39B_FROZEN_DESIGN_OR_SOURCE_IDENTITY_CHANGED")
    seeds=[s for group in SEEDS for s in group]
    if len(seeds)!=12 or len(set(seeds))!=12:
        raise ValueError("MG39B_DUPLICATED_EXPOSED_DEV_ID")
    for sha in (PARENT,FREEZE):
        if git("merge-base","--is-ancestor",sha,"HEAD").returncode:
            raise ValueError("MG39B_FREEZE_NOT_COMMITTED_BEFORE_EXECUTABLE")
    for seed in seeds:
        prior=git("grep","-n","-w",str(seed),PARENT,"--",
                  "research/lcrm01","docs/research")
        if prior.returncode==0:raise ValueError("MG39B_SEED_ALREADY_EXPOSED")
        if prior.returncode!=1:raise ValueError("MG39B_SOURCE_CUSTODY_UNAVAILABLE")
    return p

class AblatedNavigation(NavigationAwareModel):
    SCHEMA="mg39b.navigation-public-empirical-no-engineered-generic-affordance.v1"

    def choose(self, public):
        if self.pending is not None:
            raise ValueError("MG38_DOUBLE_CHOICE_BEFORE_ORIGINAL_FEEDBACK")
        key = digest(public)
        first = int(key[:2], 16) % 7
        front = public["image"][3][5]
        row = self.edges.get(key, {})
        chosen = None
        best = None
        for offset in range(7):
            action = (first + offset) % 7
            cell = row.get(str(action))
            local_count = cell["n"] if cell else 0
            g = self.global_actions[action]
            g_count = g["n"]
            effect = (g["changed"] + 0.5) / (g_count + 1)
            novel = (g["novel"] + 0.5) / (g_count + 1)
            goal = (g["goals"] + 0.25) / (g_count + 1)
            if action == 2:
                # Forward public change is *not* assumed to prove locomotion.
                local_nochange = (0 if cell is None else
                                  (cell["n"] - cell["changed"]) / cell["n"])
                score = (2.3 + 1.7 / (1 + local_count)
                         + 1.0 * novel - 2.0 * local_nochange)
            elif action in (0, 1):
                # Rotations NEVER get credit for changing egocentric public SHA.
                # Rotation is still eligible after unsuccessful own forward.
                score = (0.4 + 0.4 / (1 + local_count)
                         + 2.5 * int(self.last_forward_nochange)
                         - 1.25 * self.turn_chain)
                if self.turn_chain >= 2:
                    score -= 8.0
            else:
                score = (0.6 + 1.7 / (1 + local_count) + 2.0 * goal
                         + 0.7 * effect - 0.1 * local_count)
                # MG39B: no engineered public-front pickup/door action bonus.
            # Keep reward tied only to selected empirical source consequences.
            if cell is not None:
                score += 2.0 * cell["goals"] / (1 + cell["n"])
            if best is None or score > best:
                best = score
                chosen = action
        self.pending = (key, chosen)
        return chosen


def ablated_episode(gym, entry, family, seed, prior, cap, public, original_digest):
    env = gym.make(family)
    try:
        if gym.spec(family).entry_point != entry or getattr(env.action_space,"n",None) != 7:
            raise ValueError("MG38_WRONG_AUTHENTIC_FARAMA_WORLD")
        raw, _ = env.reset(seed=seed)
        first = public(raw)
        start = original_digest(first)
        mission = first["mission"]
        model = AblatedNavigation() if prior is None else AblatedNavigation.restore(prior)
        model.begin_episode()
        previous_samples = model.total
        events = []
        for index in range(1,cap+1):
            before = public(raw)
            if before["mission"] != mission:
                raise ValueError("MG38_ORIGINAL_MISSION_CHANGED_DURING_EPISODE")
            action = model.choose(before)
            raw2, reward, terminated, truncated, _ = env.step(action)
            after = public(raw2)
            if (after["mission"] != mission or type(terminated) is not bool
                or type(truncated) is not bool or not math.isfinite(float(reward))):
                raise ValueError("MG38_ORIGINAL_WORLD_SELECTED_FEEDBACK_INVALID")
            model.observe_selected(before,action,after,float(reward),terminated)
            events.append({"index":index,"before":before,"after":after,
                "action":action,"mission":mission,"reward":float(reward),
                "terminated":terminated,"truncated":truncated,
                "before_sha256":original_digest(before),
                "after_sha256":original_digest(after),"external_actions":0,
                "policy_status":"MG38_ROTATION_NEUTRAL_EMPIRICAL_MODEL_SELECTED"})
            raw = raw2
            if terminated or truncated:
                break
        checkpoint = model.checkpoint()
        if (AblatedNavigation.restore(checkpoint).checkpoint() != checkpoint
            or model.total != previous_samples + len(events)):
            raise ValueError("MG38_COLD_SOURCE_MODEL_OR_EPISODE_SAMPLES_LOST")
        return ({
            "family":family,"role":ROLES[7],"seed_dev_exposed":seed,
            "public_start_sha256":start,"original_public_mission":mission,
            "original_source_actions":len(events),
            "prior_selected_source_samples":previous_samples,
            "selected_source_samples_after":model.total,
            "original_terminal_goal_rewards":
                sum(int(e["reward"]>0 and e["terminated"]) for e in events),
            "observed_public_changes":
                sum(e["before_sha256"]!=e["after_sha256"] for e in events),
            "unique_public_views":len({e["before_sha256"] for e in events}),
            "distinct_actions":len({e["action"] for e in events}),
            "checkpoint_sha256":hashlib.sha256(checkpoint).hexdigest(),
            "source_events_sha256":original_digest(events),
            "source_events":events
        }, checkpoint)
    finally:
        env.close()



def source_only():
    import textwrap
    # Entire method must be identical except for exactly the frozen
    # engineered generic object pickup / door toggle 4-line bonus block.
    old=inspect.getsource(NavigationAwareModel.choose)
    block=("                # Public object classes only; NOT a mission-target matcher.\n"
        "                if action == 3 and front[0] in (5,6,7):\n"
        "                    score += 2.2\n"
        "                elif action == 5 and front[0] == 4:\n"
        "                    score += 2.2\n")
    marker="                # MG39B: no engineered public-front pickup/door action bonus.\n"
    if old.count(block)!=1 or old.replace(block,marker)!=inspect.getsource(AblatedNavigation.choose):
        raise ValueError("MG39B_NOT_EXACT_ORIGINAL_MINUS_ONE_ENGINEERED_PRIOR")
    first={"image":[[[1,0,0] for _ in range(7)] for _ in range(7)],
           "direction":1,"mission":"pick up the red box"}
    first["image"][3][5]=[7,0,0]
    orig=NavigationAwareModel()
    no=AblatedNavigation()
    a,b=orig.choose(first),no.choose(first)
    if type(a)!=int or type(b)!=int or a not in range(7) or b not in range(7):
        raise ValueError("MG39B_CONTROL_POLICY_INVALID_ORIGINAL_PUBLIC_ACTION")
    second=dict(first,direction=2)
    orig.observe_selected(first,a,second,0.0,False)
    no.observe_selected(first,b,second,0.0,False)
    x=no.checkpoint()
    if AblatedNavigation.restore(x).checkpoint()!=x:
        raise ValueError("MG39B_ABLATED_COLD_CHECKPOINT_LOSS")
    no.begin_episode()
    if no.total!=1 or no.turn_chain!=0:
        raise ValueError("MG39B_EPISODE_MEMORY_RESET_INVALID")
    return {"exact_method_minus_engineered_prior":True,
            "original_synthetic_first_action":a,"ablated_synthetic_first_action":b}

def calculate(rows):
    results={}
    for family in FAMILIES:
        results[family]={}
        for role in ROLES:
            grp=[x for x in rows if x["family"]==family and x["role"]==role]
            if len(grp)!=3 or grp[0]["prior_selected_source_samples"] not in (0,None):
                raise ValueError("MG39B_SOURCE_COLD_SEED_COUNT_DRIFT")
            if role!=ROLES[-1]:
                for a,b in zip(grp,grp[1:]):
                    if a["selected_source_samples_after"]!=b["prior_selected_source_samples"]:
                        raise ValueError("MG39B_SOURCE_COLD_LEARNING_NOT_RETAINED")
            tally=collections.Counter()
            action_hist=[0]*7
            candidate_front_counts=collections.Counter()
            for ep in grp:
                if digest(ep["source_events"])!=ep["source_events_sha256"]:
                    raise ValueError("MG39B_ORIGINAL_EPISODE_SOURCE_HASH_MISMATCH")
                for e in ep["source_events"]:
                    z=event_metric(e)
                    tally.update(z)
                    action_hist[e["action"]]+=1
                    f=e["before"]["image"][3][5]
                    if f[0] in (5,6,7):
                        candidate_front_counts["pickupable_public_front_frames"]+=1
                        if e["action"]==3:
                            candidate_front_counts["generic_pickupable_front_selected_action3"]+=1
                    if f[0]==4:
                        candidate_front_counts["door_public_front_frames"]+=1
                        if e["action"]==5:
                            candidate_front_counts["generic_door_front_selected_action5"]+=1
            if sum(action_hist)!=sum(ep["original_source_actions"] for ep in grp):
                raise ValueError("MG39B_ROLE_ACTION_HISTOGRAM_INVALID")
            results[family][role]={
                "episodes":len(grp),"source_actions":sum(action_hist),
                "action_histogram":action_hist,
                "target_visible_frames":tally["target_any_visible_frames"],
                "exact_target_front_frames":tally["target_front_frames"],
                "exact_target_selected_pickup_attempts":tally["target_front_selected_pickup_attempts"],
                "exact_target_disappearance":tally["target_front_selected_effects"],
                "actual_door_openings":tally["locked_door_openings"],
                "positive_goal_episodes":sum(x["original_terminal_goal_rewards"]>0 for x in grp),
                **candidate_front_counts
            }
    return results

def run_original(source_root,native_go,control_root,p):
    import gymnasium as gym
    import minigrid
    from mg17_original_family_source_qual import (
        frozen as upstream_frozen,attest_source,public,digest as original_digest)
    from mg21_original_development import one_episode,ROLES as native_roles
    source_only()
    if not Path(minigrid.__file__).resolve().is_relative_to(source_root.resolve()):
        raise ValueError("MG39B_NOT_PINNED_ORIGINAL_FARAMA")
    upstream=upstream_frozen()
    attest_source(source_root,upstream)
    registry={v["id"]:v["entry_point"] for v in upstream["families"]}
    exact_control=corrected_class(control_root)
    results=[]
    for family,seeds in zip(FAMILIES,SEEDS):
        state={role:None for role in ROLES}
        for seed in seeds:
            original_start=[]
            for role in ROLES:
                if role in (ROLES[0],ROLES[1],ROLES[8]):
                    actual=(native_roles[0] if role==ROLES[0] else
                            native_roles[1] if role==ROLES[1] else native_roles[3])
                    row,_,new=one_episode(family,seed,actual,192,
                                          state[role],native_go,registry[family])
                elif role==ROLES[2]:
                    row,new=mg33_episode(gym,registry[family],family,seed,
                                         state[role],192,public,original_digest)
                elif role==ROLES[3]:
                    row,new=mg34_episode(gym,registry[family],family,seed,
                                         state[role],192,public,original_digest)
                elif role in (ROLES[4],ROLES[5]):
                    mode="ucb" if role==ROLES[4] else "round_robin"
                    row,new=control_episode(gym,registry[family],family,seed,
                                             mode,state[role],192,public,original_digest,
                                             exact_control)
                elif role==ROLES[6]:
                    row,new=original_mg38_episode(gym,registry[family],family,seed,
                                                  state[role],192,public,original_digest)
                elif role==ROLES[7]:
                    row,new=ablated_episode(gym,registry[family],family,seed,
                                             state[role],192,public,original_digest)
                else:raise ValueError("MG39B_INVALID_FROZEN_ROLE")
                row["role"]=role
                original_start.append(row["public_start_sha256"])
                if role!=ROLES[8]:state[role]=new
                results.append(row)
            if len(set(original_start))!=1:
                raise ValueError("MG39B_PAIRED_ORIGINAL_START_NOT_IDENTICAL")
    if len(results)!=108 or any(not (1<=r["original_source_actions"]<=192)
                                 for r in results):
        raise ValueError("MG39B_ORIGINAL_EPISODES_OR_SOURCE_ACTIONS_MISSING")
    table=calculate(results)
    on,off=ROLES[6],ROLES[7]
    unfamiliar=FAMILIES[1:]
    effects={role:sum(table[f][role]["exact_target_disappearance"] for f in unfamiliar)
             for role in (on,off)}
    goals={role:sum(table[f][role]["positive_goal_episodes"] for f in unfamiliar)
           for role in (on,off)}
    goal_families=sum(table[f][on]["positive_goal_episodes"]>0 for f in unfamiliar)
    difficult_goal=any(table[f][on]["positive_goal_episodes"]>0 for f in FAMILIES[1:3])
    supported=(effects[on]>effects[off] and goals[on]>goals[off]
               and difficult_goal and goal_families>=2)
    source={
        "schema":"itd02.mg39b.authentic-original-public-affordance-prior-ablation.dev.v1",
        "classification":p["frozen_outcomes"]["pass"] if supported
             else p["frozen_outcomes"]["fail"],
        "source_parent":PARENT,"farama_source":UPSTREAM,
        "original_108_episodes":results,
        "original_selected_action_count":sum(x["original_source_actions"] for x in results),
        "per_family_per_role":table,
        "paired_prior_on_off":{
            "effects":effects,"goal_episodes":goals,
            "prior_on_goal_positive_unfamiliar_families":goal_families,
            "prior_on_unlock_or_blocked_positive":difficult_goal,
            "filter_supported":supported},
        "exposed_dev_seeds":[list(a) for a in SEEDS],
        "source_only_exact_method_ablation":True,
        "zero_external_actions":True,"scientific_first_use":False,
        "native_models_or_controllers_modified":False,
        "mg28_native_rollout_permitted":False,
        "native_resource_parity_qualified":False}
    return {"schema":source["schema"],"source":source,
            "canonical_source_sha256":digest(source)}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--preflight",action="store_true")
    ap.add_argument("--source-root",type=Path)
    ap.add_argument("--native-go",type=Path)
    ap.add_argument("--control-root",type=Path)
    ap.add_argument("--output",type=Path)
    ap.add_argument("--compare",nargs=2,type=Path)
    args=ap.parse_args()
    p=freeze()
    if args.preflight:
        r=source_only()
        print("MG39B_EXACT_QUALIFIED_SOURCE_ONLY_ENGINEERED_PRIOR_ABLATION_PASS",
              json.dumps(r,sort_keys=True))
        return
    if args.compare:
        a,b=[json.loads(x.read_text(encoding="utf-8")) for x in args.compare]
        if (a.get("source")!=b.get("source")
            or a.get("canonical_source_sha256")!=b.get("canonical_source_sha256")
            or a.get("canonical_source_sha256")!=digest(a["source"])
            or len(a["source"]["original_108_episodes"])!=108
            or a["source"]["zero_external_actions"] is not True
            or a["source"]["scientific_first_use"] is not False):
            raise ValueError("MG39B_ORIGINAL_DUAL_PROCESSES_DIFFER_OR_MISSING")
        print("MG39B_TWO_INDEPENDENT_ORIGINAL_PROCESSES_IDENTICAL",a["canonical_source_sha256"])
        print("MG39B_FROZEN_DEV_CLASSIFICATION",a["source"]["classification"])
        print("MG39B_PAIRED_PRIOR_CONSEQUENCES",json.dumps(a["source"]["paired_prior_on_off"],sort_keys=True))
        return
    if any(x is None for x in (args.source_root,args.native_go,args.control_root,args.output)):
        ap.error("require source-root/native-go/control-root/output")
    started=time.perf_counter()
    try:result=run_original(args.source_root,args.native_go,args.control_root,p)
    except Exception as e:
        result={"schema":"itd02.mg39b.original-public-affordance-ablation.dev.v1",
                "classification":"MG39B_ORIGINAL_SOURCE_BLOCKED_NO_SCIENCE",
                "error_type":type(e).__name__,"error":str(e),
                "trace_tail":traceback.format_exc().splitlines()[-15:]}
    result["host_wall_time_outside_canonical_source_seconds"]=round(
        time.perf_counter()-started,6)
    args.output.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n",
                           encoding="utf-8")
    cls=result.get("classification",result.get("source",{}).get(
        "classification","MG39B_MISSING_CLASSIFICATION_BLOCKED"))
    print("MG39B_ORIGINAL_SOURCE_CLASSIFICATION",cls)
    if "BLOCKED" in cls:raise ValueError(result.get("error","MG39B_UNKNOWN_BLOCKER"))
    print("MG39B_ORIGINAL_SOURCE_SHA256",result["canonical_source_sha256"])
if __name__=="__main__":
    main()
