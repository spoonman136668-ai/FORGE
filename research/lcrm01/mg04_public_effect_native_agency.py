#!/usr/bin/env python3
"""MG04 real Farama DoorKey: native learned public effects vs conventional.

Wingless uses new opt-in Go DK8, *not* original Wingless R8. Yggdrasil uses
original R12 over R11 local-cell source. Equal original 1664 selected training
events, same current public 7x7 image/direction/mission, same explicit manual
stage objective, independently chosen actual source steps, separate memories.
"""
import argparse,base64,hashlib,importlib.util,json,os,random,resource,sys,time,traceback
from pathlib import Path
from k4u_native_minigrid import WingBridge
from k4r_minigrid_source import canon,sha
import mg03_equal_public_doorkey_live as parent

HERE=Path(__file__).resolve().parent
FROZEN=HERE/"mg04_visible_effect_native_agency_prereg.json"
SCHEMA="itd02.mg04.original-doorkey-native-effect-agency.sourceonly.v1"
POS="MG04_BOUNDED_ORIGINAL_DOORKEY_NATIVE_EFFECT_AGENCY_ENGINEERING_POSITIVE__NO_SCIENCE"
NEG="MG04_AUTHENTIC_PUBLIC_EFFECT_NATIVE_AGENCY_NOT_ESTABLISHED__NO_SCIENCE"
FAIL="MG04_SOURCE_OR_EQUAL_PUBLIC_ENGINEERING_BLOCKED__NO_SCIENCE"
ROLES=("wingless_go_dk8","yggdrasil_r12_on_r11","conventional_public_categorical")

def freeze():
    p=json.loads(FROZEN.read_text())
    if (p["schema"]!="itd02.mg04.authentic-original-doorkey-common-public-visible-effect-agency.v1"
        or p["parent_forge"]!="105f953b8536bde78688f0b618f75c9cd51b4696"
        or p["FIT"]["observations"]!=1664
        or p["development"]["arms"]!=list(ROLES)
        or p["development"]["seeds"]!=[64301,64303,64307]
        or p["public"]["legal_actions"]!=list(range(7))):
        raise ValueError("MG04_FROZEN_DESIGN_DRIFT")
    return p

def get_modules():
    gym,owner,Cell,select,collector=parent.source_modules()
    path=Path(os.environ["MG03_COLLECTOR_ROOT"])/"research/mass_r7c30/control.py"
    spec=importlib.util.spec_from_file_location("mg04_original_independent_categorical",path)
    conventional=importlib.util.module_from_spec(spec);spec.loader.exec_module(conventional)
    return gym,owner,Cell,select,collector,conventional

def objective(owner,before):
    cues=owner.public_cues(before)
    # Same declared manually defined stage for all 3 actors.
    return "carrying_changed" if cues["carried"] is None else "visible_door_state_changed"

def conventional_choice(control,conv,before,obj):
    bit={"carrying_changed":2,"visible_door_state_changed":1}[obj]
    possible=[]
    for action in range(7):
        rows=control.counts.get(conv.context(before,action))
        if not rows:continue
        total=sum(rows.values())
        favorable=sum(n for k,n in rows.items() if int(k)&(1<<bit))
        if favorable>0:possible.append((-favorable/total,action))
    if not possible:return {"action":None,"status":"ABSTAIN_NO_LEARNED_POSITIVE_ACTION"}
    return {"action":sorted(possible)[0][1],"status":"SELECT_LEARNED_PUBLIC_ACTION"}

def fit(go_bin,p):
    gym,owner,Cell,select,collector,conv=get_modules()
    wing=WingBridge(go_bin)
    ygg=Cell();control=conv.Control()
    digest=hashlib.sha256();samples=0
    actions={str(a):0 for a in range(7)}
    pickups=doors=0
    try:
        for index,seed in enumerate(p["FIT"]["seeds"]):
            env=gym.make("MiniGrid-DoorKey-8x8-v0")
            adapter=owner.DoorKeyPublicAdapter()
            rng=random.Random(93617+7919*index)
            try:
                raw,_=env.reset(seed=seed)
                adapter.reset_public(collector.normalized_original_public(raw))
                ygg.start_session(adapter,"mg04-authentic-source-fit-"+str(seed))
                for step in range(p["FIT"]["cap"]):
                    before=parent.normalize(collector,owner,raw)
                    cues=owner.public_cues(before)
                    selected=collector.policy({"image":before["image"],"cues":cues},rng,step,{})
                    if type(selected)is not int or selected not in range(7):
                        raise ValueError("MG04_FIT_ACTION_NOT_ORIGINAL_PUBLIC")
                    assert adapter.submit(selected)==selected
                    nxt,reward,terminated,truncated,_=env.step(selected)
                    after=parent.normalize(collector,owner,nxt)
                    event=adapter.complete(after,float(reward),bool(terminated),bool(truncated))
                    native_receipt=ygg.learn_selected(adapter)
                    control.learn(event)
                    response=wing.request("learn",before=before,action=selected,after=after,
                                          reward=float(reward),terminal=bool(terminated or truncated))
                    samples+=1
                    if (native_receipt["sample_index"]!=samples or ygg.samples!=samples
                        or control.samples!=samples or response.get("updates",0)!=samples):
                        raise ValueError("MG04_FIT_SELECTED_PUBLIC_RECEIPT_LOST")
                    actions[str(selected)]+=1
                    pickups+=int(event["visible_key_pickup"])
                    doors+=int(event["visible_door_opened"])
                    digest.update((canon({"before":before,"action":selected,
                      "after":after,"reward":float(reward),
                      "terminal":bool(terminated or truncated)})+"\n").encode())
                    raw=nxt
                    if terminated or truncated:break
            finally:env.close()
        if samples!=1664 or any(x<=0 for x in actions.values()) or pickups==0 or doors==0:
            raise ValueError("MG04_INADEQUATE_OR_CHANGED_AUTHENTIC_FIT")
        go_cp=wing.snapshot();y_cp=ygg.checkpoint();c_cp=control.checkpoint()
    finally:wing.close()
    cold=WingBridge(go_bin)
    try:
        reply=cold.request("load",state=base64.b64encode(go_cp).decode())
        if reply.get("updates",0)!=samples or cold.snapshot()!=go_cp:
            raise ValueError("MG04_GO_FIT_CHECKPOINT_FAIL")
    finally:cold.close()
    if Cell.restore(y_cp).checkpoint()!=y_cp or conv.Control.restore(c_cp).checkpoint()!=c_cp:
        raise ValueError("MG04_R11_OR_CONVENTIONAL_COLD_CHECKPOINT_FAIL")
    return {"native_go":go_cp,"native_ygg":y_cp,"conventional":c_cp,
      "source_history_sha256":digest.hexdigest(),"samples":samples,
      "seven_actual_action_counts":actions,"original_fit_pickups":pickups,
      "original_fit_door_openings":doors,
      "checkpoint_sha256":{"go":sha(go_cp),"ygg":sha(y_cp),"conventional":sha(c_cp)}}

def live(role,seed,index,trained,binary,p):
    gym,owner,Cell,select,collector,conv=get_modules()
    env=gym.make("MiniGrid-DoorKey-8x8-v0")
    adapter=owner.DoorKeyPublicAdapter()
    wing=None;local=None;baseline=None
    rng=random.Random(93617+7919*index+999)
    try:
        raw,_=env.reset(seed=seed)
        start=parent.normalize(collector,owner,raw)
        initial_sha=owner.digest(start)
        adapter.reset_public(start)
        if role=="wingless_go_dk8":
            wing=WingBridge(binary)
            ack=wing.request("load",state=base64.b64encode(trained["native_go"]).decode())
            if ack.get("updates",0)!=trained["samples"]:raise ValueError("MG04_GO_FIT_NOT_RESTORED")
            wing.request("begin_episode")
        elif role=="yggdrasil_r12_on_r11":
            local=Cell.restore(trained["native_ygg"])
            local.start_session(adapter,"mg04-live-"+str(seed))
        elif role=="conventional_public_categorical":
            baseline=conv.Control.restore(trained["conventional"])
        else:raise ValueError("MG04_ROLE_NOT_FROZEN")
        steps=[];selected=abstained=external=effects=0
        achieved={"carrying_changed":0,"visible_door_state_changed":0}
        native_achieved={"carrying_changed":0,"visible_door_state_changed":0}
        goals=0
        for step in range(p["development"]["cap"]):
            before=parent.normalize(collector,owner,raw)
            if adapter.current!=before:raise ValueError("MG04_ORIGINAL_PUBLIC_ADAPTER_DRIFT")
            obj=objective(owner,before)
            cues=owner.public_cues(before)
            if wing is not None:
                proposal=wing.request("choose",before=before,objective=obj)
            elif local is not None:
                proposal=select(local,before,obj)
            else:
                proposal=conventional_choice(baseline,conv,before,obj)
            suggestion=proposal.get("action")
            status=proposal.get("status")
            if suggestion is None:
                if status!="ABSTAIN_NO_LEARNED_POSITIVE_ACTION":
                    raise ValueError("MG04_UNDISCLOSED_UNKNOWN_PUBLIC_ACTION")
                abstained+=1;external+=1
                action=collector.policy({"image":before["image"],"cues":cues},rng,step,{})
                provenance="public_external_collector_after_native_or_control_abstention"
            else:
                if type(suggestion)is not int or suggestion not in range(7) or status!="SELECT_LEARNED_PUBLIC_ACTION":
                    raise ValueError("MG04_PROPOSAL_NOT_ORIGINAL_NATIVE_OR_CONVENTIONAL")
                selected+=1
                action=suggestion
                provenance="model_selected_from_own_source_public_effect_memory"
            if wing is not None:
                receipt=wing.request("commit",before=before,action=action)
                if receipt.get("updates",0)!=trained["samples"]+step:
                    raise ValueError("MG04_GO_COMMITTED_SELECTED_RECEIPT_CHANGED")
            if adapter.submit(action)!=action:raise ValueError("MG04_ORIGINAL_SOURCE_ACTION_REMAP")
            nxt,reward,terminated,truncated,_=env.step(action)
            after=parent.normalize(collector,owner,nxt)
            original=adapter.complete(after,float(reward),bool(terminated),bool(truncated))
            if wing is not None:
                ack=wing.request("feedback",before=before,action=action,after=after,
                    reward=float(reward),terminal=bool(terminated or truncated))
                count=ack.get("live",0)
                if ack.get("updates",0)!=trained["samples"]+step+1 or count!=step+1:
                    raise ValueError("MG04_GO_PUBLIC_EFFECT_FEEDBACK_DROPPED")
            elif local is not None:
                receipt=local.learn_selected(adapter)
                count=local.samples-trained["samples"]
                if receipt["sample_index"]!=trained["samples"]+step+1 or count!=step+1:
                    raise ValueError("MG04_YGG_SELECTED_PUBLIC_EFFECT_DROPPED")
            else:
                baseline.learn(original);count=baseline.samples-trained["samples"]
                if count!=step+1:raise ValueError("MG04_CONTROL_SELECTED_PUBLIC_LEARNING_DROPPED")
            carried_effect=original["carried_before"]!=original["carried_after"]
            front_b,front_a=original["front_before"],original["front_after"]
            door_effect=(front_b[0]==4 and front_a[0]==4 and front_b[2]!=front_a[2])
            effect=carried_effect if obj=="carrying_changed" else door_effect
            achieved[obj]+=int(effect)
            if suggestion is not None:native_achieved[obj]+=int(effect)
            goals+=int(reward>0)
            steps.append({"step":step+1,"public_before":before,"public_after":after,
              "objective_explicit_external":obj,"model_proposal":suggestion,
              "proposal_status":status,"source_of_executed_action":provenance,
              "real_original_action":action,"actual_selected_reward":float(reward),
              "carried_changed":carried_effect,"visible_door_state_changed":door_effect,
              "real_objective_effect":bool(effect),"terminated":bool(terminated),
              "truncated":bool(truncated),"native_or_control_selected_feedback_count":count,
              "original_public_before_sha256":owner.digest(before),
              "original_public_after_sha256":owner.digest(after)})
            raw=nxt
            if terminated or truncated:break
        checkpoint=wing.snapshot() if wing is not None else (
            local.checkpoint() if local is not None else baseline.checkpoint())
        if wing is not None:
            cold=WingBridge(binary)
            try:
                ack=cold.request("load",state=base64.b64encode(checkpoint).decode())
                if (ack.get("updates",0)!=trained["samples"]+len(steps)
                    or ack.get("live",0)!=len(steps) or cold.snapshot()!=checkpoint):
                    raise ValueError("MG04_GO_COLD_REAL_FEEDBACK_LOST")
            finally:cold.close()
        elif local is not None:
            x=Cell.restore(checkpoint)
            if x.samples!=trained["samples"]+len(steps) or x.checkpoint()!=checkpoint:
                raise ValueError("MG04_YGG_SOURCE_COLD_RESTORE_INVALID")
        else:
            x=conv.Control.restore(checkpoint)
            if x.samples!=trained["samples"]+len(steps) or x.checkpoint()!=checkpoint:
                raise ValueError("MG04_CONVENTIONAL_COLD_RESTORE_INVALID")
        if selected+abstained!=len(steps) or external!=abstained:
            raise ValueError("MG04_UNATTRIBUTED_SOURCE_ACTION")
        return {"role":role,"seed_evaluator_only":seed,"original_start_public_sha256":initial_sha,
           "native_or_conventional_actions":selected,"abstentions":abstained,
           "external_public_collector_actions":external,
           "actual_original_env_steps":len(steps),
           "objective_effects_all_origins":achieved,
           "objective_effects_model_selected_only":native_achieved,
           "original_goal_reward_count":goals,
           "native_checkpoint_sha256_after_live":sha(checkpoint),
           "real_original_selected_events":steps}
    finally:
        env.close()
        if wing is not None:wing.close()

def run(binary,p):
    trained=fit(binary,p)
    records=[]
    for index,seed in enumerate(p["development"]["seeds"]):
        trio=[live(role,seed,index,trained,binary,p) for role in ROLES]
        if len({r["original_start_public_sha256"] for r in trio})!=1:
            raise ValueError("MG04_INEQUIVALENT_AUTHENTIC_PUBLIC_START")
        if len({canon(r["real_original_selected_events"][0]["public_before"]) for r in trio})!=1:
            raise ValueError("MG04_MISMATCHED_ORIGINAL_SEVEN_ACTION_FIRST_PUBLIC")
        records.extend(trio)
    if len(records)!=9 or any(x["actual_original_env_steps"]==0 for x in records):
        raise ValueError("MG04_INCOMPLETE_REAL_ORIGINAL_DOORKEY_EXPOSURE")
    summary={role:{
      "episodes":3,
      "model_selected_actions":sum(x["native_or_conventional_actions"] for x in records if x["role"]==role),
      "declared_external_actions":sum(x["external_public_collector_actions"] for x in records if x["role"]==role),
      "actual_original_source_actions":sum(x["actual_original_env_steps"] for x in records if x["role"]==role),
      "actual_key_carry_effects":sum(x["objective_effects_all_origins"]["carrying_changed"] for x in records if x["role"]==role),
      "actual_door_visible_effects":sum(x["objective_effects_all_origins"]["visible_door_state_changed"] for x in records if x["role"]==role),
      "model_selected_key_effects":sum(x["objective_effects_model_selected_only"]["carrying_changed"] for x in records if x["role"]==role),
      "model_selected_door_effects":sum(x["objective_effects_model_selected_only"]["visible_door_state_changed"] for x in records if x["role"]==role),
      "original_goal_rewards":sum(x["original_goal_reward_count"] for x in records if x["role"]==role)
    } for role in ROLES}
    evidence={"schema":SCHEMA,"source_sha":p["original_farama"],
      "same_exact_1664_selected_public_fit_sha256":trained["source_history_sha256"],
      "same_selected_fit_per_arm":trained["samples"],
      "same_all_seven_training_action_counts":trained["seven_actual_action_counts"],
      "source_fit_effects":{"key":trained["original_fit_pickups"],"door":trained["original_fit_door_openings"]},
      "original_model_and_conventional_checkpoint_shas":trained["checkpoint_sha256"],
      "original_source_native_public_action_and_effect_records":records,
      "native_source_truth":p["original_yggdrasil"],
      "go_candidate_is_not_original_wingless_R8":True,
      "external_public_stage_objective_not_learned":True,
      "equal_original_public_action_capability":True,
      "each_arm_separate_native_memory":True,
      "conventional_matched_original_fit":True}
    sha256=sha(canon(evidence).encode())
    if summary["wingless_go_dk8"]["model_selected_actions"]==0 or summary["yggdrasil_r12_on_r11"]["model_selected_actions"]==0:
        classification=NEG
    else:classification=POS
    return {"schema":SCHEMA,"classification":classification,
      "scientific_first_use":False,"native_model_accepted":False,
      "controller_mutated":False,"original_wingless_R8_modified":False,
      "original_yggdrasil_R12_modified":False,
      "same_public_and_budget_provenance":True,
      "real_original_env_step_count":sum(x["actual_original_env_steps"] for x in records),
      "same_1664_fit_samples_per_arm":trained["samples"],
      "source_origin_summary":summary,
      "canonical_evidence_sha256":sha256,"canonical_evidence":evidence}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--wingless-dk8-go",required=True,type=Path)
    parser.add_argument("--output",required=True,type=Path)
    args=parser.parse_args()
    t=time.perf_counter();cpu=time.process_time()
    try:
        result=run(args.wingless_dk8_go,freeze())
    except Exception as exc:
        result={"schema":SCHEMA,"classification":FAIL,"scientific_first_use":False,
          "error_type":type(exc).__name__,"error":str(exc),
          "trace_tail":traceback.format_exc().splitlines()[-16:]}
    result["host_wall_s"]=round(time.perf_counter()-t,6)
    result["host_cpu_s"]=round(time.process_time()-cpu,6)
    result["host_peak_rss_kib"]=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    args.output.write_text(json.dumps(result,sort_keys=True,indent=2,allow_nan=False)+"\n")
    print("MG04_CLASSIFICATION",result["classification"])
    print("MG04_CANONICAL_SHA",result.get("canonical_evidence_sha256","NONE"))
    print("MG04_REAL_SELECTED_FIT",result.get("same_1664_fit_samples_per_arm",0))
    print("MG04_SOURCE_ORIGIN_RESULTS",json.dumps(result.get("source_origin_summary",{}),sort_keys=True))
    if result["classification"]==FAIL:print("MG04_BLOCKER",result.get("error_type"),result.get("error"))
    return 1 if result["classification"]==FAIL else 0
if __name__=="__main__":
    raise SystemExit(main())
