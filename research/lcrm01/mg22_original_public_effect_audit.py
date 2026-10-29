#!/usr/bin/env python3
"""MG22 retrospective original Farama selected-action causal exposure audit.

Read-only authenticated MG21 original-world DEV evidence. Neither a causal
intervention nor an original source first-use study; no world reset/step here.
"""
from __future__ import annotations
import argparse,collections,hashlib,json,re
from pathlib import Path

HERE=Path(__file__).resolve().parent
PROTOCOL=HERE/"mg22_original_public_effect_prereg.json"
SCHEMA="itd02.mg22.retrospective-original-public-selected-effect-audit.v1"
EXACT_SHA="d6068acb9c246da4347afc065028983026e6b2bbaa03300e803c1f70995e8df2"
ROLES=("wingless_MG19_native","yggdrasil_MG19_local_cells",
       "independent_public_transition_count_conventional","uniform_original_random")
FAMILIES=("MiniGrid-DoorKey-6x6-v0","MiniGrid-UnlockPickup-v0",
          "MiniGrid-BlockedUnlockPickup-v0","MiniGrid-KeyCorridorS3R1-v0")
SEEDS=((946101,946103),(946201,946203),(946301,946303),(946401,946403))
MISSION=re.compile(r"^pick up the (red|green|blue|purple|yellow|grey) (key|ball|box)$")

def raw(x):
    return json.dumps(x,separators=(",",":"),sort_keys=True,ensure_ascii=True,allow_nan=False).encode("ascii")
def digest(x):
    return hashlib.sha256(raw(x)).hexdigest()
def check_public(p, mission):
    if type(p)is not dict or set(p)!={"image","direction","mission"} or p["mission"]!=mission:
        raise ValueError("MG22_SOURCE_MISSION_REPLACED_OR_FIELDS")
    if type(p["direction"])is not int or p["direction"] not in range(4):
        raise ValueError("MG22_SOURCE_DIRECTION_MISSING")
    img=p["image"]
    if (type(img)is not list or len(img)!=7 or any(type(row)is not list or len(row)!=7 or
         any(type(cell)is not list or len(cell)!=3 or any(type(x)is not int or not 0<=x<=255
         for x in cell) for cell in row) for row in img)):
        raise ValueError("MG22_SOURCE_PUBLIC_PIXELS_BAD")

def freeze():
    p=json.loads(PROTOCOL.read_text(encoding="utf-8"))
    if (p["schema"]!=SCHEMA or
        p["phase"]!="RETROSPECTIVE_SOURCE_AUDIT_AFTER_MG21_EXPOSURE__NOT_PREREG_OF_ORIGINAL_ACTIONS" or
        p["original_immutable"]["original_source_sha256"]!=EXACT_SHA or
        p["original_immutable"]["original_source_actions"]!=3997 or
        p["original_immutable"]["original_episodes"]!=32 or
        p["original_immutable"]["artifact_id"]!=12891691420 or
        p["cohorts"]["roles"]!=list(ROLES) or
        p["cohorts"]["families"]!=list(FAMILIES) or
        p["cohorts"]["exposed_dev_seeds"]!=[x for pair in SEEDS for x in pair] or
        not all(p["frozen_methods"].values()) or
        not all(p["prohibited"].values())):
        raise ValueError("MG22_FROZEN_RETROSPECTIVE_AUDIT_METHOD_CHANGED")
    colors=p["original_farama_encoding"]["colors"]
    objs=p["original_farama_encoding"]["objects"]
    states=p["original_farama_encoding"]["door_states"]
    if (colors!={"red":0,"green":1,"blue":2,"purple":3,"yellow":4,"grey":5} or
        objs!={"empty":1,"door":4,"key":5,"ball":6,"box":7,"goal":8} or
        states!={"open":0,"closed":1,"locked":2}):
        raise ValueError("MG22_UPSTREAM_ORIGINAL_OBJECT_ENCODING_DRIFT")
    return p

def load(path):
    envelope=json.loads(path.read_text(encoding="utf-8"))
    s=envelope.get("source")
    if (not isinstance(s,dict) or envelope.get("source_sha256")!=EXACT_SHA or
        digest(s)!=EXACT_SHA or
        envelope.get("schema")!="itd02.mg21.original-genuine-mission-source-online-development.v1" or
        envelope.get("classification")!="MG21_ORIGINAL_SOURCE_DEVELOPMENT_RECORDED_NOT_SCIENTIFIC_FIRST_USE" or
        s.get("source_commit")!="7f5853792ea7f04f75614661006d87fcf949f26d" or
        s.get("scientific_first_use") is not False or
        s.get("external_live_actions")!=0 or
        s.get("new_original_source_env_actions")!=3997 or
        s.get("native_models_promoted") is not False or
        s.get("accepted_models_and_forge_controller_unchanged") is not True):
        raise ValueError("MG22_UNTRUSTED_ORIGINAL_SELECTED_SOURCE_ENVELOPE")
    return s

def analyze(s,proto):
    rows=s["original_source_32_independent_role_episodes"]
    if type(rows)is not list or len(rows)!=32:
        raise ValueError("MG22_MISSING_32_ORIGINAL_ROLE_EPISODES")
    role_counts=collections.Counter()
    start_hash={}
    episodes=[]
    actions_total=0
    per_role_family=collections.defaultdict(lambda:collections.Counter())
    trace_by_family_seed={}
    encoding=proto["original_farama_encoding"]
    colors=encoding["colors"]
    objects=encoding["objects"]
    for row in rows:
        fam,seed,role=row["family"],row["seed_dev_exposed"],row["role"]
        if fam not in FAMILIES or seed not in SEEDS[FAMILIES.index(fam)] or role not in ROLES:
            raise ValueError("MG22_ORIGINAL_DEV_ROLE_OR_SEED_MISMATCH")
        key=(fam,seed)
        role_counts[(fam,seed,role)]+=1
        if role_counts[(fam,seed,role)]!=1:raise ValueError("MG22_DUPLICATE_ORIGINAL_ROLE")
        origin=row["public_start_sha256"]
        if key in start_hash and start_hash[key]!=origin:raise ValueError("MG22_UNEQUAL_AUTHENTIC_ORIGINAL_START")
        start_hash[key]=origin
        es=row["source_events"]
        if type(es)is not list or not 1<=len(es)<=128 or row["original_source_actions"]!=len(es):
            raise ValueError("MG22_SOURCE_EPISODE_ACTION_CAP")
        if digest(es)!=row["source_events_sha256"]:raise ValueError("MG22_SOURCE_EPISODE_HASH")
        mission=row["original_public_mission"]
        target=MISSION.fullmatch(mission)
        if fam==FAMILIES[0] and mission!="use the key to open the door and then get to the goal":
            raise ValueError("MG22_ORIGINAL_DOORKEY_MISSION_CHANGED")
        if fam!=FAMILIES[0] and target is None:
            raise ValueError("MG22_ORIGINAL_PICKUP_MISSION_CHANGED")
        picked=[];doors=[];goal=[]
        seen=set()
        no_change=observed_changes=target_effects=0
        pickup=drop=locked_open=closed_open=door_close=repeat_pick_drop=0
        counts=collections.Counter()
        previous=None
        for i,e in enumerate(es,1):
            if type(e)is not dict or set(e)!={"index","action","before","after","before_sha256",
                 "after_sha256","external_actions","mission","policy_status","reward",
                 "terminated","truncated"}:
                raise ValueError("MG22_ORIGINAL_ACTION_SOURCE_FIELDS_INCOMPLETE")
            b,a=e["before"],e["after"]
            check_public(b,mission);check_public(a,mission)
            if (e["index"]!=i or type(e["action"])is not int or e["action"] not in range(7) or
                type(e["reward"])is not float or
                type(e["terminated"])is not bool or type(e["truncated"])is not bool or
                e["external_actions"]!=0 or e["mission"]!=mission or
                not isinstance(e["policy_status"],str) or not e["policy_status"] or
                e["before_sha256"]!=digest(b) or e["after_sha256"]!=digest(a) or
                (i==1 and e["before_sha256"]!=origin) or
                (previous is not None and previous!=b) or
                (i<len(es) and (e["terminated"] or e["truncated"]))):
                raise ValueError("MG22_NOT_ORIGINAL_SELECTED_SOURCE_PUBLIC_CONTINUITY")
            previous=a
            action=e["action"];counts[action]+=1
            same=e["before_sha256"]==e["after_sha256"]
            no_change+=int(same); observed_changes+=int(not same)
            # Verified original MiniGrid egocentric public front cell is (x=3,y=5).
            # No agent coordinates or hidden possession/inventory are inspected.
            fb=b["image"][3][5];fa=a["image"][3][5]
            stable_heading=b["direction"]==a["direction"]
            if stable_heading and action==3 and fb[0] in (5,6,7) and fa[0]==1:
                pickup+=1;picked.append(i)
                if target and fb[0]==objects[target.group(2)] and fb[1]==colors[target.group(1)]:
                    target_effects+=1
            if stable_heading and action==4 and fb[0]==1 and fa[0] in (5,6,7):
                drop+=1
            if stable_heading and action==5 and fb[0]==fa[0]==4 and fb[1]==fa[1]:
                if (fb[2],fa[2])==(2,0):locked_open+=1;doors.append(i)
                if (fb[2],fa[2])==(1,0):closed_open+=1;doors.append(i)
                if (fb[2],fa[2])==(0,1):door_close+=1
            if action in (3,4) and picked:repeat_pick_drop+=int(i>picked[0])
            if e["reward"]>0:
                if not e["terminated"]:raise ValueError("MG22_FALSE_GOAL_REWARD_NOT_TERMINAL")
                goal.append(i)
        actual_goals=len(goal)
        if row["original_terminal_goal_rewards"]!=actual_goals:
            raise ValueError("MG22_ORIGINAL_TERMINAL_REWARD_DISAGREEMENT")
        if row["distinct_actions"]!=len(counts) or row["observed_public_changes"]!=observed_changes:
            raise ValueError("MG22_SOURCE_ROLE_ACTION_COUNTER_DISAGREEMENT")
        if role in ROLES[:3]:
            if row["selected_source_samples_after"]-row["prior_selected_source_samples"]!=len(es):
                raise ValueError("MG22_NATIVE_SELECTED_FEEDBACK_NOT_PERSISTED")
        if role in ROLES[:2]:
            if not re.fullmatch("[0-9a-f]{64}",row["checkpoint_sha256"]):
                raise ValueError("MG22_NATIVE_COLD_RECEIPT_MISSING")
        ordered=any(p<d<g for p in picked for d in doors for g in goal)
        stats={"family":fam,"seed_exposed":seed,"role":role,"original_actions":len(es),
          "original_terminal_goal_rewards":actual_goals,"original_public_no_change":no_change,
          "original_public_changes":observed_changes,"selected_pickup_visual_effect":pickup,
          "selected_drop_visual_effect":drop,"selected_mission_target_pickup_visual_effect":target_effects,
          "selected_locked_door_open_visible_effect":locked_open,
          "selected_closed_door_open_visible_effect":closed_open,
          "selected_door_close_visible_effect":door_close,
          "selected_pickup_or_drop_after_first_pickup":repeat_pick_drop,
          "ordered_public_pickup_door_reward_temporal_chain":int(ordered),
          "total_forward":counts[2],"total_done":counts[6],
          "original_action_diversity":len(counts)}
        episodes.append(stats)
        trace_by_family_seed[(fam,seed,role)]=[(x["action"],x["before_sha256"],x["after_sha256"],x["reward"]) for x in es]
        per_role_family[(fam,role)].update({k:v for k,v in stats.items() if type(v)is int and k not in ("seed_exposed",)})
        actions_total+=len(es)
    if actions_total!=3997 or len(role_counts)!=32 or len(start_hash)!=8:
        raise ValueError("MG22_ORIGINAL_ACTIONS_AND_SEED_MATRIX_INCOMPLETE")
    agreements=[]
    for fam in FAMILIES:
        for seed in SEEDS[FAMILIES.index(fam)]:
            for role in ROLES[0:2]:
                conventional=trace_by_family_seed[(fam,seed,ROLES[2])]
                native=trace_by_family_seed[(fam,seed,role)]
                agreements.append({"family":fam,"seed_exposed":seed,"native":role,
                   "identical_original_action_effect_trace_as_conventional":native==conventional,
                   "identical_selected_action_ids_as_conventional":[v[0] for v in native]==[v[0] for v in conventional]})
    rollup={}
    for fam in FAMILIES:
        rollup[fam]={role:dict(sorted(per_role_family[(fam,role)].items())) for role in ROLES}
    return {"episodes":episodes,"by_family_and_role":rollup,
            "native_conventional_trajectory_agreement":agreements,
            "original_source_actions_verified":actions_total,
            "actual_original_terminal_goal_rewards":sum(x["original_terminal_goal_rewards"] for x in episodes),
            "verified_original_episode_count":len(episodes),
            "no_original_world_actions_generated":True}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--first",required=True,type=Path)
    parser.add_argument("--second",required=True,type=Path)
    parser.add_argument("--output",required=True,type=Path)
    args=parser.parse_args()
    p=freeze(); a=load(args.first);b=load(args.second)
    if a!=b:raise ValueError("MG22_TWO_ORIGINAL_SELECTED_SOURCE_PROCESSES_DIFFER")
    report=analyze(a,p)
    receipt={"schema":"itd02.mg22.retrospective-public-consequence-audit-receipt.v1",
        "classification":"MG22_SOURCE_AUTHENTIC_PUBLIC_EFFECT_CAUSAL_EXPOSURE_DIAGNOSTIC__NOT_SCIENCE",
        "source_sha256":EXACT_SHA,"original_source_archive_id":12891691420,
        "frozen_audit_method_sha256":hashlib.sha256(PROTOCOL.read_bytes()).hexdigest(),
        "source_action_effect_diagnostics":report,
        "scientific_first_use":False,"new_original_environment_steps":0,
        "accepted_models_or_forge_controller_modified":False}
    receipt["canonical_receipt_sha256"]=digest({k:v for k,v in receipt.items() if k!="canonical_receipt_sha256"})
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print("MG22_TWO_SOURCE_PROCESS_ORIGINAL_PUBLIC_EFFECT_AUDIT_PASS",receipt["canonical_receipt_sha256"])
    print("MG22_REAL_SOURCE_ACTIONS",report["original_source_actions_verified"])
    print("MG22_PER_FAMILY_PER_ROLE",json.dumps(report["by_family_and_role"],sort_keys=True))
if __name__=="__main__":
    main()
