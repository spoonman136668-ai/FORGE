#!/usr/bin/env python3
"""MG12 prospective, original Farama selected-public post-door credit audit.

Unchanged MG11 native learners, raw public observation and chosen feedback.
An independently fitted two-hop conventional actor is the added control.
No inferred physical crossing from ego-centric source-pixel motion.
"""
import argparse,json,resource,time,traceback
from pathlib import Path
from k4r_minigrid_source import canon,sha
import mg11_authentic_selected_novelty as parent
from mg12_conventional_two_step import independent_fit,independent_episode

SCHEMA="itd02.mg12.original-postdoor-public-selected-audit.v1"
PREREG=Path(__file__).with_name("mg12_postdoor_prereg.json")
BLOCKED="MG12_POSTDOOR_ORIGINAL_SOURCE_BLOCKED__NO_SCIENCE"
NEGATIVE="MG12_POSTDOOR_NATIVE_GOAL_NOT_ESTABLISHED__NO_SCIENCE"
POSITIVE="MG12_BOTH_NATIVE_POSTDOOR_GOAL_ENGINEERING_POSITIVE__NO_SCIENCE"
ROLES=parent.ROLES+("conventional_two_step_public_model",)
NATIVE=("wingless_go_dk12","yggdrasil_r16")

def freeze():
    p=json.loads(PREREG.read_text(encoding="utf-8"))
    if (p["schema"]!="itd02.mg12.postdoor-public-source.v1"
        or p["parent_head"]!="79a494a30dd54bd0dd1211b41d215ebf05cc29e8"
        or p["original_source_evaluator_blob"]!="89f68a4f97232cd63cdbb2675e1deb53d75abfcb"
        or p["new_development_seeds"]!=[72301,72303,72307]
        or p["original_FIT_count"]!=1664 or p["max_original_steps"]!=192
        or p["external_live_actions"]!=0 or p["roles"]!=list(ROLES)
        or p["public_fields"]!=["image","direction","mission"]
        or p["action_ids"]!=list(range(7))
        or p["classification"]["blocked"]!=BLOCKED
        or p["classification"]["negative"]!=NEGATIVE
        or p["classification"]["positive"]!=POSITIVE):
        raise ValueError("MG12_FROZEN_ORIGINAL_PUBLIC_SOURCE_PREREG_DRIFT")
    return p

def classify_door(event):
    b=event["public_before"]
    a=event["public_after"]
    before=b["image"][3][5];after=a["image"][3][5]
    if event["action"]!=5 or before[0]!=4 or after[0]!=4:
        return "other"
    if before[2]!=0 and after[2]==0:return "open"
    if before[2]==0 and after[2]!=0:return "close"
    return "other"

def examine_episode(r):
    events=r["all_original_public_selected_events"]
    if len(events)!=r["real_original_source_actions"] or not 1<=len(events)<=192:
        raise ValueError("MG12_NO_REAL_ORIGINAL_ACTION_SERIES")
    opens=[];closes=[];time_to_goal=[];post=[]
    keydoor=0;real_goals=0;image_changes=0;compass_only=0
    actions={str(a):0 for a in range(7)}
    for i,e in enumerate(events):
        if (e["index"]!=i+1 or type(e["action"])is not int or e["action"] not in range(7)
            or e["external_action_count"]!=0
            or set(e["public_before"])!={"image","direction","mission"}
            or set(e["public_after"])!={"image","direction","mission"}
            or e["before_sha"]!=sha(canon(e["public_before"]).encode())
            or e["after_sha"]!=sha(canon(e["public_after"]).encode())):
            raise ValueError("MG12_NONAUTHENTIC_SELECTED_PUBLIC_EVENT")
        kind=classify_door(e)
        if kind=="open":opens.append(i)
        if kind=="close":closes.append(i)
        if e["original_reward"]>0:real_goals+=1
        keydoor+=int(e["public_key_front_door"])
        image_changes+=int(e["public_before"]["image"]!=e["public_after"]["image"])
        compass_only+=int(e["public_before"]["image"]==e["public_after"]["image"]
                         and e["public_before"]["direction"]!=e["public_after"]["direction"])
        actions[str(e["action"])]+=1
    goals_after_open=sum(
       int(any(g>o and events[g]["original_reward"]>0 for g in range(o+1,len(events))))
       for o in opens)
    # Each opening has its own censored at-most-eight true selected action window.
    for o in opens:
        window=events[o+1:o+9]
        open_before=events[o]["before_sha"]
        public_shas=[events[o]["after_sha"]]+[x["after_sha"] for x in window]
        post.append({
            "open_selected_ordinal":o+1,
            "source_reward_at_open":events[o]["original_reward"],
            "subsequent_selected_steps":len(window),
            "right_censored":len(window)<8,
            "forward_selected":sum(x["action"]==2 for x in window),
            "repeated_toggle_selected":sum(x["action"]==5 for x in window),
            "door_reclosed_source":sum(classify_door(x)=="close" for x in window),
            "door_reopened_source":sum(classify_door(x)=="open" for x in window),
            "distinct_source_public_image_shas":len(set(
                sha(canon(x["public_after"]["image"]).encode()) for x in window)),
            "actual_source_public_image_changes":sum(
                x["public_before"]["image"]!=x["public_after"]["image"] for x in window),
            "public_state_sha_revisits":len(public_shas)-len(set(public_shas)),
            "original_goal_reward_after_open":sum(x["original_reward"]>0 for x in events[o+1:]),
            "source_returned_to_opening_before_SHA":sum(
                x["after_sha"]==open_before for x in window)
        })
    return {"role":r["role"],"evaluator_seed_only":r["evaluator_seed_only"],
        "source_selected_steps":len(events),"distinct_actions":len(set(e["action"] for e in events)),
        "original_true_goal_rewards":real_goals,
        "source_public_front_door_openings":len(opens),
        "source_public_front_door_closings":len(closes),
        "public_key_held_front_door_frames":keydoor,
        "public_image_changes":image_changes,
        "compass_only_public_changes":compass_only,
        "selected_original_action_histogram":actions,
        "original_goals_after_any_own_door_opening":sum(
            e["original_reward"]>0 and any(o<i for o in opens)
            for i,e in enumerate(events)),
        "public_post_door_open_windows":post}

def run(go_new,go_old,p):
    # Reuse *unchanged* source policies, original training and selected credit.
    base_p={"source_FIT_seeds":p["original_FIT_seeds"],
         "development_seeds":p["new_development_seeds"],
         "max_original_steps":p["max_original_steps"],
         "source_farama":p["original_farama"],
         "new_go":p["native_go"],"new_ygg":p["native_ygg"]}
    original=parent.run(go_new,go_old,base_p)
    if original["classification"] not in (parent.NEGATIVE,parent.POSITIVE):
        raise ValueError("MG12_ORIGINAL_NATIVE_SOURCE_NOT_INTACT")
    source_e=original["original_public_source_evidence"]
    classical_fit=independent_fit(p,source_e["same_original_public_FIT_source_sha"])
    extra=[independent_episode(seed,classical_fit["checkpoint"])
           for seed in p["new_development_seeds"]]
    records=source_e["original_public_selected_records"]+extra
    if len(records)!=24:raise ValueError("MG12_NOT_EIGHT_TRUE_ORIGINAL_ROLES")
    for seed in p["new_development_seeds"]:
        group=[x for x in records if x["evaluator_seed_only"]==seed]
        if len(group)!=8 or {x["role"] for x in group}!=set(ROLES):
            raise ValueError("MG12_MISSING_SOURCE_OR_CONTROL")
        if len({x["original_public_start_sha"] for x in group})!=1:
            raise ValueError("MG12_UNEQUAL_ORIGINAL_PUBLIC_RESETS")
    observed=[examine_episode(r) for r in records]
    summaries={}
    for role in ROLES:
        group=[o for o in observed if o["role"]==role]
        if len(group)!=3:raise ValueError("MG12_MISSING_ONE_ROLE")
        summaries[role]={
            "episodes":3,"real_original_selected_actions":sum(x["source_selected_steps"] for x in group),
            "minimum_distinct_actions_per_episode":min(x["distinct_actions"] for x in group),
            "public_door_openings":sum(x["source_public_front_door_openings"] for x in group),
            "public_door_closings":sum(x["source_public_front_door_closings"] for x in group),
            "key_held_front_door_frames":sum(x["public_key_held_front_door_frames"] for x in group),
            "post_open_forward_selected":sum(sum(w["forward_selected"] for w in x["public_post_door_open_windows"]) for x in group),
            "post_open_repeated_toggle":sum(sum(w["repeated_toggle_selected"] for w in x["public_post_door_open_windows"]) for x in group),
            "post_open_door_reclosures":sum(sum(w["door_reclosed_source"] for w in x["public_post_door_open_windows"]) for x in group),
            "source_image_changes":sum(x["public_image_changes"] for x in group),
            "compass_only_public_changes":sum(x["compass_only_public_changes"] for x in group),
            "original_goal_rewards":sum(x["original_true_goal_rewards"] for x in group),
            "original_goal_rewards_after_open":sum(x["original_goals_after_any_own_door_opening"] for x in group)}
    positive=all(summaries[n]["original_goal_rewards_after_open"]>=1 for n in NATIVE)
    evidence={"schema":SCHEMA,"original_farama_source":p["original_farama"],
        "source_fixed_native_go_ygg":{k:p[k] for k in ("native_go","native_ygg")},
        "unchanged_native_and_original_seven_arm_evidence":source_e,
        "independently_matched_1664_fit_source_sha":classical_fit["source_selected_sha"],
        "independent_classical_fit_action_counts":classical_fit["action_counts"],
        "independent_classical_fit_checkpoint_sha":sha(classical_fit["checkpoint"]),
        "eighth_independent_original_selected_control":extra,
        "postdoor_public_diagnostic_per_episode":observed,
        "postdoor_public_diagnostic_per_role":summaries,
        "external_original_selected_actions":0,
        "no_oracle_or_global_pose":True,
        "no_native_policy_change_since_MG11":True}
    return {"schema":SCHEMA,"classification":POSITIVE if positive else NEGATIVE,
       "scientific_first_use":False,"accepted_native_changed":False,
       "FORGE_controller_changed":False,"source_original_FIT_count":1664,
       "original_source_episodes":24,"external_original_actions":0,
       "canonical_original_public_source_sha":sha(canon(evidence).encode()),
       "original_source_evidence":evidence}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--wingless-dk12",type=Path,required=True)
    ap.add_argument("--wingless-dk11",type=Path,required=True)
    ap.add_argument("--output",type=Path,required=True)
    x=ap.parse_args();start=time.perf_counter();cpu=time.process_time()
    try:result=run(x.wingless_dk12,x.wingless_dk11,freeze())
    except Exception as e:
        result={"schema":SCHEMA,"classification":BLOCKED,"scientific_first_use":False,
           "error_type":type(e).__name__,"error":str(e),
           "trace_tail":traceback.format_exc().splitlines()[-15:]}
    result["host_wall_seconds"]=round(time.perf_counter()-start,6)
    result["host_cpu_seconds"]=round(time.process_time()-cpu,6)
    result["host_peak_rss_kib"]=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    x.output.write_text(json.dumps(result,sort_keys=True,indent=2,allow_nan=False)+"\n")
    print("MG12_CLASSIFICATION",result["classification"])
    print("MG12_CANONICAL_SHA",result.get("canonical_original_public_source_sha","NONE"))
    print("MG12_ROLE_RESULTS",json.dumps(result.get("original_source_evidence",{}).get(
        "postdoor_public_diagnostic_per_role",{}),sort_keys=True))
    if result["classification"]==BLOCKED:
        print("MG12_BLOCKER",result.get("error_type"),result.get("error"))
    return 1 if result["classification"]==BLOCKED else 0
if __name__=="__main__":raise SystemExit(main())
