#!/usr/bin/env python3
"""MG41 source-custodied retrospective audit of original MG40 reversible effects.

Never creates/steps original MiniGrid environments. Counts selected public
effects/revisits, NOT inferred inventory, physical regions or counterfactuals.
"""
from __future__ import annotations
import argparse,collections,hashlib,json,zipfile
from pathlib import Path
from mg37_mg36_navigation_audit import event_metric,digest

HERE=Path(__file__).resolve().parent
PREREG=HERE/"mg41_mg40_public_effect_cycles_prereg.json"
EXPECTED_SOURCE="bf17aae4f7b5ceecbfa754f0cc797653648580db78d661a012d739fcb0ea8f27"
EXPECTED_ARCHIVE="112e485ccadc8f395264dbf9b490773b8c5add3382cdb3b234405eca427995e7"
FIELDS=("actions","target_visible","target_front","target_pick_attempt",
        "target_pick_effect","selected_drops","selected_drops_empty_front",
        "actual_public_drop_effects","actual_public_generic_pickup_effects",
        "door_open","positive_goal_episodes")

def frozen():
    p=json.loads(PREREG.read_text(encoding="utf8"))
    parent=p["parent"]
    if (p["schema"]!="itd02.mg41.exposed-mg40-public-action-cycle-audit.v1"
        or p["phase"]!="RETROSPECTIVE_METRICS_FROZEN_BEFORE_AUDIT_EXECUTABLE"
        or p["scope"]!="AUTHENTIC_MG40_ARCHIVED_SOURCE_ONLY_ZERO_NEW_WORLD_ACTIONS"
        or parent["mg40_head"]!="a39c7224debbe16077bbd88e84116d8d9dde827d"
        or parent["mg40_run"]!=40954119154
        or parent["mg40_artifact"]!=12933106228
        or parent["archive_sha256"]!=EXPECTED_ARCHIVE
        or parent["canonical_original_sha256"]!=EXPECTED_SOURCE
        or parent["episodes"]!=132 or parent["selected_actions"]!=24719
        or p["metrics"]["lag_revisits"]!=[2,4,8,16]
        or not all(p["prohibitions"].values())
        or not all(p["source_custody"].values())):
        raise ValueError("MG41_FROZEN_PROTOCOL_ORIGINAL_SOURCE_CHANGED")
    return p

def observed_effect(e):
    before=e["before"];after=e["after"]
    bf=before["image"][3][5]; af=after["image"][3][5]
    same=before["direction"]==after["direction"]
    return (e["action"]==3 and same and bf[0] in (5,6,7) and af[0]==1,
            e["action"]==4 and same and bf[0]==1 and af[0] in (5,6,7))

def lag_revisits(after_hashes):
    return {f"lag_{n}_public_revisit":sum(after_hashes[i]==after_hashes[i-n]
        for i in range(n,len(after_hashes))) for n in (2,4,8,16)}

def reversible_pairs(events):
    pending=[]
    pairs=[]
    for index,e in enumerate(events):
        pickup,drop=observed_effect(e)
        if pickup:
            pending.append(index)
        if drop and pending:
            prior=pending.pop()
            gap=index-prior
            if gap<=16:
                pairs.append((prior+1,index+1,gap))
    return {"reversible_pickup_then_drop_within_4":sum(z[2]<=4 for z in pairs),
            "reversible_pickup_then_drop_within_16":len(pairs),
            "reversible_pair_original_source_indices":[[a,b] for a,b,_ in pairs]}

def measure_episode(ep):
    events=ep["source_events"]
    if (not 1<=len(events)<=192
        or ep["original_source_actions"]!=len(events)
        or digest(events)!=ep["source_events_sha256"]
        or digest(events[0]["before"])!=ep["public_start_sha256"]):
        raise ValueError("MG41_ORIGINAL_EPISODE_LENGTH_OR_DIGEST_CHANGED")
    counts=collections.Counter()
    after_hashes=[]
    hist=[0]*7
    unique_before=set()
    pickup=drop=0
    for i,e in enumerate(events):
        if (e["index"]!=i+1 or e["mission"]!=ep["original_public_mission"]
            or e["before"]["mission"]!=ep["original_public_mission"]
            or e["after"]["mission"]!=ep["original_public_mission"]
            or e["external_actions"]!=0
            or type(e["action"]) is not int or e["action"] not in range(7)
            or digest(e["before"])!=e["before_sha256"]
            or digest(e["after"])!=e["after_sha256"]
            or (i and e["before_sha256"]!=events[i-1]["after_sha256"])):
            raise ValueError("MG41_ORIGINAL_SELECTED_EVENT_OR_PUBLIC_CHAIN_INVALID")
        x=event_metric(e)
        hist[e["action"]]+=1
        unique_before.add(e["before_sha256"])
        after_hashes.append(e["after_sha256"])
        counts["target_visible"]+=x["target_any_visible_frames"]
        counts["target_front"]+=x["target_front_frames"]
        counts["target_pick_attempt"]+=x["target_front_selected_pickup_attempts"]
        counts["target_pick_effect"]+=x["target_front_selected_effects"]
        counts["door_open"]+=x["locked_door_openings"]
        counts["public_unchanged"]+=int(e["before_sha256"]==e["after_sha256"])
        counts["positive_reward_steps"]+=x["positive_terminal_goal_steps"]
        pick,dr=observed_effect(e)
        pickup+=int(pick);drop+=int(dr)
        if e["action"]==4:
            counts["selected_drops"]+=1
            if e["before"]["image"][3][5][0]==1:
                counts["selected_drops_empty_front"]+=1
        if i and events[i-1]["action"]==3 and e["action"]==4:
            counts["adjacent_selected_pickup_drop"]+=1
        if i and events[i-1]["action"]==4 and e["action"]==3:
            counts["adjacent_selected_drop_pickup"]+=1
        counts["actions"]+=1
    if (len(unique_before)!=ep["unique_public_views"]
        or len(set(hist))<0
        or sum(hist)!=len(events)
        or ep["observed_public_changes"]+counts["public_unchanged"]!=len(events)
        or ep["original_terminal_goal_rewards"]!=counts["positive_reward_steps"]):
        raise ValueError("MG41_ORIGINAL_EPISODE_REPRODUCTION_INVARIANT_FAIL")
    halfway=len(events)//2
    halves=[]
    for part in (events[:halfway],events[halfway:]):
        halves.append({"selected_actions":len(part),
             "target_visible_frames":sum(event_metric(e)["target_any_visible_frames"] for e in part),
             "target_front_frames":sum(event_metric(e)["target_front_frames"] for e in part),
             "selected_pickup_effects":sum(observed_effect(e)[0] for e in part),
             "selected_drop_effects":sum(observed_effect(e)[1] for e in part)})
    pairs=reversible_pairs(events)
    return {"family":ep["family"],"role":ep["role"],"seed":ep["seed_dev_exposed"],
        "actions":len(events),"positive_goal_episode":int(counts["positive_reward_steps"]>0),
        "target_visible_frames":counts["target_visible"],"target_front_frames":counts["target_front"],
        "selected_target_pickup_attempts":counts["target_pick_attempt"],
        "selected_target_pickup_effects":counts["target_pick_effect"],
        "public_pickup_effects":pickup,"public_drop_effects":drop,
        "selected_drop_actions":counts["selected_drops"],
        "selected_drop_front_empty":counts["selected_drops_empty_front"],
        "actual_door_openings":counts["door_open"],
        "adjacent_selected_pickup_drop":counts["adjacent_selected_pickup_drop"],
        "adjacent_selected_drop_pickup":counts["adjacent_selected_drop_pickup"],
        "public_unchanged_actions":counts["public_unchanged"],
        "unique_public_before_contexts":len(unique_before),
        "action_histogram":hist,"first_second_episode_halves":halves,
        **lag_revisits(after_hashes),**pairs}

def audit(source,p):
    if (source["classification"]!=p["parent"]["mg40_frozen_classification"]
        or source["original_selected_action_count"]!=24719
        or source["exposed_dev_seeds"]!=p["seeds"]
        or source["scientific_first_use"] is not False
        or source["mg28_native_rollout_permitted"] is not False
        or source["native_models_or_controllers_modified"] is not False
        or source["native_resource_parity_qualified"] is not False
        or source["zero_external_actions"] is not True):
        raise ValueError("MG41_FROZEN_ORIGINAL_MG40_NO_SCIENCE_BOUNDARY_CHANGED")
    episodes=source["original_132_episodes"]
    if len(episodes)!=132:
        raise ValueError("MG41_NOT_132_ORIGINAL_EPISODES")
    expected={(f,r,s) for f,seeds in zip(p["families"],p["seeds"])
              for r in p["roles"] for s in seeds}
    if len(expected)!=132:raise ValueError("MG41_INVALID_FROZEN_ROLE_MATRIX")
    found=set()
    reports=[]
    sums=collections.defaultdict(collections.Counter)
    hist=collections.defaultdict(lambda:[0]*7)
    for ep in episodes:
        identity=(ep["family"],ep["role"],ep["seed_dev_exposed"])
        if identity not in expected or identity in found:
            raise ValueError("MG41_MISSING_OR_DUPLICATE_ORIGINAL_ROLE_FAMILY_SEED")
        found.add(identity)
        row=measure_episode(ep)
        reports.append(row)
        key=identity[:2]
        for metric in ("actions","positive_goal_episode","target_visible_frames",
                       "target_front_frames","selected_target_pickup_attempts",
                       "selected_target_pickup_effects","public_pickup_effects",
                       "public_drop_effects","selected_drop_actions",
                       "selected_drop_front_empty","actual_door_openings",
                       "adjacent_selected_pickup_drop","adjacent_selected_drop_pickup",
                       "public_unchanged_actions","unique_public_before_contexts",
                       "reversible_pickup_then_drop_within_4",
                       "reversible_pickup_then_drop_within_16",
                       "lag_2_public_revisit","lag_4_public_revisit",
                       "lag_8_public_revisit","lag_16_public_revisit"):
            sums[key][metric]+=row[metric]
        for i,v in enumerate(row["action_histogram"]):hist[key][i]+=v
    if found!=expected or sum(v["actions"] for v in sums.values())!=24719:
        raise ValueError("MG41_ORIGINAL_SOURCE_IDENTITY_OR_STEP_COUNT_DRIFT")
    aggregated=[]
    for (family,role),counts in sorted(sums.items()):
        prior=source["per_family_per_role"][family][role]
        mapping={"actions":"actions","target_visible_frames":"target_visible",
                 "target_front_frames":"target_front",
                 "selected_target_pickup_attempts":"target_pick_attempt",
                 "selected_target_pickup_effects":"target_pick_effect",
                 "public_pickup_effects":"actual_public_generic_pickup_effects",
                 "public_drop_effects":"actual_public_drop_effects",
                 "selected_drop_actions":"selected_drops",
                 "selected_drop_front_empty":"selected_drops_empty_front",
                 "actual_door_openings":"door_open",
                 "positive_goal_episode":"positive_goal_episodes"}
        for metric,original in mapping.items():
            if counts[metric]!=prior[original]:
                raise ValueError("MG41_EXACT_ORIGINAL_PER_ROLE_METRIC_DRIFT:"+family+":"+role+":"+metric)
        if hist[(family,role)]!=prior["action_histogram"]:
            raise ValueError("MG41_ORIGINAL_SELECTED_ACTION_HISTOGRAM_DRIFT")
        aggregated.append({"family":family,"role":role,
                           **{k:counts[k] for k in counts},
                           "selected_action_histogram":hist[(family,role)],
                           "episodes":3})
    enabled="mg40_precondition_memory_enabled"
    disabled="mg40_precondition_memory_ablated"
    unfamiliar=p["families"][1:]
    def total(role,metric):
        return sum(sums[(family,role)][metric] for family in unfamiliar)
    pair={
      role:{metric:total(role,metric) for metric in (
          "actions","positive_goal_episode","target_visible_frames",
          "selected_target_pickup_effects","public_pickup_effects",
          "public_drop_effects","adjacent_selected_pickup_drop",
          "adjacent_selected_drop_pickup",
          "reversible_pickup_then_drop_within_4",
          "reversible_pickup_then_drop_within_16",
          "lag_2_public_revisit","lag_4_public_revisit",
          "lag_8_public_revisit","lag_16_public_revisit")}
      for role in (enabled,disabled,
                   "mg38_generic_affordance_prior_enabled_exact_source",
                   "mg39b_generic_affordance_prior_removed")}
    if total(enabled,"public_drop_effects")!=244 or total(disabled,"public_drop_effects")!=0:
        raise ValueError("MG41_ORIGINAL_MG40_244_VS_0_DROP_EVIDENCE_CHANGED")
    return {"classification":p["classification_if_valid"],
         "original_classification_unchanged":source["classification"],
         "original_source_episodes":132,"original_selected_actions":24719,
         "original_Farama_env_step_calls_in_this_audit":0,
         "scientific_first_use":False,
         "hidden_inventory_or_geographic_location_inferred":False,
         "paired_exposed_unfamiliar_family_summary":pair,
         "per_family_role":aggregated,
         "per_episode":sorted(reports,key=lambda q:(q["family"],q["role"],q["seed"]))}

def run(archive,output):
    p=frozen()
    file_sha=hashlib.sha256(archive.read_bytes()).hexdigest()
    if file_sha!=EXPECTED_ARCHIVE:
        raise ValueError("MG41_ORIGINAL_MG40_ARCHIVE_DIGEST_MISMATCH")
    with zipfile.ZipFile(archive) as z:
        if set(z.namelist())!={"first.json","first.log","second.json",
                               "second.log","comparison.log","mg33c-synthetic.json"}:
            raise ValueError("MG41_ORIGINAL_SOURCE_ARTIFACT_LAYOUT_CHANGED")
        with z.open("first.json") as f:a=json.load(f)
        if (a["canonical_source_sha256"]!=EXPECTED_SOURCE
            or digest(a["source"])!=EXPECTED_SOURCE):
            raise ValueError("MG41_FIRST_REAL_SOURCE_CANONICAL_HASH_INVALID")
        report=audit(a["source"],p)
        del a
        with z.open("second.json") as f:b=json.load(f)
        if (b["canonical_source_sha256"]!=EXPECTED_SOURCE
            or digest(b["source"])!=EXPECTED_SOURCE):
            raise ValueError("MG41_SECOND_ORIGINAL_REAL_SOURCE_NOT_IDENTICAL")
        if EXPECTED_SOURCE not in z.read("comparison.log").decode("utf8"):
            raise ValueError("MG41_ARCHIVED_REPRODUCTION_COMPARISON_UNQUALIFIED")
        del b
    receipt=digest(report)
    report["original_source_sha256"]=EXPECTED_SOURCE
    report["archived_source_zip_sha256"]=file_sha
    report["audit_sha256"]=receipt
    output.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n",encoding="utf8")
    print(report["classification"])
    print("MG41_ORIGINAL_MG40_DUAL_PROCESS_SOURCE_CUSTODY_PASS",receipt)
    print("MG41_PUBLIC_EFFECT_LOOP_DESCRIPTIVE_DIAGNOSIS",
          json.dumps(report["paired_exposed_unfamiliar_family_summary"],sort_keys=True))

def preflight():
    p=frozen()
    assert p["parent"]["selected_actions"]==24719
    before={"image":[[[1,0,0] for _ in range(7)] for _ in range(7)],
            "direction":0,"mission":"pick up the red box"}
    after=dict(before,image=[[cell[:] for cell in row] for row in before["image"]])
    before["image"][3][5]=[7,0,0]
    e1={"action":3,"before":before,"after":after}
    b2={"image":[[cell[:] for cell in row] for row in after["image"]],
        "direction":0,"mission":"pick up the red box"}
    b2["image"][3][5]=[1,0,0]
    e2={"action":4,"before":b2,"after":before}
    assert observed_effect(e1)==(True,False)
    assert observed_effect(e2)==(False,True)
    assert reversible_pairs([e1,e2])["reversible_pickup_then_drop_within_4"]==1
    assert lag_revisits(["a","b","a","b"])["lag_2_public_revisit"]==2
    print("MG41_DUAL_HOST_FROZEN_SOURCE_ONLY_LOOP_AUDIT_PREFLIGHT_PASS")

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--preflight",action="store_true")
    ap.add_argument("--archive",type=Path)
    ap.add_argument("--output",type=Path)
    opt=ap.parse_args()
    if opt.preflight:preflight();return
    if not opt.archive or not opt.output:ap.error("--archive and --output required")
    run(opt.archive,opt.output)
if __name__=="__main__":main()
