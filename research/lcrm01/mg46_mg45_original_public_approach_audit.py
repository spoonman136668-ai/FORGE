#!/usr/bin/env python3
"""MG46 retrospective original MG45 selected-public observation audit.

Never imports/runs Farama environments or native Wingless/Yggdrasil. Identifies
the first missing public task stage without inventing hidden location or
counterfactual actions. Pinned previously exposed original-source ZIP only.
"""
from __future__ import annotations
import argparse,collections,hashlib,json,subprocess,zipfile
from pathlib import Path
from mg31_original_public_exploration import digest
from mg37_mg36_navigation_audit import event_metric

HERE=Path(__file__).resolve().parent
PRE=HERE/"mg46_mg45_original_public_approach_audit_prereg.json"
PARENT="bff9b8551dfd2e64537c59199f032de19dd39f35"
FREEZE="831a9d8430fc97a6d43ca5ec84b7999b2c56f92a"
ZIP_SHA="14f986ef363fab757a39c79bf48e97e3a14f0fa0273080ab7b82b514bda88ff5"
SOURCE_SHA="7a7970c90711b68b934be306f2a9c5898b6325e441d222621e666ce1d3f2c30d"
FAMILIES=("MiniGrid-KeyCorridorS3R2-v0","MiniGrid-KeyCorridorS4R3-v0",
          "MiniGrid-ObstructedMaze-1Dl-v0")
SEEDS=((1041101,1041103,1041107),(1041201,1041203,1041207),
       (1041301,1041303,1041307))
CANDIDATE="mg44_public_precondition_release_enabled_UNMODIFIED"
DISABLED="mg44_public_precondition_release_disabled_UNMODIFIED"
ROLES=("wingless_mg19_unchanged","yggdrasil_mg19_unchanged",
"mg33_public_history_frontier_unchanged",
"mg34_graph_lookahead_unchanged",
"mg33c_actiononly_ucb_exact_source",
"mg33c_actiononly_round_robin_exact_source",
"mg38_generic_affordance_prior_enabled_exact_source",
"mg39b_generic_affordance_prior_removed",
"mg40_precondition_memory_enabled_unchanged",
"mg40_precondition_memory_ablated_unchanged",
"mg42_observed_reversal_guard_unchanged",
"mg43_engineered_target_matcher_plus_learned_action_value_unchanged",
"mg43_engineered_target_matcher_no_action_value_ablation_unchanged",
CANDIDATE,DISABLED,"seeded_uniform_random")

def git(*args):
    return subprocess.run(["git",*args],cwd=HERE.parents[1],
        capture_output=True,text=True,check=False)

def prereg():
    p=json.loads(PRE.read_text(encoding="utf-8"))
    q=p["parent"];v=p["frozen_audit"]
    if (p["schema"]!="itd02.mg46.authenticated-MG45-public-approach-no-target-source-audit.v1"
        or p["phase"]!="FROZEN_RETROSPECTIVE_METRICS_BEFORE_AUDIT_EXECUTABLE_NO_NEW_ORIGINAL_ACTIONS"
        or q["mg45_head"]!=PARENT or q["mg45_artifact"]!=12936790567
        or q["original_archive_sha256"]!=ZIP_SHA
        or q["original_source_canonical_sha256"]!=SOURCE_SHA
        or q["original_actor_episodes"]!=144
        or q["original_selected_actions"]!=27514
        or tuple(p["families"])!=FAMILIES
        or tuple(map(tuple,p["seeds"]))!=SEEDS
        or tuple(p["roles"])!=ROLES
        or p["classification_valid"]!="MG46_MG45_AUTHENTIC_TARGET_ABSENCE_APPROACH_AUDIT_PASS_NO_SCIENCE"
        or not v["none_new_source_actions"]
        or not v["two_independent_processes"]
        or not all(p["prohibitions"].values())):
        raise ValueError("MG46_FROZEN_ORIGINAL_MG45_SOURCE_AND_METRIC_DRIFT")
    for h in (PARENT,FREEZE):
        if git("merge-base","--is-ancestor",h,"HEAD").returncode:
            raise ValueError("MG46_PREREG_NOT_ANCESTOR_OF_EXECUTABLE")
    if git("hash-object","research/lcrm01/mg44_public_precondition_release.py").stdout.strip()!=q["mg44_policy_blob"]:
        raise ValueError("MG46_ORIGINAL_MG44_SOURCE_POLICY_CHANGED")
    return p

def preflight():
    p=prereg()
    assert len(p["families"])==3 and len(p["roles"])==16
    probe={"image":[[[1,0,0] for _ in range(7)] for _ in range(7)],
           "direction":0,"mission":"pick up the red box"}
    pair=json.loads(json.dumps(probe))
    pair["image"][3][5]=[7,0,0]
    sample={"index":1,"action":3,"before":pair,"after":probe,
            "mission":pair["mission"],"reward":1.0,"terminated":True,
            "external_actions":0,"before_sha256":digest(pair),
            "after_sha256":digest(probe)}
    if (event_metric(sample)["target_front_selected_effects"]!=1
        or event_metric(sample)["positive_terminal_goal_steps"]!=1):
        raise ValueError("MG46_PUBLIC_EFFECT_METRIC_SOURCE_ONLY_SELFTEST_FAILED")
    print("MG46_FROZEN_ORIGINAL_PUBLIC_SOURCE_ONLY_PREFLIGHT_PASS")
    return p

def episode_metrics(ep):
    actions=ep["source_events"]
    if (len(actions)!=ep["original_source_actions"]
        or not 1<=len(actions)<=192
        or digest(actions)!=ep["source_events_sha256"]
        or digest(actions[0]["before"])!=ep["public_start_sha256"]):
        raise ValueError("MG46_ORIGINAL_EPISODE_CUSTODY_FAIL")
    count=collections.Counter()
    hist=[0]*7
    contexts=set()
    target_contexts=set()
    door_contexts=set()
    afters=[]
    first_target=None
    first_door=None
    for i,e in enumerate(actions,1):
        if (e["index"]!=i or e["mission"]!=ep["original_public_mission"]
            or e["external_actions"]!=0
            or e["before_sha256"]!=digest(e["before"])
            or e["after_sha256"]!=digest(e["after"])
            or (i>1 and e["before_sha256"]!=actions[i-2]["after_sha256"])):
            raise ValueError("MG46_ORIGINAL_SELECTED_ACTION_CHAIN_INVALID")
        v=event_metric(e)
        count.update(v)
        a=e["action"];hist[a]+=1
        contexts.add(e["before_sha256"])
        afters.append(e["after_sha256"])
        if v["target_any_visible_frames"]:
            target_contexts.add(e["before_sha256"])
            if first_target is None:first_target=i
        if v["locked_door_front_frames"]:
            door_contexts.add(e["before_sha256"])
            if first_door is None:first_door=i
    if (len(contexts)!=ep["unique_public_views"]
        or count["positive_terminal_goal_steps"]!=ep["original_terminal_goal_rewards"]
        or count["actions"]!=len(actions)
        or count["actions"]!=ep["observed_public_changes"]+count["public_no_change_frames"]):
        raise ValueError("MG46_ORIGINAL_PUBLIC_EPISODE_SUMMARY_MISMATCH")
    midpoint=len(actions)//2
    halves=[]
    for section in (actions[:midpoint],actions[midpoint:]):
        totals=collections.Counter()
        for e in section:totals.update(event_metric(e))
        halves.append({
            "source_actions":len(section),
            "target_visible":totals["target_any_visible_frames"],
            "locked_door_front":totals["locked_door_front_frames"],
            "forward_no_public_change":totals["forward_no_public_change"]})
    return {"family":ep["family"],"role":ep["role"],
       "seed":ep["seed_dev_exposed"],
       "source_actions":len(actions),
       "positive_goal_episode":int(count["positive_terminal_goal_steps"]>0),
       "target_visible_frames":count["target_any_visible_frames"],
       "target_front_frames":count["target_front_frames"],
       "target_selected_pickup_attempts":count["target_front_selected_pickup_attempts"],
       "actual_target_selected_pickup_effects":count["target_front_selected_effects"],
       "locked_door_front_frames":count["locked_door_front_frames"],
       "locked_door_selected_toggles":count["locked_door_toggle_attempts"],
       "real_locked_door_openings":count["locked_door_openings"],
       "selected_forward":count["selected_forward"],
       "forward_no_public_change":count["forward_no_public_change"],
       "public_no_change":count["public_no_change_frames"],
       "unique_public_contexts":len(contexts),
       "unique_public_target_contexts":len(target_contexts),
       "unique_locked_door_contexts":len(door_contexts),
       "first_target_visible_selected_step":first_target,
       "first_locked_door_front_selected_step":first_door,
       "lag2_identical_public_after":sum(afters[i]==afters[i-2] for i in range(2,len(afters))),
       "lag4_identical_public_after":sum(afters[i]==afters[i-4] for i in range(4,len(afters))),
       "action_histogram":hist,
       "first_second_halves":halves,
       "release_triggers":ep.get("release_triggers",0),
       "real_public_release_effects":ep.get("release_actual_public_effects",0),
       "target_retry_count":ep.get("release_retry_target_attempts",0)}

def audit(s,p):
    parent=p["parent"]
    if (s["classification"]!=parent["original_negative"]
        or s["original_selected_action_count"]!=27514
        or s["unchanged_mg44_source_blob_sha1"]!=parent["mg44_policy_blob"]
        or s["family_source_registration_blob_sha1"]!=p["source_pins"]["original_Farama_registry_blob"]
        or s["source_original_Farama"]!=p["source_pins"]["original_Farama"]
        or s["exposed_transfer_DEV_seeds"]!=p["seeds"]
        or s["scientific_first_use"] is not False
        or s["independent_sealed_scientific_witness"] is not False
        or s["native_full_compute_energy_parity_qualified"] is not False
        or s["native_models_or_controllers_modified"] is not False
        or s["zero_external_actions"] is not True):
        raise ValueError("MG46_ORIGINAL_MG45_FROZEN_NEGATIVE_OR_SOURCE_CHANGED")
    episodes=s["original_144_episodes"]
    expected={(f,role,seed) for f,seeds in zip(FAMILIES,SEEDS)
              for role in ROLES for seed in seeds}
    if len(episodes)!=144 or len(expected)!=144:
        raise ValueError("MG46_ORIGINAL_COHORT_INCOMPLETE")
    seen=set()
    totals=collections.defaultdict(collections.Counter)
    hist=collections.defaultdict(lambda:[0]*7)
    per_ep=[]
    for ep in episodes:
        key=(ep["family"],ep["role"],ep["seed_dev_exposed"])
        if key in seen or key not in expected:
            raise ValueError("MG46_ORIGINAL_SOURCE_ROLE_DUPLICATED_OR_UNREGISTERED")
        seen.add(key)
        row=episode_metrics(ep)
        per_ep.append(row)
        pair=key[:2]
        for metric in ("source_actions","positive_goal_episode","target_visible_frames",
            "target_front_frames","target_selected_pickup_attempts",
            "actual_target_selected_pickup_effects","locked_door_front_frames",
            "locked_door_selected_toggles","real_locked_door_openings",
            "selected_forward","forward_no_public_change","public_no_change",
            "unique_public_contexts","unique_public_target_contexts",
            "unique_locked_door_contexts","lag2_identical_public_after",
            "lag4_identical_public_after","release_triggers",
            "real_public_release_effects","target_retry_count"):
            totals[pair][metric]+=row[metric]
        for i,v in enumerate(row["action_histogram"]):hist[pair][i]+=v
    if seen!=expected or sum(q["source_actions"] for q in totals.values())!=27514:
        raise ValueError("MG46_ORIGINAL_ALL_ROLE_SOURCE_ACTIONS_NOT_REPRODUCED")
    per_family=[]
    mapping={"source_actions":"actions","positive_goal_episode":"positive_goal_episodes",
         "target_visible_frames":"target_visible_frames",
         "target_front_frames":"target_front_frames",
         "target_selected_pickup_attempts":"selected_target_pickup_attempts",
         "actual_target_selected_pickup_effects":"actual_selected_target_pickup_effects",
         "real_locked_door_openings":"real_door_openings",
         "release_triggers":"release_public_triggers",
         "real_public_release_effects":"release_public_effects"}
    for f in FAMILIES:
        for role in ROLES:
            key=(f,role)
            rec=totals[key]
            orig=s["per_family_per_role"][f][role]
            for new,old in mapping.items():
                if rec[new]!=orig[old]:
                    raise ValueError("MG46_ORIGINAL_AGGREGATE_METRIC_DRIFT:"+f+":"+role+":"+new)
            if hist[key]!=orig["action_histogram"]:
                raise ValueError("MG46_ORIGINAL_ACTION_HISTOGRAM_DRIFT")
            per_family.append({"family":f,"role":role,**dict(rec),
                "action_histogram":hist[key],"episodes":3})
    k=(FAMILIES[0],CANDIDATE)
    kk=(FAMILIES[1],CANDIDATE)
    if (totals[k]["target_visible_frames"]!=0
        or totals[kk]["target_visible_frames"]!=0
        or totals[k]["release_triggers"]!=0
        or totals[kk]["release_triggers"]!=0):
        raise ValueError("MG46_PREDECLARED_TARGET_ABSENCE_HYPOTHESIS_FALSIFIED")
    any_seen_by_all_roles={
       f:sum(totals[(f,role)]["target_visible_frames"] for role in ROLES)
       for f in FAMILIES}
    no_target_all_roles=all(any_seen_by_all_roles[f]==0 for f in FAMILIES[:2])
    result={"schema":"itd02.mg46.authenticated-mg45-public-approach-retrospective.v1",
        "classification":p["classification_valid"],
        "preserved_original_mg45_negative":s["classification"],
        "original_144_role_episodes":144,
        "original_selected_actions":27514,
        "original_Farama_env_actions_in_MG46_audit":0,
        "scientific_first_use":False,
        "original_source_sha256":SOURCE_SHA,
        "original_archive_sha256":ZIP_SHA,
        "new_family_approach_diagnosis":{
          "larger_keycorridors_zero_exact_public_target_exposure_all_16_controls":
            no_target_all_roles,
          "target_visible_original_frames_by_environment_all_roles":
            any_seen_by_all_roles,
          "candidate_unchanged_MG44_larger_keycorridor":{
            f:dict(totals[(f,CANDIDATE)]) for f in FAMILIES[:2]},
          "release_disabled_larger_keycorridor":{
            f:dict(totals[(f,DISABLED)]) for f in FAMILIES[:2]},
          "interpretation":"No publicly observed mission-target encounter, not a demonstrated failed release intervention; observed egocentric contexts never establish physical map coverage or reachability."},
        "per_family_per_role":per_family,
        "per_episode":sorted(per_ep,key=lambda x:(x["family"],x["role"],x["seed"]))}
    result["audit_sha256"]=digest(result)
    return result

def run(archive,output):
    p=preflight()
    if hashlib.sha256(archive.read_bytes()).hexdigest()!=ZIP_SHA:
        raise ValueError("MG46_ORIGINAL_GITHUB_SOURCE_ARCHIVE_SHA_MISMATCH")
    with zipfile.ZipFile(archive) as z:
        if set(z.namelist())!={
           "comparison.log","first-resources.json","first.json","first.log",
           "mg33c-synthetic.json","second-resources.json","second.json","second.log"}:
            raise ValueError("MG46_SOURCE_ARCHIVE_LAYOUT_CHANGED")
        for fname in ("first.json","second.json"):
            with z.open(fname) as fp: envelope=json.load(fp)
            if (envelope.get("canonical_source_sha256")!=SOURCE_SHA
                or digest(envelope["source"])!=SOURCE_SHA
                or envelope.get("schema")!="itd02.mg45.unmodified-mg44-transfer-original-family.dev-source.v1"):
                raise ValueError("MG46_INDEPENDENT_ORIGINAL_SOURCE_DIGEST_INVALID:"+fname)
            if fname=="first.json":
                summary=audit(envelope["source"],p)
            del envelope
        if SOURCE_SHA not in z.read("comparison.log").decode("utf-8"):
            raise ValueError("MG46_MG45_REPRODUCTION_LOG_MISSING")
        for fname in ("first-resources.json","second-resources.json"):
            with z.open(fname) as fp:resources=json.load(fp)
            if (len(resources["records"])!=144
                or resources["original_source_sha256"]!=SOURCE_SHA):
                raise ValueError("MG46_AUXILIARY_RESOURCE_SOURCE_ASSOCIATION_INVALID")
    output.write_text(json.dumps(summary,sort_keys=True,indent=2)+"\n",
                     encoding="utf-8")
    print("MG46_ORIGINAL_MG45_DUAL_PROCESS_SOURCE_CUSTODY_PASS",SOURCE_SHA)
    print("MG46_ORIGINAL_SOURCE_TARGET_EXPOSURE_ALL_ROLES",json.dumps(
        summary["new_family_approach_diagnosis"]["target_visible_original_frames_by_environment_all_roles"],
        sort_keys=True))
    print("MG46_ORIGINAL_MG45_APPROACH_AUDIT_SHA256",summary["audit_sha256"])
    print("MG46_FROZEN_RETROSPECTIVE_CLASSIFICATION",summary["classification"])

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--preflight",action="store_true")
    ap.add_argument("--archive",type=Path)
    ap.add_argument("--output",type=Path)
    a=ap.parse_args()
    if a.preflight:preflight();return
    if not a.archive or not a.output:
        ap.error("require --archive and --output")
    run(a.archive,a.output)

if __name__=="__main__":main()
