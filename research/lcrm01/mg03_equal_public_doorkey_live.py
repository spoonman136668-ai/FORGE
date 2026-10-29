#!/usr/bin/env python3
"""MG03 exact-source authentic MiniGrid DoorKey paired native seven-action gate.

Original Wingless 3-action R8 is NOT this opt-in Go DK7 child. Ygg R12's
R11 source-selected local affordance cells and R12 selector remain untouched.
No hidden map, path oracle, unselected reward, independent answer sharing.
"""
import argparse,base64,hashlib,importlib.util,json,math,os,random,sys,time,traceback
from pathlib import Path
from k4u_native_minigrid import WingBridge
from k4r_minigrid_source import canon,sha
HERE=Path(__file__).resolve().parent
SPEC=HERE/"mg03_equal_public_doorkey_preregistration.json"
PASS="MG03_EQUAL_PUBLIC_SEVEN_ACTION_DOORKEY_NATIVE_INTERFACES_CONNECTED__NO_SCIENCE"
FAIL="MG03_UNEQUAL_OR_UNVERIFIED_NATIVE_SEVEN_ACTION_DOORKEY_BLOCKED__NO_SCIENCE"
SCHEMA="itd02.mg03.authentic-public-seven-action-doorkey-source-only.v1"

def freeze():
    d=json.loads(SPEC.read_text(encoding="utf-8"))
    if (d["schema"]!="itd02.mg03.authentic-public-seven-action-doorkey-wingless-go-ygg-r12.v1"
        or d["parent"]["head"]!="50e2a2d34e8e358624594eed3d57d098c89fa3b1"
        or d["shared_contract"]["environment"]!="MiniGrid-DoorKey-8x8-v0"
        or d["shared_contract"]["legal_actions"]!=list(range(7))
        or d["shared_contract"]["visible_exact_fields"]!=["image","direction","mission"]
        or d["shared_contract"]["objective"]!="positive_reward"
        or d["budgets"]["FIT_expected_exact_selected"]!=1664
        or d["outcome"]["pass"]!=PASS):
        raise ValueError("MG03_PREREG_NOT_FROZEN")
    return d

def source_modules():
    import gymnasium as gym,minigrid
    from research.native.itd02.r10 import public_adapter as o
    from research.native.itd02.r11.affordance_cells import PublicAffordanceCells
    from research.native.itd02.r12.outcome_choice import select_public_action
    collector_path=Path(os.environ["MG03_COLLECTOR_ROOT"])/"research/mass_r7c29/collect.py"
    module=importlib.util.spec_from_file_location("mg03_original_source_public_collector",str(collector_path))
    collector=importlib.util.module_from_spec(module)
    module.loader.exec_module(collector)
    if (tuple(o.ACTION_NAMES)!=("left","right","forward","pickup","drop","toggle","done")
        or o.UPSTREAM_MINIGRID_COMMIT!="7f5853792ea7f04f75614661006d87fcf949f26d"):
        raise ValueError("MG03_ORIGINAL_R12_ACTION_OR_SOURCE_CHANGED")
    return gym,o,PublicAffordanceCells,select_public_action,collector

def normalize(collector,owner,raw):
    normalized=collector.normalized_original_public(raw)
    public=owner.public_observation(normalized)
    if set(public)!={"image","direction","mission"} or len(public["image"])!=7:
        raise ValueError("MG03_NOT_EXACT_ORIGINAL_PUBLIC_OBSERVATION")
    return public

def fit(go_binary,p):
    gym,owner,Cell,choose,collector=source_modules()
    model=Cell()
    wing=WingBridge(go_binary)
    digest=hashlib.sha256()
    events=0
    action_counts={str(a):0 for a in range(7)}
    pickup=door=0
    try:
        for index,seed in enumerate(p["budgets"]["FIT_seeds"]):
            env=gym.make("MiniGrid-DoorKey-8x8-v0")
            a=owner.DoorKeyPublicAdapter()
            rng=random.Random(93617+7919*index)
            try:
                raw,_=env.reset(seed=seed)
                a.reset_public(collector.normalized_original_public(raw))
                model.start_session(a,"mg03-original-public-fit-"+str(seed))
                for step in range(p["budgets"]["FIT_cap_per_episode"]):
                    before=normalize(collector,owner,raw)
                    cues=owner.public_cues(before)
                    native_action=collector.policy({"image":before["image"],"cues":cues},
                                                   rng,step,{})
                    if type(native_action)is not int or native_action not in range(7):
                        raise ValueError("MG03_FIT_ACTION_NOT_ORIGINAL_0_6")
                    assert a.submit(native_action)==native_action
                    after_raw,reward,terminated,truncated,_=env.step(native_action)
                    after=normalize(collector,owner,after_raw)
                    terminal=bool(terminated or truncated)
                    public_event=a.complete(after,float(reward),bool(terminated),bool(truncated))
                    model.learn_selected(a)
                    response=wing.request("learn",before=before,action=native_action,
                        after=after,reward=float(reward),terminal=terminal)
                    events+=1
                    if response.get("updates",0)!=events or model.samples!=events:
                        raise ValueError("MG03_DIFFERENT_SELECTED_FIT_EXPOSURES")
                    action_counts[str(native_action)]+=1
                    pickup+=int(public_event["visible_key_pickup"])
                    door+=int(public_event["visible_door_opened"])
                    digest.update((canon({"before":before,"action":native_action,"after":after,
                                          "reward":float(reward),"terminal":terminal})+"\n").encode())
                    raw=after_raw
                    if terminal:break
            finally:env.close()
        if events!=p["budgets"]["FIT_expected_exact_selected"] or any(n==0 for n in action_counts.values()):
            raise ValueError("MG03_EXACT_ORIGINAL_1664_SEVEN_ACTION_FIT_NOT_PRESENT")
        yblob=model.checkpoint()
        gblob=wing.snapshot()
        if len(yblob)>180000 or len(gblob)>150000:
            raise ValueError("MG03_NATIVE_FIT_CHECKPOINT_OVERSIZE")
    finally:wing.close()
    cold=WingBridge(go_binary)
    try:
        ack=cold.request("load",state=base64.b64encode(gblob).decode())
        if ack.get("updates",0)!=events or cold.snapshot()!=gblob:
            raise ValueError("MG03_GO_ORIGINAL_FIT_NOT_COLD_RESTORED")
    finally:cold.close()
    if Cell.restore(yblob).checkpoint()!=yblob or Cell.restore(yblob).samples!=events:
        raise ValueError("MG03_YGG_NATIVE_LOCAL_FIT_NOT_COLD_RESTORED")
    return {"wingless":gblob,"yggdrasil":yblob,"count":events,
       "selected_history_sha":digest.hexdigest(),
       "action_counts":action_counts,"visible_fit_pickups":pickup,
       "visible_fit_doors":door,"go_source_checkpoint_sha":sha(gblob),
       "ygg_local_source_checkpoint_sha":sha(yblob)}

def episode(native,seed,index,fit_state,binary,p):
    gym,owner,Cell,choose,collector=source_modules()
    env=gym.make("MiniGrid-DoorKey-8x8-v0")
    wing=None
    model=None
    adapter=owner.DoorKeyPublicAdapter()
    rng=random.Random(93617+7919*index+999)
    try:
        raw,_=env.reset(seed=seed)
        start=normalize(collector,owner,raw)
        start_sha=owner.digest(start)
        adapter.reset_public(start)
        if native=="wingless_native_go_dk7":
            wing=WingBridge(binary)
            response=wing.request("load",state=base64.b64encode(fit_state["wingless"]).decode())
            if response.get("updates",0)!=fit_state["count"]:
                raise ValueError("MG03_GO_LIVE_COLD_RESTORE_DRIFT")
            wing.request("begin_episode")
        elif native=="yggdrasil_native_r12_on_r11":
            model=Cell.restore(fit_state["yggdrasil"])
            if model.samples!=fit_state["count"]:
                raise ValueError("MG03_YGG_LIVE_COLD_RESTORE_DRIFT")
            model.start_session(adapter,"mg03-live-"+str(seed))
        else:raise ValueError("MG03_UNKNOWN_NATIVE_ACTOR")
        selected=[]
        proposals=abstentions=fallbacks=goals=pickup=doors=0
        for step in range(p["budgets"]["DEV_cap_per_episode"]):
            before=normalize(collector,owner,raw)
            if adapter.current!=before:
                raise ValueError("MG03_PUBLIC_ADAPTER_SOURCE_DRIFT")
            cues=owner.public_cues(before)
            if wing is not None:
                proposal=wing.request("choose",before=before)
                suggested=proposal.get("action")
                status=proposal.get("status")
                if (suggested is None) != (status=="ABSTAIN_NO_OBSERVED_POSITIVE_ACTION"):
                    raise ValueError("MG03_GO_NATIVE_ABSTENTION_PROVENANCE")
            else:
                proposal=choose(model,before,"positive_reward")
                suggested=proposal["action"]
                status=proposal["status"]
                if (suggested is None) != (status=="ABSTAIN_NO_LEARNED_POSITIVE_ACTION"):
                    raise ValueError("MG03_R12_NATIVE_ABSTENTION_PROVENANCE")
            if suggested is None:
                abstentions+=1;fallbacks+=1
                action=collector.policy({"image":before["image"],"cues":cues},
                                        rng,step,{})
                selector="declared_common_public_external_collector_after_native_abstention"
            else:
                if type(suggested)is not int or suggested not in range(7):
                    raise ValueError("MG03_ILLEGAL_NATIVE_SELECTED_ACTION")
                proposals+=1;action=suggested
                selector="native_selected_from_own_learned_public_effect"
            if wing is not None:
                committed=wing.request("commit",before=before,action=action)
                if committed.get("updates",0)!=fit_state["count"]+step:
                    raise ValueError("MG03_GO_NATIVE_COMMIT_DRIFT")
            a=adapter.submit(action)
            if a!=action:raise ValueError("MG03_SOURCE_ACTION_REMAP")
            next_raw,reward,terminated,truncated,_=env.step(action)
            next_pub=normalize(collector,owner,next_raw)
            event=adapter.complete(next_pub,float(reward),bool(terminated),bool(truncated))
            if wing is not None:
                ack=wing.request("feedback",before=before,action=action,after=next_pub,
                         reward=float(reward),terminal=bool(terminated or truncated))
                if (ack.get("updates",0)!=fit_state["count"]+step+1
                    or ack.get("live",0)!=step+1):
                    raise ValueError("MG03_GO_REAL_NATIVE_SELECTED_FEEDBACK_LOST")
                updates=ack["live"]
            else:
                receipt=model.learn_selected(adapter)
                if model.samples!=fit_state["count"]+step+1 or receipt["sample_index"]!=model.samples:
                    raise ValueError("MG03_R11_REAL_SELECTED_REWARD_NOT_LEARNED")
                updates=model.samples-fit_state["count"]
            goals+=int(float(reward)>0)
            pickup+=int(event["visible_key_pickup"])
            doors+=int(event["visible_door_opened"])
            selected.append({"ordinal":step+1,"before_public_sha":owner.digest(before),
                "public_before":before,"native_proposed_action":suggested,
                "native_proposal_status":status,"action_origin":selector,
                "actual_seven_action":action,"after_public_sha":owner.digest(next_pub),
                "public_after":next_pub,"original_selected_reward":float(reward),
                "terminated":bool(terminated),"truncated":bool(truncated),
                "native_selected_feedback_count":updates})
            raw=next_raw
            if terminated or truncated:break
        last=wing.snapshot() if wing is not None else model.checkpoint()
        cold=WingBridge(binary) if wing is not None else None
        try:
            if cold is not None:
                ack=cold.request("load",state=base64.b64encode(last).decode())
                if (ack.get("updates",0)!=fit_state["count"]+len(selected)
                    or ack.get("live",0)!=len(selected) or cold.snapshot()!=last):
                    raise ValueError("MG03_GO_LIVE_COLD_CUSTODY_DRIFT")
            else:
                restored=Cell.restore(last)
                if restored.samples!=fit_state["count"]+len(selected) or restored.checkpoint()!=last:
                    raise ValueError("MG03_YGG_LIVE_COLD_CUSTODY_DRIFT")
        finally:
            if cold is not None:cold.close()
        return {"native":native,"seed_evaluator_only":seed,
            "exact_identical_start_public_sha":start_sha,
            "actual_original_steps":len(selected),
            "native_selected_proposals":proposals,"native_abstentions":abstentions,
            "external_public_collector_fallbacks":fallbacks,
            "real_goals":goals,"real_key_pickups":pickup,"real_door_openings":doors,
            "cold_native_checkpoint_sha":sha(last),"selected_original_public_events":selected}
    finally:
        env.close()
        if wing is not None:wing.close()

def run(binary,p):
    fit_state=fit(binary,p)
    records=[]
    for index,seed in enumerate(p["budgets"]["DEV_seeds"]):
        pair=[episode(native,seed,index,fit_state,binary,p)
              for native in ("wingless_native_go_dk7","yggdrasil_native_r12_on_r11")]
        if (pair[0]["exact_identical_start_public_sha"]!=pair[1]["exact_identical_start_public_sha"]
            or pair[0]["selected_original_public_events"][0]["public_before"]!=
                pair[1]["selected_original_public_events"][0]["public_before"]):
            raise ValueError("MG03_UNEQUAL_PUBLIC_START")
        records.extend(pair)
    if len(records)!=4 or any(e["actual_original_steps"]==0 for e in records):
        raise ValueError("MG03_EMPTY_ORIGINAL_DOORKEY_EPISODE")
    origin={"schema":SCHEMA,"upstream_source":p["sources"]["farama"],
       "native_source_pins":p["sources"],
       "fit_selected_public_history_sha":fit_state["selected_history_sha"],
       "identical_fit_source_reward_events_per_native":fit_state["count"],
       "all_seven_fit_action_count":fit_state["action_counts"],
       "original_source_fit_pickups":fit_state["visible_fit_pickups"],
       "original_source_fit_door_openings":fit_state["visible_fit_doors"],
       "wingless_fit_checkpoint_sha":fit_state["go_source_checkpoint_sha"],
       "yggdrasil_fit_checkpoint_sha":fit_state["ygg_local_source_checkpoint_sha"],
       "original_doorkey_live_records":records,
       "equal_original_public_7x7_mission_direction":True,
       "different_native_architectures_and_no_shared_memory":True,
       "source_only_external_abstention_collector":True,
       "external_objective_positive_reward_not_learned":True,
       "wingless_go_dk7_is_not_original_r8":True}
    trace=sha(canon(origin).encode())
    return {"schema":SCHEMA,"classification":PASS,
       "scientific_first_use":False,"scientific_accepted":False,
       "accepted_native_model_modified":False,"FORGE_controller_modified":False,
       "wingless_native_R8_upgraded":False,
       "authentic_original_env_step":True,
       "equal_native_seven_action_legal_set":True,
       "same_exact_public_input":True,
       "paired_original_live_episodes":4,
       "original_FIT_identical_feedback_per_model":fit_state["count"],
       "canonical_original_source_trace_sha":trace,
       "canonical_original_source_records":origin}

def main():
    a=argparse.ArgumentParser()
    a.add_argument("--wingless-go-dk7",type=Path,required=True)
    a.add_argument("--output",type=Path,required=True)
    opts=a.parse_args()
    t=time.perf_counter()
    try:
        p=freeze()
        report=run(opts.wingless_go_dk7,p)
    except Exception as e:
        report={"schema":SCHEMA,"classification":FAIL,"scientific_first_use":False,
          "error_type":type(e).__name__,"error":str(e),
          "trace_tail":traceback.format_exc().splitlines()[-12:]}
    report["host_wall_seconds_only"]=time.perf_counter()-t
    opts.output.write_text(json.dumps(report,sort_keys=True,indent=2,allow_nan=False)+"\n")
    print("MG03_CLASSIFICATION",report["classification"])
    print("MG03_SAME_ACTUAL_FIT_PER_NATIVE",report.get("original_FIT_identical_feedback_per_model",0))
    print("MG03_AUTHENTIC_LIVE_EPISODES",report.get("paired_original_live_episodes",0))
    print("MG03_CANONICAL_SOURCE_TRACE_SHA",report.get("canonical_original_source_trace_sha","NONE"))
    if report["classification"]!=PASS:
        print("MG03_BLOCKER",report.get("error_type"),report.get("error"))
    return 0 if report["classification"]==PASS else 1
if __name__=="__main__":
    raise SystemExit(main())
