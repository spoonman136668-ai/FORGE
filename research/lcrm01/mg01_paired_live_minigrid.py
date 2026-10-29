#!/usr/bin/env python3
"""MG01 — both ORIGINAL native implementations in same source-authentic MiniGrid.

The same original FullyObsWrapper public six-field projection is passed to both
independent learners. Each gets its OWN original env.step consequences, after
its OWN chosen action. No hidden grid, task ID, source oracle, or model sharing.
"""
import argparse
import base64
import dataclasses
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import subprocess
import sys
import time
import traceback

from k4r_minigrid_source import make_env,public,canon,sha
from k4u_native_minigrid import train_experiences, WingBridge, public_grid

HERE=Path(__file__).resolve().parent
FROZEN=HERE/"mg01_paired_live_minigrid_preregistration.json"
SCHEMA="itd02.mg01.paired-authentic-minigrid-live-native.v1"
FIELDS=("x","y","goal_x","goal_y","direction","front_blocked")
NATIVE_TYPES=("wingless_native_go","yggdrasil_native_local_cells")
FAMILIES=("empty","fourrooms")
SEEDS=(9200,9201)
SOURCE="7f5853792ea7f04f75614661006d87fcf949f26d"

def protocol():
    p=json.loads(FROZEN.read_text(encoding="utf-8"))
    if (p["schema"]!="itd02.mg01.original-minigrid-two-native-live-boundary.v1"
        or p["parent"]["head"]!="51b3a936e74a3132c40252f97af1c1b084d62703"
        or p["sources"]["farama_minigrid_git"]!="Farama-Foundation/Minigrid@"+SOURCE
        or p["live_development"]["seeds"]!=list(SEEDS)
        or tuple(p["one_authentic_environment_contract"]["equal_native_six_field_projection"])!=FIELDS
        or p["classification"]["pass"]!="MG01_TWO_INDEPENDENT_NATIVES_LIVE_ORIGINAL_MINIGRID_CONNECTED__NO_SCIENCE"):
        raise ValueError("MG01_FROZEN_SOURCES_OR_INPUTS_CHANGED")
    return p

def public_wire(st):
    """LOSSLESS SAME six legal public fields, no model-specific translation."""
    raw=public_grid(st)
    if type(raw) is not dict or set(raw)!={"X","Y","GoalX","GoalY","Direction","FrontBlocked"}:
        raise ValueError("MG01_K4U_SOURCE_PUBLIC_GRID_SHAPE_DRIFT")
    wire={"x":raw["X"],"y":raw["Y"],
          "goal_x":raw["GoalX"],"goal_y":raw["GoalY"],
          "direction":raw["Direction"],"front_blocked":raw["FrontBlocked"]}
    exact(wire)
    return wire

def exact(s):
    if type(s) is not dict or set(s)!=set(FIELDS):
        raise ValueError("MG01_MISSING_OR_NONCANONICAL_PUBLIC_FIELDS")
    for k in FIELDS[:-1]:
        if type(s[k]) is not int or not 0<=s[k]<=64:
            raise ValueError("MG01_NONINTEGER_PUBLIC_FIELD:"+k)
    if s["direction"]>3 or type(s["front_blocked"]) is not bool:
        raise ValueError("MG01_INVALID_ORIENTATION_OR_FRONT_BLOCKED")
    return s

def colony_input(module,wire):
    x=exact(wire)
    native=module.PublicGrid(**x)
    echoed=dataclasses.asdict(native)
    if echoed!=x or set(echoed)!=set(FIELDS):
        raise ValueError("MG01_YGGDRASIL_PUBLIC_ROUNDTRIP_DRIFT")
    return native

def verify_go_wire(wing,wire):
    e=wing.request("public_echo",before=exact(wire))
    if e.get("public")!=wire:
        raise ValueError("MG01_GO_PUBLIC_JSON_TAGS_OR_ROUNDTRIP_CHANGED")
    # The caller may deliberately test noncanonical formats. Do not coerce.
    return True

def source_training(executable,module):
    """The identical real original K4U FIT transitions reach both natives."""
    stream,original_records,starts,source_cpu=train_experiences()
    if len(starts)!=48 or len(stream)<500 or len(stream)!=len(original_records):
        raise ValueError("MG01_ORIGINAL_K4U_FIT_INCOMPLETE")
    w=WingBridge(executable)
    y=module.GridColony()
    digest=hashlib.sha256()
    first=None
    try:
        for n,e in enumerate(stream):
            before=canonical_from_k4u(e["before"])
            after=canonical_from_k4u(e["after"])
            act=e["action"]
            reward=e["reward"]
            terminal=e["terminal"]
            if type(act) is not int or act not in (0,1,2):
                raise ValueError("MG01_NOT_AN_ORIGINAL_ACTION")
            if type(terminal) is not bool or type(reward) not in (int,float) or not math.isfinite(reward):
                raise ValueError("MG01_INVALID_ORIGINAL_TERMINAL_REWARD")
            if n==0 or n==len(stream)-1:
                verify_go_wire(w,before)
            wb=w.request("learn",before=before,action=act,after=after,
                         reward=float(reward),terminal=terminal)
            if wb.get("updates")!=n+1:
                raise ValueError("MG01_WINGLESS_FIT_DID_NOT_LEARN_ONCE")
            y.observe(colony_input(module,before),act,colony_input(module,after),
                      float(reward),terminal)
            if y.feedback_updates!=n+1:
                raise ValueError("MG01_YGGDRASIL_FIT_DID_NOT_LEARN_ONCE")
            visible={"before":before,"action":act,"after":after,
                     "reward":float(reward),"terminal":terminal}
            digest.update(canon(visible).encode("utf-8")+b"\n")
            if first is None:first=visible
        wing_state=w.snapshot()
        ygg_state=y.save()
        if len(wing_state)>16384 or len(ygg_state)>16384:
            raise ValueError("MG01_NATIVE_FIT_CHECKPOINT_OVER_BOUND")
        if module.GridColony.restore(ygg_state).feedback_updates!=len(stream):
            raise ValueError("MG01_YGG_COLD_RESTORED_FIT_UPDATES_WRONG")
    finally:
        w.close()
    # Wingless state is restored only in an independent new Go process.
    new_w=WingBridge(executable)
    try:
        answer=new_w.request("load",state=base64.b64encode(wing_state).decode())
        if answer.get("updates")!=len(stream):raise ValueError("MG01_GO_COLD_RESTORE_LOST_FIT_UPDATES")
        verify_go_wire(new_w,first["before"])
    finally:new_w.close()
    # Also exercise Yggdrasil reconstruction inside a genuinely new Python OS
    # process, loading ONLY the opaque authenticated source checkpoint.
    check='''import native_policy,sys,json
v=native_policy.GridColony.restore(sys.stdin.buffer.read())
print(json.dumps({"updates":v.feedback_updates}))
'''
    subprocess_check=subprocess.run([sys.executable,"-B","-c",check],input=ygg_state,
                           capture_output=True,timeout=30)
    if subprocess_check.returncode!=0:
        raise ValueError("MG01_YGG_NATIVE_NEW_PROCESS_RESTORE_FAILED:"+subprocess_check.stderr.decode()[-400:])
    if json.loads(subprocess_check.stdout).get("updates")!=len(stream):
        raise ValueError("MG01_YGG_NEW_PROCESS_FIT_UPDATES_DRIFT")
    return {"wingless":wing_state,"yggdrasil":ygg_state,
            "count":len(stream),"stream_sha256":digest.hexdigest(),
            "source_cpu_seconds":source_cpu,
            "go_bytes":len(wing_state),"ygg_bytes":len(ygg_state),
            "go_sha256":sha(wing_state),"ygg_sha256":sha(ygg_state),
            "first_actual_selected_feedback":first}

def canonical_from_k4u(x):
    if type(x) is not dict or set(x)!={"X","Y","GoalX","GoalY","Direction","FrontBlocked"}:
        raise ValueError("MG01_K4U_FIT_PUBLIC_FIELDS_NOT_EXACT")
    return exact({"x":x["X"],"y":x["Y"],"goal_x":x["GoalX"],
                  "goal_y":x["GoalY"],"direction":x["Direction"],
                  "front_blocked":x["FrontBlocked"]})

def episode(family,seed,native_type,fit_state,executable,module):
    """One original-world episode; one independent native actor's decisions."""
    env=make_env(family)
    wing=None
    colony=None
    try:
        obs,info=env.reset(seed=seed)
        st=public(obs)
        start_image_sha=st["grid_sha256"]
        start_six=public_wire(st)
        if native_type=="wingless_native_go":
            wing=WingBridge(executable)
            s=wing.request("load",state=base64.b64encode(fit_state["wingless"]).decode())
            if s.get("updates")!=fit_state["count"]:
                raise ValueError("MG01_GO_EPISODE_INITIAL_FIT_NOT_COLD")
            verify_go_wire(wing,start_six)
        elif native_type=="yggdrasil_native_local_cells":
            colony=module.GridColony.restore(fit_state["yggdrasil"])
            if colony.feedback_updates!=fit_state["count"]:
                raise ValueError("MG01_YGG_EPISODE_INITIAL_FIT_NOT_COLD")
            colony_input(module,start_six)
        else:raise ValueError("MG01_UNKNOWN_NATIVE_ACTOR")
        steps=[]
        reward_total=0.0
        maxsteps=96 if family=="empty" else 192
        success=False
        for t in range(maxsteps):
            before=public_wire(st)
            if native_type=="wingless_native_go":
                action=wing.choose(before)
            else:
                action=colony.choose(colony_input(module,before))
            if type(action) is not int or action not in (0,1,2):
                raise ValueError("MG01_NATIVE_RETURNED_ILLEGAL_ORACLE_ACTION")
            # This is the only environment transition call for the selected
            # action; no emulator, unwrapped state or second-agent reward here.
            next_obs,reward,terminated,truncated,info=env.step(action)
            nxt=public(next_obs,st["goal"])
            after=public_wire(nxt)
            if type(terminated) is not bool or type(truncated) is not bool:
                raise ValueError("MG01_NONCANONICAL_REAL_ENV_TERMINAL")
            if type(reward) not in (int,float) or not math.isfinite(float(reward)):
                raise ValueError("MG01_NONFINITE_ORIGINAL_ENV_REWARD")
            terminal=bool(terminated or truncated)
            if native_type=="wingless_native_go":
                ack=wing.request("learn",before=before,action=action,after=after,
                                 reward=float(reward),terminal=terminal)
                updates=ack.get("updates")
            else:
                colony.observe(colony_input(module,before),action,
                    colony_input(module,after),float(reward),terminal)
                updates=colony.feedback_updates
            if updates!=fit_state["count"]+t+1:
                raise ValueError("MG01_REAL_ENV_FEEDBACK_NOT_LEARNED_EXACTLY_ONCE")
            steps.append({"step":t+1,
              "before_public_image_sha256":st["grid_sha256"],
              "before_equal_sixfield_interface":before,
              "selected_action":action,
              "after_public_image_sha256":nxt["grid_sha256"],
              "after_equal_sixfield_interface":after,
              "original_public_reward":float(reward),
              "original_terminated":terminated,
              "original_truncated":truncated,
              "native_update_counter":updates})
            reward_total+=float(reward)
            st=nxt
            if terminal:
                success=bool(terminated and reward_total>0)
                break
        last_checkpoint=wing.snapshot() if wing is not None else colony.save()
        if len(last_checkpoint)>16384:
            raise ValueError("MG01_REAL_NATIVE_CHECKPOINT_TOO_LARGE")
        if native_type=="wingless_native_go":
            check=WingBridge(executable)
            try:
                ack=check.request("load",state=base64.b64encode(last_checkpoint).decode())
                if ack.get("updates")!=fit_state["count"]+len(steps):
                    raise ValueError("MG01_WINGLESS_END_COLD_RESTORE_LOST_UPDATES")
                verify_go_wire(check,public_wire(st))
                if check.choose(public_wire(st))!=wing.choose(public_wire(st)):
                    raise ValueError("MG01_GO_END_COLD_RESTORE_ACTION_DRIFT")
            finally:check.close()
        else:
            cold=module.GridColony.restore(last_checkpoint)
            if (cold.feedback_updates!=fit_state["count"]+len(steps) or
                cold.choose(colony_input(module,public_wire(st)))!=
                    colony.choose(colony_input(module,public_wire(st)))):
                raise ValueError("MG01_YGG_END_COLD_RESTORE_ACTION_DRIFT")
        return {"family":family,"source_seed_evaluator_only":seed,
           "native":native_type,"public_start_image_sha256":start_image_sha,
           "public_start_sixfield":start_six,
           "real_original_env_step_calls":len(steps),
           "real_selected_original_reward_total":reward_total,
           "original_goal_reached":success,
           "live_native_update_count":len(steps),
           "cold_checkpoint_sha256":sha(last_checkpoint),
           "cold_checkpoint_bytes":len(last_checkpoint),
           "public_actual_action_consequence_trace":steps}
    finally:
        env.close()
        if wing is not None:wing.close()

def run(executable,yggsrc):
    p=protocol()
    if (not (yggsrc/"native_policy.py").is_file() or
        str(yggsrc.resolve()) not in [str(Path(v).resolve()) for v in sys.path]):
        raise ValueError("MG01_PINNED_LOCAL_CELL_SOURCE_NOT_IMPORTABLE")
    import native_policy as ymod
    fit=source_training(executable,ymod)
    records=[]
    for family in FAMILIES:
        for seed in SEEDS:
            two=[episode(family,seed,native_type,fit,executable,ymod)
                 for native_type in NATIVE_TYPES]
            if (len(two)!=2 or
                two[0]["public_start_image_sha256"]!=two[1]["public_start_image_sha256"] or
                two[0]["public_start_sixfield"]!=two[1]["public_start_sixfield"]):
                raise ValueError("MG01_PAIR_DID_NOT_START_SAME_AUTHENTIC_WORLD")
            records.extend(two)
    if len(records)!=8 or any(not x["public_actual_action_consequence_trace"] for x in records):
        raise ValueError("MG01_MISSING_REAL_ORIGINAL_EPISODE")
    if any(len(x["public_actual_action_consequence_trace"])!=x["live_native_update_count"]
           for x in records):
        raise ValueError("MG01_NATIVE_LIVE_FEEDBACK_EXPOSURE_MISMATCH")
    canonical={"schema":SCHEMA,"source_commit":SOURCE,
      "fit_public_updates_each":fit["count"],
      "fit_equal_selected_public_history_sha256":fit["stream_sha256"],
      "fit_go_checkpoint_sha256":fit["go_sha256"],
      "fit_ygg_checkpoint_sha256":fit["ygg_sha256"],
      "native_source_commits":{
          "wingless":p["sources"]["wingless_native_go_source"]["commit"],
          "yggdrasil":p["sources"]["yggdrasil_original_local_cell_source"]["commit"]},
      "paired_live_original_world_episodes":records}
    receipt=sha(canon(canonical).encode())
    return {"schema":SCHEMA,
       "classification":p["classification"]["pass"],
       "scientific_first_use":False,"scientific_accepted":False,
       "native_originals_untouched":True,"FORGE_controller_mutated":False,
       "one_authentic_source_both_natives":True,
       "original_Farama_environment_not_emulated":True,
       "identical_initial_public_observation_per_pair":True,
       "identical_sixfield_semantics_for_both_actors":True,
       "different_selected_actions_may_diverge_true_world_experiences":True,
       "authentic_source_commit":SOURCE,
       "two_independent_native_fit_feedback_counts":fit["count"],
       "FIT_public_selected_history_sha256":fit["stream_sha256"],
       "FIT_go_checksum":fit["go_sha256"],
       "FIT_ygg_checksum":fit["ygg_sha256"],
       "paired_episode_count":len(records),
       "episode_summary":[{
           "family":r["family"],"seed_evaluator_only":r["source_seed_evaluator_only"],
           "native":r["native"],"original_step_calls":r["real_original_env_step_calls"],
           "live_updates":r["live_native_update_count"],
           "original_goal_reached":r["original_goal_reached"],
           "original_reward":r["real_selected_original_reward_total"]}
           for r in records],
       "canonical_public_episode_and_model_custody_sha256":receipt,
       "canonical_full_science":canonical}

def main():
    cli=argparse.ArgumentParser()
    cli.add_argument("--wingless-binary",type=Path,required=True)
    cli.add_argument("--yggdrasil-source-dir",type=Path,required=True)
    cli.add_argument("--output",type=Path,required=True)
    opts=cli.parse_args()
    if opts.output.exists() or not opts.output.parent.is_dir():
        raise ValueError("MG01_RESULT_CANNOT_REPLACE_EXISTING_EVIDENCE")
    before_wall=time.perf_counter();before_cpu=time.process_time()
    try:
        sys.path.insert(0,str(opts.yggdrasil_source_dir.resolve()))
        result=run(opts.wingless_binary,opts.yggdrasil_source_dir)
    except Exception as e:
        result={"schema":SCHEMA,"classification":
           "MG01_ORIGINAL_MINIGRID_NATIVE_BOUNDARY_BLOCKED__NO_SCIENCE",
           "scientific_first_use":False,"scientific_accepted":False,
           "error_type":type(e).__name__,"error":str(e),
           "traceback_tail":traceback.format_exc().splitlines()[-15:]}
    result["host_only_resources"]={
        "wall_seconds":time.perf_counter()-before_wall,
        "python_cpu_seconds":time.process_time()-before_cpu,
        "python_peak_RSS_bytes":int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)*1024,
        "native_Go_process_CPU_not_included":True}
    opts.output.write_text(json.dumps(result,sort_keys=True,indent=2,allow_nan=False)+"\n")
    print("MG01_CLASSIFICATION",result["classification"])
    print("MG01_REAL_FIT_PUBLIC_UPDATES",result.get("two_independent_native_fit_feedback_counts",0))
    print("MG01_REAL_PAIRED_EPISODES",result.get("paired_episode_count",0))
    print("MG01_CANONICAL_EVIDENCE_SHA",result.get("canonical_public_episode_and_model_custody_sha256","NONE"))
    return 0 if result["classification"]=="MG01_TWO_INDEPENDENT_NATIVES_LIVE_ORIGINAL_MINIGRID_CONNECTED__NO_SCIENCE" else 1

if __name__=="__main__":
    raise SystemExit(main())
