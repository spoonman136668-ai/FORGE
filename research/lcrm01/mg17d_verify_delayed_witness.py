#!/usr/bin/env python3
"""MG17-D: retrospective independently reproducible original-source delayed witness.

Input: archived, immutable MG17-C *development* complete source processes.
No environment reset, action policy, model training or hidden inventory use.
The public door-transition-to-original-goal interval is observational, not
proof that either learner understood causality.
"""
from __future__ import annotations
import argparse, hashlib, json, math, zipfile
from pathlib import Path

HERE=Path(__file__).resolve().parent
FROZEN=HERE/"mg17d_delayed_chain_witness_freeze.json"
SCHEMA="itd02.mg17d.retrospective-original-public-delayed-chain-witness.v1"
RESULT="MG17D_VERIFIED_PUBLIC_DOOR_THEN_ORIGINAL_GOAL_DELAY__NO_CAUSAL_SCIENCE"
ROLES=("wingless_dk17","yggdrasil_r21","wingless_parent_dk16",
       "yggdrasil_parent_r20","conventional_local_effect",
       "conventional_mission_blind","uniform_random")
COHORTS={"MiniGrid-DoorKey-6x6-v0":(78301,78303,78307),
         "MiniGrid-Empty-Random-6x6-v0":(78501,78503,78507)}

def canonical(x):
    return json.dumps(x,sort_keys=True,separators=(",",":"),allow_nan=False,ensure_ascii=True).encode()

def digest(x):return hashlib.sha256(canonical(x)).hexdigest()
def require(test,reason):
    if not test:raise ValueError("MG17D_ORIGINAL_SOURCE_"+reason)

def freeze():
    p=json.loads(FROZEN.read_text())
    require(p["schema"]==SCHEMA and
            p["phase"]=="RETROSPECTIVE_FROZEN_EVIDENCE_INVENTORY_BEFORE_NEW_AUDIT_EXECUTABLE",
            "FREEZE_SCHEMA")
    src=p["evidence"]
    require(src["source_run"]==40854091686 and src["source_artifact_id"]==12888462851 and
            src["expected_trace_sha256"]==
              "42e0a50bf7d88e3929e4e6efae2a37d3fbdf814762132ce238aa8f4b6bd6161c" and
            src["original_world_episodes"]==42 and
            src["expected_legal_actual_selected_actions"]==5065 and
            src["complete_original_source_processes"]==2 and
            src["original_farama"]=="7f5853792ea7f04f75614661006d87fcf949f26d",
            "FROZEN_ORIGINAL_CUSTODY")
    require(p["expected_frozen_worlds"]=={"DoorKey6":[78301,78303,78307],
                                            "EmptyRandom6":[78501,78503,78507]},
            "FROZEN_COHORT")
    require(p["negative_control_roles"]==list(ROLES[i] for i in (0,1,4)),
            "FROZEN_NEGATIVE_CONTROLS")
    require(p["rules"]["no_rerun_original_seeds"] and
            p["rules"]["no_new_training"] and
            p["rules"]["forbid_training_or_scientific_acceptance"],
            "NO_NEW_SCIENCE")
    return p

def public(obj):
    require(type(obj)is dict and set(obj)=={"image","direction","mission"},
            "ORIGINAL_PUBLIC_KEYS")
    require(type(obj["direction"])is int and obj["direction"] in range(4) and
            type(obj["mission"])is str and bool(obj["mission"].strip()),
            "ORIGINAL_SOURCE_MISSION")
    m=obj["image"]
    require(type(m)is list and len(m)==7 and
            all(type(x)is list and len(x)==7 for x in m) and
            all(type(v)is list and len(v)==3 and
                all(type(t)is int and 0<=t<=255 for t in v)
                for row in m for v in row),
            "ORIGINAL_SOURCE_IMAGE")

def explicit_open_transition(before,after):
    # Source-public event ONLY: object 4, same color, door-state 2 -> 0.
    # No hidden inventory, pose, or proof of a learned door/key rule.
    return any(
        before["image"][i][j][0]==4 and before["image"][i][j][2]==2 and
        after["image"][i][j][0]==4 and after["image"][i][j][2]==0 and
        before["image"][i][j][1]==after["image"][i][j][1]
        for i in range(7) for j in range(7)
    )

def verify_process(report,freeze_doc):
    require(report["schema"]=="itd02.mg17c.original-farama-local-effect-seven-arm.v1" and
            report["classification"]==
              "MG17C_LOCAL_CONSEQUENCE_GENERALIZATION_NOT_BOTH_DEMONSTRATED__NO_SCIENCE" and
            report["scientific_first_use"] is False and
            report["original_episode_count"]==42 and
            report["external_live_actions"]==0 and
            report["accepted_native_model_promoted"] is False and
            report["FORGE_or_CKB_controller_modified"] is False,
            "SOURCE_CLASSIFICATION_AND_AUTHORITY")
    src=report["canonical_original_source_evidence"]
    require(digest(src)==report["canonical_original_source_sha256"]==
            freeze_doc["evidence"]["expected_trace_sha256"] and
            src["original_training_stream_sha256"]==
              "9c640b0ae6a0865b9db7147d4b816643962ee69141950e7639dcc09b832d0e24" and
            src["original_source_fit_samples_each"]==1664 and
            src["zero_external_live_actions"] is True,
            "SOURCE_HASH_AND_FIT")
    rows=src["authentic_original_source_records"]
    expected={(env,seed,role) for env,seeds in COHORTS.items()
                                  for seed in seeds for role in ROLES}
    require(len(rows)==42 and
            {(r["environment"],r["seed_evaluator_only"],r["role"])
              for r in rows}==expected,"EXACT_42_REGISTERED_EPISODES")
    witnesses=[]
    source_actions=0
    totals={}
    for env,seeds in COHORTS.items():
        for seed in seeds:
            group=[r for r in rows if r["environment"]==env and
                   r["seed_evaluator_only"]==seed]
            require(len({r["original_start_public_sha256"] for r in group})==1,
                    "SEVEN_ARM_ORIGINAL_RESET_PARITY")
    for row in rows:
        role=row["role"];env=row["environment"];seed=row["seed_evaluator_only"]
        events=row["real_source_events"]
        mission=("use the key to open the door and then get to the goal"
                 if env=="MiniGrid-DoorKey-6x6-v0"
                 else "get to the green goal square")
        require(0<len(events)<=192 and row["original_live_selected_steps"]==len(events)
                and row["external_actions"]==0 and
                row["actual_source_mission"]==mission,
                "EPISODE_AND_TRUE_SOURCE_MISSION")
        source_actions+=len(events)
        openings=[];positive_goals=[]
        for index,e in enumerate(events):
            b=e["public_before"];a=e["public_after"]
            public(b);public(a)
            require(e["step"]==index+1 and e["role"]==role and
                    b["mission"]==mission and a["mission"]==mission and
                    e["original_public_before_sha256"]==digest(b) and
                    e["original_public_after_sha256"]==digest(a) and
                    type(e["actual_original_source_action"])is int and
                    e["actual_original_source_action"] in range(7) and
                    e["external_live_actions"]==0 and
                    type(e["source_reward"])is float and
                    math.isfinite(e["source_reward"]) and
                    type(e["terminated"])is bool and type(e["truncated"])is bool,
                    "ACTION_SOURCE_PUBLIC_REWARD_OR_MISSION")
            if index:
                prev=events[index-1]
                require(prev["original_public_after_sha256"]==e["original_public_before_sha256"] and
                        not prev["terminated"] and not prev["truncated"],
                        "SELECTED_ACTION_CONTINUITY")
            opened=explicit_open_transition(b,a)
            require(e["source_visible_door_opened"]==opened,"PUBLIC_DOOR_WITNESS_NOT_AUTHENTIC")
            if opened:openings.append(e["step"])
            if e["source_reward"]>0:
                require(e["terminated"] is True and e["truncated"] is False and
                        index==len(events)-1,
                        "ORIGINAL_REWARD_NOT_TERMINAL")
                positive_goals.append(e["step"])
        require(len(openings)==row["source_visible_door_openings"] and
                len(positive_goals)==row["source_goal_rewards"],
                "SOURCE_AGGREGATE_MISMATCH")
        totals.setdefault(role,{"DoorKey":0,"Empty":0,"door_open":0})
        totals[role]["DoorKey" if env=="MiniGrid-DoorKey-6x6-v0" else "Empty"]+=len(positive_goals)
        totals[role]["door_open"]+=len(openings)
        if env=="MiniGrid-DoorKey-6x6-v0" and positive_goals:
            require(len(openings)==1 and len(positive_goals)==1 and
                    openings[0]<positive_goals[0],"PUBLIC_DOOR_NOT_PRECEDING_REWARD")
            witnesses.append({"role":role,"seed":seed,
                "source_public_door_open_step":openings[0],
                "source_goal_reward_step":positive_goals[0],
                "door_to_goal_delay":positive_goals[0]-openings[0]})
    require(source_actions==freeze_doc["evidence"]["expected_legal_actual_selected_actions"],
            "SELECTED_ACTION_TOTAL")
    require(sorted(witnesses,key=lambda x:(x["role"],x["seed"]))==
            sorted(freeze_doc["expected_source_goal_witnesses"],
                 key=lambda x:(x["role"],x["seed"])),"FROZEN_DELAYED_WITNESS")
    require(all(totals[role]["DoorKey"]==0 and totals[role]["door_open"]==0
                for role in freeze_doc["negative_control_roles"]),
            "NEW_NATIVE_FALSE_GOAL_PROGRESS")
    return {"original_episode_count":len(rows),"selected_actions":source_actions,
            "source_sha256":digest(src),"delayed_public_witnesses":witnesses,
            "per_role_original_goals_and_doors":totals}

def audit(archive):
    p=freeze()
    with zipfile.ZipFile(archive) as z:
        names=set(z.namelist())
        require({"first.json","second.json","comparison.json"}.issubset(names),
                "ARCHIVED_FULL_TWO_PROCESS_EVIDENCE")
        one=json.loads(z.read("first.json"));two=json.loads(z.read("second.json"))
        compare=json.loads(z.read("comparison.json"))
    original=verify_process(one,p);again=verify_process(two,p)
    require(one["canonical_original_source_evidence"]==
            two["canonical_original_source_evidence"] and original==again and
            compare["canonical_original_source_sha256"]==original["source_sha256"] and
            compare["complete_independent_source_processes"]==2 and
            compare["same_canonical_original_selected_source"] is True and
            compare["classification"]==one["classification"],
            "TWO_PROCESS_REPRODUCIBILITY")
    return {"schema":SCHEMA,"classification":RESULT,
            "retrospective_existing_development_source_only":True,
            "source_original_Farama_commit":p["evidence"]["original_farama"],
            "MG17C_qualifying_run":p["evidence"]["source_run"],
            "MG17C_artifact_id":p["evidence"]["source_artifact_id"],
            "fully_audited_independent_original_processes":2,
            "no_original_seed_reexecution":True,
            "no_true_inventory_custody_claim":True,
            "causal_generalization_or_native_advantage_proven":False,
            "scientific_first_use":False,
            "blocked_new_mission_family_before_native_admission":True,
            **original}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--archive",type=Path,required=True)
    ap.add_argument("--output",type=Path,required=True)
    opt=ap.parse_args()
    result=audit(opt.archive)
    opt.output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("MG17D_DELAYED_CHAIN_VERIFIED",result["source_sha256"])
    print("MG17D_OBSERVED_DOOR_TO_GOAL_WITNESS",json.dumps(result["delayed_public_witnesses"],sort_keys=True))
    print("MG17D_SCIENTIFIC_FIRST_USE_FALSE")
if __name__=="__main__":main()
