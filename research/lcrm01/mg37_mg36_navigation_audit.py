#!/usr/bin/env python3
"""MG37: source-pinned original-public MG36 navigation/action consequence audit, no MiniGrid."""
from __future__ import annotations
import argparse, collections, hashlib, json, re, zipfile
from pathlib import Path

HERE=Path(__file__).resolve().parent
FREEZE=HERE/"mg37_mg36_navigation_audit_prereg.json"
MISSION=re.compile(r"^pick up the (red|green|blue|purple|yellow|grey) (key|ball|box)$")
COLORS={"red":0,"green":1,"blue":2,"purple":3,"yellow":4,"grey":5}
TYPES={"key":5,"ball":6,"box":7}
METRICS=("actions","target_any_visible_frames","target_visible_not_front_frames",
 "target_front_frames","target_front_selected_pickup_attempts","target_front_selected_effects",
 "target_front_no_pickup_frames","locked_door_front_frames","locked_door_toggle_attempts",
 "locked_door_openings","positive_terminal_goal_steps","public_no_change_frames",
 "selected_turn_left","selected_turn_right","selected_forward","selected_pickup",
 "selected_drop","selected_toggle","selected_done","forward_no_public_change",
 "toggle_no_public_change")

def encode(v):
    return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=True,allow_nan=False).encode("utf8")
def digest(v):
    return hashlib.sha256(encode(v)).hexdigest()

def frozen():
    p=json.loads(FREEZE.read_text(encoding="utf8"))
    assert p["schema"]=="itd02.mg37.exposed-mg36-original-public-navigation-attribution-audit.v1"
    assert p["phase"]=="METRICS_AND_CUSTODY_FROZEN_BEFORE_EXECUTABLE"
    assert p["scope"]=="RETROSPECTIVE_AUTHENTIC_MG36_EXPOSED_DEV_ONLY_NO_NEW_WORLD_ACTIONS"
    assert p["parent"]["mg36_head"]=="204fa4115637c1f3b8aa037a058cba6db0fc44db"
    assert p["parent"]["run_id"]==40947966691 and p["parent"]["artifact_id"]==12928909424
    assert p["parent"]["original_episodes"]==108 and p["parent"]["original_selected_actions"]==20266
    assert all(p["engineering"].values()) and all(p["prohibitions"].values())
    return p

def event_metric(e):
    b,a=e["before"],e["after"]
    assert e["external_actions"]==0 and type(e["action"]) is int and 0<=e["action"]<=6
    assert digest(b)==e["before_sha256"] and digest(a)==e["after_sha256"]
    assert b["mission"]==a["mission"]==e["mission"]
    assert len(b["image"])==len(a["image"])==7
    assert all(len(row)==7 and all(len(px)==3 for px in row) for row in b["image"])
    assert all(len(row)==7 and all(len(px)==3 for px in row) for row in a["image"])
    m=MISSION.fullmatch(e["mission"])
    t=TYPES[m.group(2)] if m else None
    c=COLORS[m.group(1)] if m else None
    visible=bool(m and any(px[0]==t and px[1]==c for row in b["image"] for px in row))
    f=b["image"][3][5];n=a["image"][3][5];front=bool(m and f[0]==t and f[1]==c)
    pick=front and e["action"]==3
    effect=pick and n[0]==1 and b["direction"]==a["direction"]
    door=f[0]==4 and f[2]==2
    toggle=door and e["action"]==5
    opening=toggle and b["direction"]==a["direction"] and n[0]==4 and n[1]==f[1] and n[2]==0
    return {"actions":1,"target_any_visible_frames":int(visible),
      "target_visible_not_front_frames":int(visible and not front),
      "target_front_frames":int(front),
      "target_front_selected_pickup_attempts":int(pick),
      "target_front_selected_effects":int(effect),
      "target_front_no_pickup_frames":int(front and not pick),
      "locked_door_front_frames":int(door),
      "locked_door_toggle_attempts":int(toggle),
      "locked_door_openings":int(opening),
      "positive_terminal_goal_steps":int(e["reward"]>0 and e["terminated"] is True),
      "public_no_change_frames":int(e["before_sha256"]==e["after_sha256"]),
      "selected_turn_left":int(e["action"]==0),
      "selected_turn_right":int(e["action"]==1),
      "selected_forward":int(e["action"]==2),
      "selected_pickup":int(e["action"]==3),
      "selected_drop":int(e["action"]==4),
      "selected_toggle":int(e["action"]==5),
      "selected_done":int(e["action"]==6),
      "forward_no_public_change":int(e["action"]==2 and e["before_sha256"]==e["after_sha256"]),
      "toggle_no_public_change":int(e["action"]==5 and e["before_sha256"]==e["after_sha256"])}

def audit(source,p):
    x=p["parent"]
    assert source["classification"]==x["frozen_original_negative"]
    assert source["original_selected_action_count"]==x["original_selected_actions"]
    assert source["scientific_first_use"] is False and source["mg28_native_rollout_permitted"] is False
    assert source["native_models_or_controllers_modified"] is False
    assert source["zero_external_actions"] is True
    assert source["native_resource_parity_qualified"] is False
    episodes=source["original_108_episodes"]
    assert len(episodes)==x["original_episodes"]
    assert source["exposed_dev_seeds"]==p["seeds"]
    expected={(family,role,seed) for family,seeds in zip(p["families"],source["exposed_dev_seeds"])
      for role in p["roles"] for seed in seeds}
    assert len(expected)==108
    found=set()
    summed=collections.defaultdict(collections.Counter)
    goals=collections.Counter();any_seen=collections.Counter();front_seen=collections.Counter()
    any_contexts=collections.defaultdict(set);front_contexts=collections.defaultdict(set)
    acts=collections.defaultdict(lambda:[0]*7);front_acts=collections.defaultdict(lambda:[0]*7)
    attempts=[];per_episode=[]
    for ep in episodes:
        identity=(ep["family"],ep["role"],ep["seed_dev_exposed"])
        assert identity in expected and identity not in found
        found.add(identity)
        events=ep["source_events"]
        assert len(events)==ep["original_source_actions"] and len(events)<=192
        assert digest(events)==ep["source_events_sha256"]
        count=collections.Counter()
        for index,e in enumerate(events,1):
            assert e["index"]==index and e["mission"]==ep["original_public_mission"]
            v=event_metric(e);count.update(v)
            group=identity[:2]
            acts[group][e["action"]]+=1
            if v["target_any_visible_frames"]:any_contexts[group].add(e["before_sha256"])
            if v["target_front_frames"]:
                front_contexts[group].add(e["before_sha256"])
                front_acts[group][e["action"]]+=1
            if v["target_front_selected_pickup_attempts"]:
                attempts.append({"family":identity[0],"role":identity[1],"seed":identity[2],
                   "step":index,"observed_effect":bool(v["target_front_selected_effects"]),
                   "positive_terminal":bool(v["positive_terminal_goal_steps"]),
                   "after_front":e["after"]["image"][3][5],
                   "before_public_sha256":e["before_sha256"]})
        assert count["actions"]==ep["original_source_actions"]
        assert count["positive_terminal_goal_steps"]==ep["original_terminal_goal_rewards"]
        assert count["public_no_change_frames"]+ep["observed_public_changes"]==count["actions"]
        assert len({e["before_sha256"] for e in events})==ep["unique_public_views"]
        group=identity[:2]
        summed[group].update(count)
        goals[group]+=int(count["positive_terminal_goal_steps"]>0)
        any_seen[group]+=int(count["target_any_visible_frames"]>0)
        front_seen[group]+=int(count["target_front_frames"]>0)
        per_episode.append({"family":identity[0],"role":identity[1],"seed":identity[2],
            **{k:count[k] for k in METRICS}})
    assert found==expected and sum(v["actions"] for v in summed.values())==x["original_selected_actions"]
    rows=[]
    for group in sorted(summed):
        v=summed[group]; prior=source["per_family_per_role"][group[0]][group[1]]
        for metric,older in (("target_front_frames","target_front"),
          ("target_front_selected_pickup_attempts","target_pick_attempt"),
          ("target_front_selected_effects","target_disappearance"),
          ("locked_door_openings","door_open"),
          ("positive_terminal_goal_steps","positive_goal"),("actions","actions")):
            assert v[metric]==prior[older],(group,metric)
        assert goals[group]==prior["positive_goal_episodes"]
        assert acts[group]==prior["action_histogram"]
        assert v["selected_turn_left"]==acts[group][0]
        assert v["selected_turn_right"]==acts[group][1]
        assert v["selected_forward"]==acts[group][2]
        assert v["selected_pickup"]==acts[group][3]
        assert v["selected_drop"]==acts[group][4]
        assert v["selected_toggle"]==acts[group][5]
        assert v["selected_done"]==acts[group][6]
        assert v["selected_turn_left"]+v["selected_turn_right"]+v["selected_forward"]+
            v["selected_pickup"]+v["selected_drop"]+v["selected_toggle"]+v["selected_done"]==v["actions"]
        assert sum(front_acts[group])==v["target_front_frames"]
        rows.append({"family":group[0],"role":group[1],**{k:v[k] for k in METRICS},
          "target_any_visible_episodes":any_seen[group],
          "target_front_episodes":front_seen[group],
          "unique_target_visible_public_contexts":len(any_contexts[group]),
          "unique_target_front_public_contexts":len(front_contexts[group]),
          "positive_goal_episodes":goals[group],
          "turn_selected_fraction":(v["selected_turn_left"]+v["selected_turn_right"])/v["actions"],
          "forward_public_change_count":v["selected_forward"]-v["forward_no_public_change"],
          "original_selected_action_histogram":acts[group],
          "selected_action_histogram_when_target_front":front_acts[group]})
    assert len(rows)==36
    return {"classification":p["classification_if_pass"],
       "original_source_classification_unchanged":source["classification"],
       "scientific_first_use":False,"original_world_actions_executed_by_audit":0,
       "native_models_or_controllers_modified":False,"mg28_rollout_permitted":False,
       "episodes":108,"selected_actions":x["original_selected_actions"],
       "per_family_per_role":rows,
       "selected_target_front_pickup_attempts":sorted(attempts,
           key=lambda z:(z["family"],z["role"],z["seed"],z["step"])),
       "per_episode":sorted(per_episode,key=lambda z:(z["family"],z["role"],z["seed"]))}

def run(artifact,out):
    p=frozen()
    zsha=hashlib.sha256(artifact.read_bytes()).hexdigest()
    assert zsha==p["parent"]["artifact_zip_sha256"],"MG37_SOURCE_ZIP_IDENTITY_FAIL"
    with zipfile.ZipFile(artifact) as z:
        assert set(z.namelist())=={"first.json","second.json","first.log","second.log",
            "comparison.log","mg33c-synthetic.json"}
        originals=[json.loads(z.read(x)) for x in ("first.json","second.json")]
        sources=[];reports=[]
        for rec in originals:
            assert rec["canonical_source_sha256"]==p["parent"]["original_canonical_source_sha256"]
            assert digest(rec["source"])==rec["canonical_source_sha256"]
            sources.append(rec["source"]);reports.append(audit(rec["source"],p))
        assert sources[0]==sources[1] and reports[0]==reports[1]
        assert p["parent"]["canonical_original_source_sha256"] in z.read("comparison.log").decode("utf8")
    report=reports[0]
    report["original_archive_sha256"]=zsha
    report["original_canonical_source_sha256"]=p["parent"]["canonical_original_source_sha256"]
    report["audit_sha256"]=digest(reports[0])
    out.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n",encoding="utf8")
    print(report["classification"])
    print("MG37_TWO_ORIGINAL_SOURCE_PROCESSES_EXACT_AUDIT_PASS",report["audit_sha256"])
    for row in report["per_family_per_role"]:
        print("MG37_ROLE",row["family"],row["role"],"visible",row["target_any_visible_frames"],
          "front",row["target_front_frames"],"pick",row["target_front_selected_pickup_attempts"],
          "effect",row["target_front_selected_effects"],"goals",row["positive_goal_episodes"],
          "turns",row["selected_turn_left"]+row["selected_turn_right"],
          "forward",row["selected_forward"],"forward_stall",row["forward_no_public_change"])

def preflight():
    p=frozen()
    e={"action":3,"reward":1.0,"terminated":True,"external_actions":0,
       "mission":"pick up the red box",
       "before":{"direction":1,"mission":"pick up the red box",
                 "image":[[[1,0,0] for _ in range(7)] for _ in range(7)]},
       "after":{"direction":1,"mission":"pick up the red box",
                "image":[[[1,0,0] for _ in range(7)] for _ in range(7)]}}
    e["before"]["image"][3][5]=[7,0,0]
    e["before_sha256"]=digest(e["before"]);e["after_sha256"]=digest(e["after"])
    x=event_metric(e)
    assert (x["target_any_visible_frames"],x["target_front_frames"],
      x["target_front_selected_pickup_attempts"],x["target_front_selected_effects"])==(1,1,1,1)
    e["action"]=5;x=event_metric(e)
    assert x["selected_toggle"]==1 and x["selected_turn_left"]==0 and x["forward_no_public_change"]==0
    assert x["target_front_no_pickup_frames"]==1 and x["target_front_selected_pickup_attempts"]==0
    e["action"]=2
    assert event_metric(e)["selected_forward"]==1
    e["mission"]=e["before"]["mission"]=e["after"]["mission"]="use the key to open the door"
    e["before_sha256"]=digest(e["before"]);e["after_sha256"]=digest(e["after"])
    assert event_metric(e)["target_any_visible_frames"]==0
    assert p["parent"]["mg36_head"]=="204fa4115637c1f3b8aa037a058cba6db0fc44db"
    print("MG37_FROZEN_SOURCE_ONLY_POSITIVE_AND_NEGATIVE_PREFLIGHT_PASS")

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--preflight",action="store_true")
    parser.add_argument("--artifact",type=Path);parser.add_argument("--output",type=Path)
    args=parser.parse_args()
    if args.preflight:preflight()
    else:
        if args.artifact is None or args.output is None:
            parser.error("--artifact and --output required")
        run(args.artifact,args.output)

if __name__=="__main__":
    main()
