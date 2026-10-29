#!/usr/bin/env python3
"""MG39 read-only authentic original MG38 selected pickup consequence diagnosis.

Never constructs or steps a MiniGrid world, runs native models, or imputes
hidden inventory. Both source copies checked against original byte custody.
"""
from __future__ import annotations
import argparse, collections, hashlib, json, zipfile
from pathlib import Path
from mg37_mg36_navigation_audit import event_metric, digest, MISSION, COLORS, TYPES

HERE = Path(__file__).resolve().parent
PREREG = HERE / "mg39_mg38_pickup_audit_prereg.json"
METRICS = ("actions", "target_any_visible_frames", "target_front_frames",
           "target_front_selected_pickup_attempts","target_front_selected_effects",
           "locked_door_openings","positive_terminal_goal_steps",
           "selected_turn_left","selected_turn_right","selected_forward",
           "forward_no_public_change","public_no_change_frames")


def frozen():
    p = json.loads(PREREG.read_text(encoding="utf8"))
    x = p["parent"]
    if (p["schema"] != "itd02.mg39.original-selected-public-pickup-precondition-exposed-audit.v1"
        or p["phase"] != "RETROSPECTIVE_METHOD_FROZEN_BEFORE_EXECUTABLE"
        or p["scope"] != "MG38_EXPOSED_DEV_READONLY_NO_NEW_ORIGINAL_WORLD_ACTIONS"
        or x["mg38_head"] != "5512fa26a55484ebd5e0db1c3927c396ab231cdf"
        or x["run_id"] != 40951093910 or x["artifact_id"] != 12930423838
        or x["archive_sha256"] != "0e3800d2ba42c2cdfa41e3cb13430e624482291e21b7d1d78322d2a0375dd556"
        or x["original_source_sha256"] != "42faea659d94c5527530f7a932d1fa0c4a409213e06733f4a9216f2db65b1fc7"
        or x["original_episodes"] != 120 or x["original_selected_actions"] != 22307
        or not all(p["frozen_engineering"].values())
        or not all(p["prohibitions"].values())):
        raise ValueError("MG39_SOURCE_CUSTODY_OR_FROZEN_DESIGN_DRIFT")
    return p


def case_category(before_front, after_front):
    if after_front[0] == 1:
        return "empty"
    if after_front == before_front:
        return "same_exact_target"
    if after_front[0] == before_front[0]:
        return "other_target_color_or_state"
    return "different_public_object"


def audit_original(source, p):
    x=p["parent"]
    if (source["classification"] != x["original_classification"]
        or source["original_selected_action_count"] != x["original_selected_actions"]
        or source["scientific_first_use"] is not False
        or source["mg28_native_rollout_permitted"] is not False
        or source["native_models_or_controllers_modified"] is not False
        or source["zero_external_actions"] is not True
        or source["native_resource_parity_qualified"] is not False
        or source["exposed_dev_seeds"] != p["seeds"]):
        raise ValueError("MG39_FROZEN_ORIGINAL_NEGATIVE_OR_SOURCE_BOUNDARY_CHANGED")
    episodes=source["original_120_episodes"]
    if len(episodes)!=120:
        raise ValueError("MG39_ORIGINAL_EPISODE_COUNT_DRIFT")
    expected={(f,role,seed)
        for f,seeds in zip(p["families"],p["seeds"])
        for role in p["roles"] for seed in seeds}
    if len(expected)!=120:
        raise ValueError("MG39_INVALID_FROZEN_IDENTITY_MATRIX")
    found=set()
    group_sums=collections.defaultdict(collections.Counter)
    goals=collections.Counter()
    episode_reports=[]
    cases=[]
    context_any=collections.defaultdict(set)
    context_front=collections.defaultdict(set)
    hist=collections.defaultdict(lambda:[0]*7)
    for ep in episodes:
        identity=(ep["family"],ep["role"],ep["seed_dev_exposed"])
        if identity not in expected or identity in found:
            raise ValueError("MG39_DUPLICATE_OR_UNEXPECTED_SOURCE_EPISODE")
        found.add(identity)
        evs=ep["source_events"]
        if len(evs)!=ep["original_source_actions"] or not (1<=len(evs)<=192):
            raise ValueError("MG39_SELECTED_EVENT_COUNT_DRIFT")
        if digest(evs)!=ep["source_events_sha256"]:
            raise ValueError("MG39_EPISODE_SELECTED_EVENT_HASH_DRIFT")
        counts=collections.Counter()
        prior_selected=collections.Counter()
        for index,e in enumerate(evs,1):
            if e["index"]!=index or e["mission"]!=ep["original_public_mission"]:
                raise ValueError("MG39_EVENT_ORDER_OR_MISSION_DRIFT")
            measures=event_metric(e)
            counts.update(measures)
            group=identity[:2]
            action=e["action"]
            hist[group][action]+=1
            if measures["target_any_visible_frames"]:
                context_any[group].add(e["before_sha256"])
            if measures["target_front_frames"]:
                context_front[group].add(e["before_sha256"])
            if measures["target_front_selected_pickup_attempts"]:
                before_front=e["before"]["image"][3][5]
                after_front=e["after"]["image"][3][5]
                kind=case_category(before_front,after_front)
                # For an action3 selected at exact public target front, the
                # direction change would also invalidate original pickup-effect
                # classification; keep a separate status without inferring cause.
                if kind=="empty" and e["before"]["direction"]!=e["after"]["direction"]:
                    kind="empty_but_direction_changed"
                cases.append({
                    "family":identity[0],"role":identity[1],"seed":identity[2],
                    "step":index,
                    "before_sha256":e["before_sha256"],
                    "after_sha256":e["after_sha256"],
                    "before_front":before_front,"after_front":after_front,
                    "after_category":kind,
                    "original_observed_effect":bool(measures["target_front_selected_effects"]),
                    "original_positive_terminal":bool(measures["positive_terminal_goal_steps"]),
                    "before_after_public_digest_changed":e["before_sha256"]!=e["after_sha256"],
                    "direction_changed":e["before"]["direction"]!=e["after"]["direction"],
                    "prior_selected_pickup_actions_in_episode":prior_selected[3],
                    "prior_selected_drop_actions_in_episode":prior_selected[4],
                    "prior_selected_toggle_actions_in_episode":prior_selected[5]})
            prior_selected[action]+=1
        if (counts["actions"]!=len(evs)
            or counts["positive_terminal_goal_steps"]!=ep["original_terminal_goal_rewards"]
            or counts["public_no_change_frames"]+ep["observed_public_changes"]!=len(evs)
            or len({e["before_sha256"] for e in evs})!=ep["unique_public_views"]):
            raise ValueError("MG39_ORIGINAL_EPISODE_SOURCE_SUMMARY_NOT_REPRODUCED")
        group_sums[identity[:2]].update(counts)
        goals[identity[:2]]+=int(counts["positive_terminal_goal_steps"]>0)
        episode_reports.append({"family":identity[0],"role":identity[1],"seed":identity[2],
            **{k:counts[k] for k in METRICS},
            "observed_positive_goal":counts["positive_terminal_goal_steps"]>0})
    if found!=expected or sum(m["actions"] for m in group_sums.values())!=22307:
        raise ValueError("MG39_SOURCE_MATRIX_OR_ACTION_COUNT_MISMATCH")
    report_rows=[]
    for identity in sorted(group_sums):
        v=group_sums[identity]
        prior=source["per_family_per_role"][identity[0]][identity[1]]
        for this,older in (("actions","actions"),("target_front_frames","target_front"),
            ("target_front_selected_pickup_attempts","target_pick_attempt"),
            ("target_front_selected_effects","target_disappearance"),
            ("locked_door_openings","door_open"),
            ("positive_terminal_goal_steps","positive_goal")):
            if v[this]!=prior[older]:
                raise ValueError("MG39_ORIGINAL_ROLE_METRIC_DRIFT:"+str(identity)+":"+this)
        if goals[identity]!=prior["positive_goal_episodes"] or hist[identity]!=prior["action_histogram"]:
            raise ValueError("MG39_ORIGINAL_GOAL_OR_ACTION_HISTOGRAM_DRIFT")
        if (sum(hist[identity])!=v["actions"] or
            hist[identity][0]+hist[identity][1]!=v["selected_turn_left"]+v["selected_turn_right"]):
            raise ValueError("MG39_ACTION_DIVERSITY_CUSTODY_DRIFT")
        report_rows.append({
            "family":identity[0],"role":identity[1],
            **{k:v[k] for k in METRICS},
            "positive_goal_episodes":goals[identity],
            "unique_public_target_visible_views":len(context_any[identity]),
            "unique_public_target_front_views":len(context_front[identity]),
            "selected_action_histogram":hist[identity]})
    if len(report_rows)!=40:
        raise ValueError("MG39_MISSING_ORIGINAL_ROLE_FAMILY_CROSSPRODUCT")
    categories=collections.Counter(z["after_category"] for z in cases)
    selected_role="navigation_aware_empirical_model_candidate"
    subset=[z for z in cases if z["role"]==selected_role and z["family"] in p["families"][1:]]
    subset_categories=collections.Counter(z["after_category"] for z in subset)
    original_effect=sum(z["original_observed_effect"] for z in subset)
    if original_effect!=sum(v["target_front_selected_effects"] for v in report_rows
                           if v["role"]==selected_role and v["family"] in p["families"][1:]):
        raise ValueError("MG39_SELECTED_TARGET_EFFECT_TALLY_DISAGREEMENT")
    if len(subset)!=sum(v["target_front_selected_pickup_attempts"] for v in report_rows
                       if v["role"]==selected_role and v["family"] in p["families"][1:]):
        raise ValueError("MG39_SELECTED_TARGET_ATTEMPTS_DISAGREE")
    return {
        "classification":p["classification_if_pass"],
        "original_classification_unchanged":source["classification"],
        "scientific_first_use":False,"new_original_source_env_steps":0,
        "model_or_controller_changes":False,
        "original_episodes":120,"original_selected_action_count":22307,
        "per_family_per_role":report_rows,
        "per_episode":sorted(episode_reports,key=lambda z:(z["family"],z["role"],z["seed"])),
        "exact_selected_target_pickup_cases":sorted(cases,
             key=lambda z:(z["family"],z["role"],z["seed"],z["step"])),
        "all_roles_pickup_outcome_categories":dict(sorted(categories.items())),
        "navigation_candidate_unfamiliar_pickup_attempts":len(subset),
        "navigation_candidate_unfamiliar_pickup_public_after_categories":dict(sorted(subset_categories.items())),
        "navigation_candidate_unfamiliar_real_pickup_effects":original_effect,
        "unobservable_carry_or_task_preconditions":"UNKNOWN_FROM_PUBLIC_SOURCE"}


def run(original_archive,output):
    p=frozen()
    sha=hashlib.sha256(original_archive.read_bytes()).hexdigest()
    if sha!=p["parent"]["archive_sha256"]:
        raise ValueError("MG39_ORIGINAL_ARCHIVE_SHA256_CHANGED")
    with zipfile.ZipFile(original_archive) as z:
        if set(z.namelist())!={"first.json","second.json","first.log","second.log",
            "comparison.log","mg33c-synthetic.json"}:
            raise ValueError("MG39_UNEXPECTED_ORIGINAL_ARTIFACT_LAYOUT")
        a=json.loads(z.read("first.json")); b=json.loads(z.read("second.json"))
        for r in (a,b):
            if (r["canonical_source_sha256"]!=p["parent"]["original_source_sha256"]
                or digest(r["source"])!=r["canonical_source_sha256"]):
                raise ValueError("MG39_ORIGINAL_SOURCE_CANONICAL_HASH_DRIFT")
        if a["source"]!=b["source"]:
            raise ValueError("MG39_ORIGINAL_TWO_PROCESSES_NOT_IDENTICAL")
        if p["parent"]["original_source_sha256"] not in z.read("comparison.log").decode("utf-8"):
            raise ValueError("MG39_PRIOR_COMPARISON_LOG_SOURCE_HASH_MISMATCH")
        report=audit_original(a["source"],p)
    canonical=digest(report)
    report["source_archive_sha256"]=sha
    report["original_canonical_source_sha256"]=p["parent"]["original_source_sha256"]
    report["audit_receipt_canonical_sha256"]=canonical
    output.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    print(report["classification"])
    print("MG39_TWO_COMPLETE_ORIGINAL_PROCESSES_AUDITED_PASS",canonical)
    print("MG39_NAVIGATION_CANDIDATE_PICKUP_ATTEMPTS",report["navigation_candidate_unfamiliar_pickup_attempts"])
    print("MG39_NAVIGATION_CANDIDATE_AFTER_PUBLIC_CATEGORIES",
          json.dumps(report["navigation_candidate_unfamiliar_pickup_public_after_categories"],sort_keys=True))
    print("MG39_NAVIGATION_CANDIDATE_REAL_EFFECTS",
          report["navigation_candidate_unfamiliar_real_pickup_effects"])


def preflight():
    p=frozen()
    e={"action":3,"reward":1.0,"terminated":True,"external_actions":0,
       "mission":"pick up the red box",
       "before":{"direction":1,"mission":"pick up the red box",
         "image":[[[1,0,0] for _ in range(7)] for _ in range(7)]},
       "after":{"direction":1,"mission":"pick up the red box",
         "image":[[[1,0,0] for _ in range(7)] for _ in range(7)]}}
    e["before"]["image"][3][5]=[7,0,0]
    e["before_sha256"]=digest(e["before"])
    e["after_sha256"]=digest(e["after"])
    x=event_metric(e)
    if not (x["target_front_selected_pickup_attempts"]==1
            and x["target_front_selected_effects"]==1
            and case_category([7,0,0],[1,0,0])=="empty"
            and case_category([7,0,0],[7,0,0])=="same_exact_target"
            and case_category([7,0,0],[5,0,0])=="different_public_object"):
        raise ValueError("MG39_SYNTHETIC_PICKUP_POSITIVE_NEGATIVE_FAILED")
    if p["parent"]["original_episodes"]!=120:
        raise ValueError("MG39_PROTOCOL_NOT_FROZEN")
    print("MG39_CROSS_HOST_SOURCE_ONLY_PICKUP_CONSEQUENCE_PREFLIGHT_PASS_NO_SCIENCE")


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--preflight",action="store_true")
    parser.add_argument("--archive",type=Path)
    parser.add_argument("--output",type=Path)
    args=parser.parse_args()
    if args.preflight:
        preflight();return
    if not args.archive or not args.output:
        parser.error("--archive and --output required for immutable read-only audit")
    run(args.archive,args.output)


if __name__=="__main__":
    main()
