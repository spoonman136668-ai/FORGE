#!/usr/bin/env python3
"""MG51 independent read-only audit of exact original MG50 selected source.

No new Farama steps, no native actions, no policy updates or outcome relabeling.
Association of public observation change and later goal is not causality.
"""
from __future__ import annotations
import argparse,collections,gc,hashlib,json,re,subprocess,zipfile
from pathlib import Path

HERE=Path(__file__).resolve().parent
PRE=HERE/"mg51_mg50_goal_relevance_audit_prereg.json"
PARENT="9b4c85c02926a3591a9feff8b821e47e3b5c4668"
FREEZE="037c3237b3a34258fe81b7d184ec9d04447f9fff"
ZIP_SHA="94dce7d4643640620afd9e67b370bbd05bfd6fd60bf012301ed3c1f69c910527"
SOURCE_SHA="11117828e42b7876b2faa59b7cecd5ddee1fbc689ae01504517f414a5b9e5024"
FAMILIES=("MiniGrid-KeyCorridorS3R2-v0","MiniGrid-KeyCorridorS4R3-v0",
          "MiniGrid-ObstructedMaze-1Dl-v0")
SEEDS=((1071101,1071103,1071107),(1071201,1071203,1071207),
       (1071301,1071303,1071307))
TYPES={"key":5,"ball":6,"box":7}
COLORS={"red":0,"green":1,"blue":2,"purple":3,"yellow":4,"grey":5}
MISSION=re.compile(r"pick up the (red|green|blue|purple|yellow|grey) (key|ball|box)")

class HashWriter:
    def __init__(self):self.value=hashlib.sha256()
    def write(self,s):self.value.update(s.encode("ascii"))
def digest(value):
    writer=HashWriter()
    json.dump(value,writer,sort_keys=True,separators=(",",":"),
              ensure_ascii=True,allow_nan=False)
    return writer.value.hexdigest()
def git(*args):
    return subprocess.run(["git",*args],cwd=HERE.parents[1],
        capture_output=True,text=True,check=False)
def frozen():
    p=json.loads(PRE.read_text(encoding="utf8"))
    q=p["parent"]
    if (p["schema"]!="itd02.mg51.frozen-MG50-source-public-objective-relevance-retrospective.v1"
        or p["phase"]!="METRIC_PROTOCOL_FROZEN_BEFORE_MG51_EXECUTABLE_AND_ANY_DIAGNOSTIC_RESULT"
        or q["mg50_head"]!=PARENT or q["artifact_id"]!=12939728373
        or q["original_run"]!=40970913974
        or q["zip_sha256"]!=ZIP_SHA or q["canonical_source_sha256"]!=SOURCE_SHA
        or q["original_episodes"]!=180 or q["original_source_actions"]!=34360
        or q["original_negative"]!="MG50_EMPIRICAL_PUBLIC_TRANSITION_UNCERTAINTY_DEV_NOT_SUPPORTED_NO_SCIENCE"
        or tuple(p["families"])!=FAMILIES
        or tuple(map(tuple,p["seeds"]))!=SEEDS
        or len(p["roles"])!=20 or p["metrics"]["original_processes"]!=2
        or p["metrics"]["new_world_actions"]!=0
        or not all(p["prohibitions"].values())):
        raise ValueError("MG51_FROZEN_METRIC_SOURCE_CUSTODY_CHANGED")
    for sha in (PARENT,FREEZE):
        if git("merge-base","--is-ancestor",sha,"HEAD").returncode:
            raise ValueError("MG51_FROZEN_PROTOCOL_NOT_COMMITTED_BEFORE_AUDIT")
    files=git("diff","--name-only",PARENT,"HEAD")
    expected={".github/workflows/itd02-mg51-mg50-goal-relevance-audit.yml",
        "research/lcrm01/mg51_mg50_goal_relevance_audit_prereg.json",
        "research/lcrm01/mg51_mg50_goal_relevance_audit.py"}
    if files.returncode or set(files.stdout.splitlines())!=expected:
        raise ValueError("MG51_OUTSIDE_READ_ONLY_ORIGINAL_RESEARCH_SCOPE")
    return p
def visible(public,mission):
    m=MISSION.fullmatch(mission)
    if m is None:return False
    col,obj=m.groups()
    t,c=TYPES[obj],COLORS[col]
    return any(cell[0]==t and cell[1]==c
               for row in public["image"] for cell in row)
def at_front(public,mission):
    m=MISSION.fullmatch(mission)
    if m is None:return False
    col,obj=m.groups()
    cell=public["image"][3][5]
    return cell[0]==TYPES[obj] and cell[1]==COLORS[col]
def preflight():
    p=frozen()
    example={"direction":0,"mission":"pick up the red box",
             "image":[[[1,0,0] for _ in range(7)] for _ in range(7)]}
    before=json.loads(json.dumps(example))
    before["image"][3][5]=[7,0,0]
    if not visible(before,before["mission"]) or not at_front(before,before["mission"]):
        raise ValueError("MG51_ORIGINAL_PUBLIC_TARGET_MATCHER_DIAGNOSTIC_FAIL")
    if visible(example,example["mission"]) or at_front(example,example["mission"]):
        raise ValueError("MG51_ORIGINAL_PUBLIC_TARGET_MATCHER_FALSE_POSITIVE")
    if digest(before)==digest(example):
        raise ValueError("MG51_AUTHENTIC_PUBLIC_HASH_DIAGNOSTIC_FAIL")
    print("MG51_FROZEN_READONLY_WINDOWS_UBUNTU_PUBLIC_GOAL_METRIC_PREFLIGHT_PASS")
    return p
def episode(row):
    events=row["source_events"]
    if (not 1<=len(events)<=192
        or len(events)!=row["original_source_actions"]
        or digest(events)!=row["source_events_sha256"]
        or digest(events[0]["before"])!=row["public_start_sha256"]):
        raise ValueError("MG51_ORIGINAL_EPISODE_SOURCE_HASH_INVALID")
    mission=row["original_public_mission"]
    stats=collections.Counter()
    hist=[0]*7
    prior={events[0]["before_sha256"]}
    changes=[];target_exposed_steps=[];goal_steps=[]
    first_target=None
    for step,e in enumerate(events,1):
        before,after=e["before"],e["after"]
        if (type(e["action"]) is not int or not 0<=e["action"]<=6
            or e["index"]!=step or e["external_actions"]!=0
            or e["mission"]!=mission
            or before["mission"]!=after["mission"] or before["mission"]!=mission
            or digest(before)!=e["before_sha256"]
            or digest(after)!=e["after_sha256"]
            or (step>1 and e["before_sha256"]!=events[step-2]["after_sha256"])):
            raise ValueError("MG51_ORIGINAL_OWN_SELECTED_PUBLIC_EVENT_CHAIN_FAIL")
        a=e["action"];hist[a]+=1
        changed=e["before_sha256"]!=e["after_sha256"]
        novel=e["after_sha256"] not in prior
        prior.add(e["after_sha256"])
        bvis=visible(before,mission);avis=visible(after,mission)
        front=at_front(before,mission)
        stats["actions"]+=1
        stats["before_target_visible"]+=int(bvis)
        stats["before_target_front"]+=int(front)
        stats["after_target_visible"]+=int(avis)
        stats["target_newly_exposed_after_action"]+=int(not bvis and avis)
        stats["view_changed"]+=int(changed)
        stats["view_unchanged"]+=int(not changed)
        stats["view_changed_and_novel_episode"]+=int(changed and novel)
        stats[f"action_{a}_total"]+=1
        stats[f"action_{a}_changed"]+=int(changed)
        stats[f"action_{a}_novel"]+=int(changed and novel)
        stats[f"action_{a}_target_newly_visible"]+=int(not bvis and avis)
        stats[f"action_{a}_target_visible_before"]+=int(bvis)
        pick=front and a==3
        effect=pick and after["direction"]==before["direction"] and after["image"][3][5][0]==1
        stats["original_selected_exact_target_pickup_attempts"]+=int(pick)
        stats["original_selected_exact_target_pickup_effects"]+=int(effect)
        door=before["image"][3][5]
        aft=after["image"][3][5]
        opened=(a==5 and door[0]==4 and door[2]==2
                and aft[0]==4 and aft[1]==door[1] and aft[2]==0
                and before["direction"]==after["direction"])
        stats["original_locked_door_openings"]+=int(opened)
        positive=e["reward"]>0 and e["terminated"] is True
        stats["positive_terminal_original_steps"]+=int(positive)
        if positive:goal_steps.append(step)
        if changed:changes.append(step)
        if bvis:
            target_exposed_steps.append(step)
            if first_target is None:first_target=step
        if avis and first_target is None:first_target=step+1
    if (stats["actions"]!=row["original_source_actions"]
        or stats["view_changed"]!=row["observed_public_changes"]
        or stats["positive_terminal_original_steps"]!=row["original_terminal_goal_rewards"]
        or len({e["before_sha256"] for e in events})!=row["unique_public_views"]):
        raise ValueError("MG51_ORIGINAL_EPISODE_ACTION_GOAL_SOURCE_AGGREGATE_DRIFT")
    for window in (8,32):
        stats[f"change_then_first_target_within_{window}_steps"] = sum(
            first_target is not None and 0<=first_target-x<=window for x in changes)
        stats[f"change_then_positive_goal_within_{window}_steps"] = sum(
            any(0<=goal-x<=window for goal in goal_steps) for x in changes)
    return {"family":row["family"],"role":row["role"],
            "seed":row["seed_dev_exposed"],"actions":len(events),
            "first_observable_exact_target_step":first_target,
            "first_positive_original_goal_step":goal_steps[0] if goal_steps else None,
            "source_prediction_overrides":row.get("source_prediction_overrides",0),
            "source_predictive_opportunities":row.get("source_predictive_opportunities",0),
            "metrics":dict(stats),"action_histogram":hist}
def audit(source,p):
    q=p["parent"]
    if (source["classification"]!=q["original_negative"]
        or source["original_selected_action_count"]!=34360
        or source["exposed_transfer_DEV_seeds"]!=p["seeds"]
        or source["source_original_Farama"]!="7f5853792ea7f04f75614661006d87fcf949f26d"
        or source["scientific_first_use"] is not False
        or source["independent_sealed_scientific_witness"] is not False
        or source["zero_external_actions"] is not True
        or source["native_models_or_controllers_modified"] is not False
        or source["native_full_compute_energy_parity_qualified"] is not False):
        raise ValueError("MG51_ORIGINAL_MG50_IMMUTABLE_SCIENCE_STATUS_CHANGED")
    rows=source["original_180_episodes"]
    expected={(f,role,seed) for f,ss in zip(FAMILIES,SEEDS)
              for role in p["roles"] for seed in ss}
    if len(rows)!=180 or len(expected)!=180:raise ValueError("MG51_ORIGINAL_SOURCE_EPISODE_COUNT")
    observed=set();aggregate=collections.defaultdict(collections.Counter)
    actions=collections.defaultdict(lambda:[0]*7)
    output=[]
    for row in rows:
        identity=(row["family"],row["role"],row["seed_dev_exposed"])
        if identity not in expected or identity in observed:
            raise ValueError("MG51_ORIGINAL_SOURCE_IDENTITY_DUPLICATED_OR_UNKNOWN")
        observed.add(identity)
        data=episode(row);output.append(data)
        key=identity[:2]
        aggregate[key].update(data["metrics"])
        actions[key]=[x+y for x,y in zip(actions[key],data["action_histogram"])]
    if observed!=expected or sum(v["actions"] for v in aggregate.values())!=34360:
        raise ValueError("MG51_ORIGINAL_SELECTED_ACTION_TOTAL_MISMATCH")
    by_family={}
    for family in FAMILIES:
        by_family[family]={}
        for role in p["roles"]:
            key=(family,role)
            actual=aggregate[key];prior=source["per_family_per_role"][family][role]
            comparisons={
                "actions":"actions",
                "before_target_visible":"target_visible_frames",
                "before_target_front":"target_front_frames",
                "original_selected_exact_target_pickup_attempts":"selected_target_pickup_attempts",
                "original_selected_exact_target_pickup_effects":"actual_selected_target_pickup_effects",
                "original_locked_door_openings":"real_door_openings",
                "positive_terminal_original_steps":"positive_goal_episodes"}
            for new,old in comparisons.items():
                if actual[new]!=prior[old]:
                    raise ValueError("MG51_ORIGINAL_ROLE_SOURCE_METRIC_DRIFT:"+family+"/"+role+"/"+new)
            if actions[key]!=prior["action_histogram"]:
                raise ValueError("MG51_ORIGINAL_OWN_SELECTED_ACTION_HISTOGRAM_DRIFT")
            by_family[family][role]=dict(actual)
    return {"episodes":180,"actions":34360,
        "per_family_per_role":by_family,
        "per_episode":sorted(output,key=lambda v:(v["family"],v["role"],v["seed"])),
        "description":"Own-selected public-change and future target/goal associations; no reward causation, hidden state or localization inference."}
def run(archive,out):
    p=preflight()
    with archive.open("rb") as fp:
        if hashlib.file_digest(fp,"sha256").hexdigest()!=ZIP_SHA:
            raise ValueError("MG51_ORIGINAL_ARTIFACT_ZIP_SHA_MISMATCH")
    first=None;checks=[]
    with zipfile.ZipFile(archive) as z:
        expected={"comparison.log","first.json","second.json","first.log",
                  "second.log","first-resources.json","second-resources.json",
                  "mg33c-synthetic.json"}
        if set(z.namelist())!=expected:
            raise ValueError("MG51_ORIGINAL_ARTIFACT_LAYOUT_DRIFT")
        if SOURCE_SHA not in z.read("comparison.log").decode("utf8"):
            raise ValueError("MG51_INDEPENDENT_ORIGINAL_PROCESS_LOG_MISSING")
        for name in ("first.json","second.json"):
            with z.open(name) as fp:record=json.load(fp)
            if (record.get("canonical_source_sha256")!=SOURCE_SHA
                or digest(record["source"])!=SOURCE_SHA):
                raise ValueError("MG51_AUTHENTIC_FULL_SOURCE_CANONICAL_HASH_FAIL:"+name)
            evaluation=audit(record["source"],p)
            checks.append(digest(evaluation))
            if first is None:first=evaluation
            del record,evaluation;gc.collect()
        if len(set(checks))!=1:
            raise ValueError("MG51_INDEPENDENT_SOURCE_OBJECTIVE_ATTRIBUTION_DIVERGED")
        for name in ("first-resources.json","second-resources.json"):
            with z.open(name) as fp:res=json.load(fp)
            if (len(res["records"])!=180
                or res["original_source_sha256"]!=SOURCE_SHA):
                raise ValueError("MG51_ORIGINAL_RESOURCE_LINKAGE_DRIFT")
    output={"schema":"itd02.mg51.readonly-original-goal-relevance-audit.v1",
      "classification":p["classification"]["pass"],
      "original_source_sha256":SOURCE_SHA,"original_artifact_zip_sha256":ZIP_SHA,
      "original_MG50_negative":p["parent"]["original_negative"],
      "source_processes_independently_verified":2,
      "original_world_actions_in_MG51":0,
      "scientific_first_use":False,"goal_relevance_audit":first}
    output["audit_sha256"]=digest(output)
    out.write_text(json.dumps(output,sort_keys=True,indent=2)+"\n",encoding="utf8")
    print("MG51_TWO_COMPLETE_ORIGINAL_MG50_SOURCE_PROCESSES_VERIFIED",SOURCE_SHA)
    for family in FAMILIES:
        roles=p["roles"]
        compact={role:{k:first["per_family_per_role"][family][role].get(k,0)
                       for k in ("actions","view_changed","view_changed_and_novel_episode",
                                 "target_newly_exposed_after_action",
                                 "before_target_visible",
                                 "original_locked_door_openings",
                                 "positive_terminal_original_steps",
                                 "change_then_first_target_within_8_steps",
                                 "change_then_positive_goal_within_8_steps")}
                 for role in (roles[17],roles[18],roles[15],roles[13],roles[3])}
        print("MG51_GOAL_RELEVANCE_ROLE_COMPARISON",json.dumps(
            {"family":family,"roles":compact},sort_keys=True))
    print("MG51_CANONICAL_AUDIT_SHA256",output["audit_sha256"])
    print("MG51_FROZEN_DIAGNOSTIC_CLASSIFICATION",output["classification"])
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--preflight",action="store_true")
    p.add_argument("--archive",type=Path)
    p.add_argument("--output",type=Path)
    a=p.parse_args()
    if a.preflight:preflight();return
    if not a.archive or not a.output:p.error("--archive and --output required")
    run(a.archive,a.output)
if __name__=="__main__":main()
